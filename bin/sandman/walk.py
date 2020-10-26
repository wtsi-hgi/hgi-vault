"""
Copyright (c) 2020 Genome Research Limited

Author: Christopher Harrison <ch12@sanger.ac.uk>

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

import os
import gzip
import stat
from abc import ABCMeta, abstractmethod
from dataclasses import dataclass, field

import core.vault
from api.vault import Vault, Branch
from bin.common import idm
from core import file, time, typing as T
from core.utils import base64


# Sentinel types to annotate exceptional vault file status
# (We use the same exception types raised by vault for simplicity)
_PhysicalVaultFile = core.vault.exception.PhysicalVaultFile
_VaultCorruption = core.vault.exception.VaultCorruption

# Downstream only cares about physical and corrupted vault files
_VaultStatusT = T.Union[T.Optional[Branch], _PhysicalVaultFile, _VaultCorruption]


# Automatic re-stat period
_RESTAT_AFTER = time.delta(hours=int(os.getenv("RESTAT_AFTER", "36")))

@dataclass
class File:
    """ Dataclass for walked files """
    path:T.Path
    branch:_VaultStatusT
    _stat:os.stat_result
    _timestamp:T.DateTime = field(default_factory=time.now)

    @property
    def stat(self) -> os.stat_result:
        """ The stat data of a file """
        # Re-stat the file if it's stale
        if time.now() - self._timestamp > _RESTAT_AFTER:
            self._stat = self.path.stat()
            self._timestamp = time.now()

        return self._stat

    @property
    def age(self) -> T.TimeDelta:
        """ The age of a file """
        mtime = time.epoch(self.stat.st_mtime)
        return time.now() - mtime


def _vault_status(path:T.Path) -> _VaultStatusT:
    """
    Determine a file's vault branch/exceptional status, if any, for
    downstream processing

    @param   path  Path to file
    @return  Branch/None   if tracked (or not) by its respective vault
             Exception     if raises a Vault exception
    """
    try:
        vault = Vault(path, idm=idm)
        return vault.branch(path)

    except (_PhysicalVaultFile, _VaultCorruption) as exc_status:
        return exc_status


def _common_ancestors(dirs:T.Iterator[T.Path]) -> T.List[T.Path]:
    """
    Find the common ancestors of a collection of directories

    @param   dirs  Iterator of directory paths
    @return  List of common branch paths
    """
    # By sorting the collection, we know that the first element is a
    # common ancestor and all children follow ancestors. As such, we can
    # simply iterate through the sorted collection checking for descent
    # from the last known common ancestor; when this fails, we have
    # found a new common ancestor and we continue the process.
    first, *remainder = sorted(dirs)
    common = [first]

    for path in remainder:
        try:
            _ = path.relative_to(common[-1])
        except ValueError:
            common.append(path)

    return common


class BaseWalker(metaclass=ABCMeta):
    """ Abstract base class for file walkers """
    @abstractmethod
    def files(self) -> T.Iterator[File]:
        """
        Walk the representation of a filesystem and generate files that
        are found, with their stat information, outside of Vault files

        @return  Generator of files
        """


class FilesystemWalker(BaseWalker):
    """ Walk the filesystem directly: Expensive, but accurate """
    _bases:T.List[T.Path]

    def __init__(self, *bases:T.Path) -> None:
        """
        Constructor: Set the base paths from which to start the walk.
        Note that any paths that are not directories, don't exist, or
        are children of other base paths will be skipped

        @param  bases  Base paths
        """
        self._bases = _common_ancestors(b for base in bases if (b := base.resolve()).is_dir())
        assert len(self._bases) > 0

    @staticmethod
    def _walk_tree(path:T.Path) -> T.Iterator[File]:
        # Recursively walk the tree from the given path
        for f in path.iterdir():
            if f.is_dir():
                yield from FilesystemWalker._walk_tree(f)

            # We only care about regular files
            elif file.is_regular(f):
                yield File(f, _vault_status(f), f.stat())

    def files(self) -> T.Iterator[File]:
        for base in self._bases:
            yield from FilesystemWalker._walk_tree(base)


# mpistat field indices
_SIZE   = 0
_OWNER  = 1
_GROUP  = 2
_ATIME  = 3
_MTIME  = 4
_CTIME  = 5
_MODE   = 6
_INODE  = 7
_NLINKS = 8
_DEVICE = 9

class mpistatWalker(BaseWalker):
    """ Walk an mpistat output file: Cheaper, but imprecise """
    _mpistat:T.Path
    _timestamp:T.DateTime

    _bases:T.List[T.Path]
    _prefixes:T.List[str]

    def __init__(self, mpistat:T.Path, *bases:T.Path) -> None:
        """
        Constructor: Set the base paths from which to start the walk.
        Note that any paths that are not directories, don't exist, or
        are children of other base paths will be skipped

        @param  mpistat  mpistat output
        @param  bases    Base paths
        """
        if not mpistat.is_file():
            raise FileNotFoundError(f"{mpistat} does not exist or is not a file")

        # mpistat file and its modification timestamp
        self._mpistat = mpistat
        self._timestamp = time.epoch(mpistat.stat().st_mtime)

        self._bases = _common_ancestors(b for base in bases if (b := base.resolve()).is_dir())
        self._prefixes = [mpistatWalker._base64_prefix(base) for base in self._bases]
        assert len(self._bases) > 0

    @staticmethod
    def _base64_prefix(path:T.Path) -> str:
        # Find the common base64 prefix of a path to optimise searching
        bare    = base64.encode(path)
        slashed = base64.encode(f"{path}/")

        for i, (lhs, rhs) in enumerate(zip(bare, slashed)):
            if lhs != rhs:
                break
        else:
            # If we reach the end, then bare is a proper prefix of slashed
            i += 1

        return bare[:i]

    def _is_match(self, encoded_path:str) -> T.Optional[T.Path]:
        """ Check that an encoded path is under one of our bases """
        for prefix in self._prefixes:
            if encoded_path.startswith(prefix):
                # Only base64 decode if there's a potential match
                decoded_path = T.Path(base64.decode(encoded_path).decode())

                # Check if we have an actual match
                for base in self._bases:
                    try:
                        _ = decoded_path.relative_to(base)
                        return decoded_path
                    except ValueError:
                        # If decoded_path is not a child of base, then
                        # rinse and repeat...
                        continue

        # ...until no match
        return None

    @staticmethod
    def _make_stat(*stats:str) -> os.stat_result:
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

    def files(self) -> T.Iterator[File]:
        with gzip.open(self._mpistat, mode="rt") as mpistat:
            # Strip excess whitespace and split each line by tabs
            while fields := mpistat.readline().strip().split("\t"):
                encoded, *stats = fields

                # We only care about regular files that are in the
                # vaults we are interested in (per the constructor)
                if stats[_MODE] == "f" and \
                   (path := self._is_match(encoded)) is not None:

                    yield File(path,
                               _vault_status(path),
                               mpistatWalker._make_stat(*stats),
                               self._timestamp)
