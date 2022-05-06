"""
Copyright (c) 2020, 2022 Genome Research Limited

Authors:
    - Christopher Harrison <ch12@sanger.ac.uk>
    - Michael Grace <mg38@sanger.ac.uk>

This program is free software: you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the
Free Software Foundation, either version 3 of the License, or (at your
option) any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General
Public License for more details.

You should have received a copy of the GNU General Public License along
with this program. If not, see https://www.gnu.org/licenses/
"""

from __future__ import annotations

import os
import fcntl
import gzip
import stat
from abc import ABCMeta, abstractmethod
from os.path import commonprefix

from api.logging import Loggable
from api.persistence import models
from api.vault import Vault, Branch
from bin.common import idm, config
from core import file, time, typing as T
from core.idm import base as IDMBase
from core.utils import base64
from core.vault import exception as VaultExc


# Automatic re-stat period (default: 36 hours)
_RESTAT_AFTER = time.delta(hours=int(os.getenv("RESTAT_AFTER", "36")))


# Downstream only cares about physical and corrupted vault files
# i.e., We use our vault exceptions as sentinel types
_VaultStatusT = T.Union[T.Optional[Branch],
                        VaultExc.PhysicalVaultFile,
                        VaultExc.VaultCorruption]


class InvalidVaultBases(Exception):
    """ Raised when invalid Vault base directories are specified """


class File(file.BaseFile):
    """ Walked file model (wrapper around persistence file model) """
    _file: models.File
    _timestamp: T.DateTime

    def __init__(self, file: models.File,
                 timestamp: T.Optional[T.DateTime] = None) -> None:
        """ Construct from filesystem """
        self._file = file
        self._timestamp = timestamp or time.now()

    @classmethod
    def FromFS(cls, path: T.Path) -> File:
        """ Construct from filesystem """
        return cls(models.File.FromFS(path, idm))

    @classmethod
    def FromStat(cls, path: T.Path, stat: os.stat_result,
                 timestamp: T.DateTime) -> File:
        """ Construct from explicit stat data """
        file = models.File(device=stat.st_dev,
                           inode=stat.st_ino,
                           path=path,
                           key=None,
                           mtime=time.epoch(stat.st_mtime),
                           atime=time.epoch(stat.st_atime),
                           ctime=time.epoch(stat.st_ctime),
                           owner=idm.user(uid=stat.st_uid),
                           group=idm.group(gid=stat.st_gid),
                           size=stat.st_size)

        return cls(file, timestamp)

    def __str__(self) -> str:
        return str(self.path)

    @property
    def path(self) -> T.Path:
        return self._file.path

    @property
    def age(self) -> T.TimeDelta:
        self.restat()
        return time.now() - max([self._file.mtime,
                                 self._file.atime, self._file.ctime])

    @property
    def locked(self) -> bool:
        """ Check the file is locked by the filesystem """
        # NOTE This is intended to detect files that are currently in
        # use, so we don't pull them out from under whatever process was
        # reading/writing them. In practice, it checks on advisory locks
        # which anecdotally aren't used much, making it redundant :P
        with self.path.open() as fd:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                fcntl.flock(fd, fcntl.LOCK_UN)
                return False

            except OSError:
                return True

    def restat(self, *, force: bool = False) -> None:
        """ Forcibly restat the file if it's stale """
        # NOTE We backup and restore the key value because it's set to
        # None in the constructor with no way to override it
        if force or time.now() - self._timestamp > _RESTAT_AFTER:
            key = self._file.key
            self._file = models.File.FromFS(self.path, idm)
            self._file.key = key

            self._timestamp = time.now()

    def delete(self) -> None:
        """ Delete the file """
        file.delete(self.path)

    def to_persistence(self, *, key: T.Optional[T.Path] = None) -> models.File:
        """
        Extract (and restat, if necessary) the persistence file model

        @param   key  Vault key path (if known)
        @return  Persistence file
        """
        self.restat()
        file = self._file
        file.key = key
        return file


class BaseWalker(Loggable, metaclass=ABCMeta):
    """ Abstract base class for file walkers """
    @abstractmethod
    def files(self) -> T.Iterator[T.Tuple[Vault, File, _VaultStatusT]]:
        """
        Walk the representation of a filesystem and generate files that
        are found, with their stat information, and corresponding vault
        and vault status

        @return  Generator of Vault, file and status tuples
        """

    @staticmethod
    def _fetch_vaults(*paths: T.Path, idm: IDMBase.IdentityManager = idm) -> T.Set[Vault]:
        """
        Return the Vaults covered by the given paths

        @param   paths  Search paths
        @return  Set of Vaults under said paths
        """
        vaults = set()

        given = 0
        for path in paths:
            given += 1

            try:
                if (vault := Vault(path, idm=idm, autocreate=False, min_owners=config.min_group_owners)).root != path:
                    # Safety feature: Only allow Vault root directories
                    raise InvalidVaultBases(
                        f"The Vault at {path} is rooted at {vault.root}; the Vault root directory must be provided")

                vaults.add(vault)

            except (VaultExc.VaultConflict, VaultExc.NoSuchVault) as e:
                # Safety feature: Don't allow non-Vault controlled paths
                raise InvalidVaultBases(f"No Vault at {path}: {e}")

            except VaultExc.MinimumNumberOfOwnersNotMet as e:
                # Safety feature: Don't allow projects that don't meet min. number of owners
                raise InvalidVaultBases(e)

        if len(vaults) == 0:
            # Safety feature: Require at least one Vault directory
            raise InvalidVaultBases(
                "At least one Vault directory must be provided")

        if len(vaults) != given:
            # Safety feature: Don't allow duplicate entries
            raise InvalidVaultBases(
                "Duplicate Vault directories detected; check command line arguments")

        return vaults

    @staticmethod
    def _vault_status(vault: Vault, path: T.Path) -> _VaultStatusT:
        """
        Determine a file's vault branch/exceptional status, if any, for
        downstream processing

        @param   vault  Vault
        @param   path    Path to file
        @return  Branch/None if tracked (or not) by its respective vault
                 Caught exception if a Vault exception is raised
        """
        try:
            return vault.branch(path)

        except (VaultExc.PhysicalVaultFile, VaultExc.VaultCorruption) as exc_status:
            return exc_status


