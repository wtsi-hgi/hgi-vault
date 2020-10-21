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
from abc import ABCMeta, abstractmethod
from dataclasses import dataclass, field

from core import time, typing as T
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

    def files(self) -> T.Iterator[File]:
        # TODO
        raise NotImplementedError()


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

    def files(self) -> T.Iterator[File]:
        # TODO
        raise NotImplementedError()
