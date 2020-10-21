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
from abc import ABCMeta, abstractmethod
from dataclasses import dataclass, field

from core import file, time, typing as T
from core.utils import base64


# Automatic re-stat period
_RESTAT_AFTER = time.delta(hours=int(os.getenv("RESTAT_AFTER", "36")))

@dataclass
class File:
    """ Dataclass for walked files """
    path:T.Path
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


def _common_branches(dirs:T.Iterator[T.Path]) -> T.List[T.Path]:
    """
    Strip any child subdirectories from within the given directories

    @param   dirs  Iterator of directory paths
    @return  List of common branch paths
    """
    common:T.List[T.Path] = []

    for this in sorted(dirs):
        if len(common) == 0:
            common.append(this)
            continue

        try:
            _ = this.relative_to(common[-1])
        except ValueError:
            common.append(this)

    return common


def _is_vault_file(path:T.Path) -> bool:
    """
    Check whether the given file is a Vault file; that is, not a file
    that is tracked by Vault, but rather a file that is physically
    present within a vault

    @param   path  Path to file
    @return  Predicate value
    """
    raise NotImplementedError()


class _BaseWalker(metaclass=ABCMeta):
    """ Abstract base class for file walkers """
    @abstractmethod
    def files(self) -> T.Iterator[File]:
        """
        Walk the representation of a filesystem and generate files that
        are found, with their stat information, outside of Vault files

        @return  Generator of files
        """


class FilesystemWalker(_BaseWalker):
    """ Walk the filesystem directly """
    _bases:T.List[T.Path]

    def __init__(self, *bases:T.Path) -> None:
        """
        Constructor: Set the base paths from which to start the walk.
        Note that any paths that are not directories, don't exist, or
        are children of other base paths will be skipped

        @param  bases  Base paths
        """
        self._bases = _common_branches(b for base in bases if (b := base.resolve()).is_dir())
        assert len(self._bases) > 0

    @staticmethod
    def _walk_tree(path:T.Path) -> T.Iterator[File]:
        # Recursively walk the tree from the given path
        for f in path.iterdir():
            if f.is_dir():
                yield from FilesystemWalker._walk_tree(f)

            elif file.is_regular(f) and not _is_vault_file(f):
                yield File(f, f.stat())

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

class mpistatWalker(_BaseWalker):
    """ Walk an mpistat output file """
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

        self._bases = _common_branches(b for base in bases if (b := base.resolve()).is_dir())
        self._prefixes = [mpistatWalker._base64_prefix(base) for base in self._bases]
        assert len(self._bases) > 0

    @staticmethod
    def _base64_prefix(path:T.Path) -> str:
        # Find the common base64 prefix of a path to facilitate searching
        bare    = base64.encode(path)
        slashed = base64.encode(f"{path}/")

        for i, (lhs, rhs) in enumerate(zip(bare, slashed)):
            if lhs != rhs:
                break
        else:
            # If we reach the end, then bare is a prefix of slashed
            i += 1

        return bare[:i]

    def _is_match(self, encoded_path:str) -> T.Optional[T.Path]:
        """ Check that an encoded path is under one of our bases """
        for prefix in self._prefixes:
            if encoded_path.startswith(prefix):
                # Only base64 decode if there's a potential match
                decoded_path = T.Path(base64.decode(encoded_path).decode())

                # Check we have an actual match
                for base in self._bases:
                    try:
                        _ = decoded_path.relative_to(base)
                        return decoded_path
                    except ValueError:
                        continue

        # No match
        return None

    @staticmethod
    def _make_stat(*stat:str) -> os.stat_result():
        """ Convert an mpistat record into an os.stat_result """
        # WARNING os.stat_result does not have a documented interface
        assert len(stat) == 10
        return os.stat_result((
            0o100000,           # Mode: We only care about regular files
            int(stat[_INODE]),  # inode ID
            int(stat[_DEVICE]), # Device ID
            int(stat[_NLINKS]), # Number of hardlinks
            int(stat[_OWNER]),  # Owner ID
            int(stat[_GROUP]),  # Group ID
            int(stat[_SIZE]),   # Size
            int(stat[_ATIME]),  # Last accessed time
            int(stat[_MTIME]),  # Last modified time
            int(stat[_CTIME])   # Last changed time
        ))

    def files(self) -> T.Iterator[File]:
        with gzip.open(self._mpistat, mode="rt") as mpistat:
            while fields := mpistat.readline().strip().split("\t"):
                encoded, *stat = fields
                if stat[_MODE] == "f" \
                   and (path := self._is_match(encoded)) is not None \
                   and not _is_vault_file(path):
                    yield File(path,
                               mpistatWalker._make_stat(*stat),
                               self._timestamp)