class FilesystemWalker(BaseWalker):
    """ Walk the filesystem directly: Expensive, but accurate """
    _vaults: T.Set[Vault]

    def __init__(self, *bases: T.Path, idm: IDMBase.IdentityManager = idm) -> None:
        """
        Constructor: Set the base paths from which to start the walk.
        Note that any paths that are not directories, don't exist, or
        are children of other base paths will be skipped

        @param  bases  Base paths
        """
        self._vaults = self._fetch_vaults(*bases, idm=idm)

    @staticmethod
    def _walk_tree(
            path: T.Path, vault: Vault) -> T.Iterator[T.Tuple[Vault, File, _VaultStatusT]]:
        # Recursively walk the tree from the given path
        for f in path.iterdir():
            # NOTE Don't walk symlinked directories: if they're symlinks
            # within the same root, we'll get to them eventually; if
            # they're outside the root, things could go very wrong!
            if (not f.is_symlink()) and f.is_dir() and os.access(f, os.X_OK):
                yield from FilesystemWalker._walk_tree(f, vault)

            # We only care about regular files
            elif file.is_regular(f):
                yield vault, \
                    File.FromFS(f), \
                    FilesystemWalker._vault_status(vault, f)

    def files(self) -> T.Iterator[T.Tuple[Vault, File, _VaultStatusT]]:
        for vault in self._vaults:
            yield from FilesystemWalker._walk_tree(vault.root, vault)


# mpistat field indices
_SIZE = 0
_OWNER = 1
_GROUP = 2
_ATIME = 3
_MTIME = 4
_CTIME = 5
_MODE = 6
_INODE = 7
_NLINKS = 8
_DEVICE = 9


class mpistatWalker(BaseWalker):
    """ Walk an mpistat output file: Cheaper, but imprecise """
    _mpistat: T.Path
    _timestamp: T.DateTime

    _vaults: T.Dict[str, Vault]

    def __init__(self, mpistat: T.Path, *bases: T.Path) -> None:
        """
        Constructor: Set the base paths from which to start the walk.
        Note that any paths that are not directories, don't exist, or
        are children of other base paths will be skipped

        @param  mpistat  mpistat output
        @param  bases    Base paths
        """
        if not mpistat.is_file():
            raise FileNotFoundError(
                f"{mpistat} does not exist or is not a file")

        # mpistat file and its modification timestamp
        self._mpistat = mpistat
        self._timestamp = time.epoch(mpistat.stat().st_mtime)

        # Log a warning if forcible restat'ing is going to happen
        if time.now() - self._timestamp > _RESTAT_AFTER:
            self.log.warning(
                f"mpistat file is out of date; files will be forcibly restat'ed")

        self._vaults = {
            mpistatWalker._base64_prefix(vault.root): vault
            for vault in self._fetch_vaults(*bases)
        }

    @staticmethod
    def _base64_prefix(path: T.Path) -> str:
        # Find the common base64 prefix of a path to optimise searching
        bare = base64.encode(path)
        slashed = base64.encode(f"{path}/")

        return commonprefix([bare, slashed])

    def _is_match(
            self, encoded_path: str) -> T.Optional[T.Tuple[Vault, T.Path]]:
        """ Check that an encoded path is in one of our vaults """
        for prefix, vault in self._vaults.items():
            if encoded_path.startswith(prefix):
                # Only base64 decode if there's a potential match
                decoded_path = T.Path(base64.decode(encoded_path).decode())

                # Check if we have an actual match
                try:
                    _ = decoded_path.relative_to(vault.root)
                    return vault, decoded_path
                except ValueError:
                    # If decoded_path is not a child of the vault
                    # root, then rinse and repeat...
                    continue

        # ...until no match
        return None

    @staticmethod
    def _make_stat(*stats: str) -> os.stat_result:
        """ Convert an mpistat record into an os.stat_result """
        # WARNING os.stat_result does not have a documented interface
        assert len(stats) == 10
        return os.stat_result((
            stat.S_IFREG,         # Mode: Regular file with null permissions
            int(stats[_INODE]),   # inode ID
            int(stats[_DEVICE]),  # Device ID
            int(stats[_NLINKS]),  # Number of hardlinks
            int(stats[_OWNER]),   # Owner ID
            int(stats[_GROUP]),   # Group ID
            int(stats[_SIZE]),    # Size
            int(stats[_ATIME]),   # Last accessed time
            int(stats[_MTIME]),   # Last modified time
            int(stats[_CTIME])    # Last changed time
        ))

    def files(self) -> T.Iterator[T.Tuple[Vault, File, _VaultStatusT]]:
        with gzip.open(self._mpistat, mode="rt") as mpistat:
            # Strip excess whitespace and split each line by tabs
            while fields := mpistat.readline().strip().split("\t"):
                encoded, *stats = fields

                # We only care about regular files that are in the
                # vaults we are interested in (per the constructor)
                if stats[_MODE] == "f" and \
                   (match := self._is_match(encoded)) is not None:

                    vault, path = match
                    yield vault, \
                        File.FromStat(path, mpistatWalker._make_stat(*stats), self._timestamp), \
                        mpistatWalker._vault_status(vault, path)
