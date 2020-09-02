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

from __future__ import annotations

import io
import os.path
from dataclasses import dataclass

from core import idm, persistence, time, typing as T


@dataclass
class File(persistence.base.File):
    """ File metadata """
    device:int
    inode:int
    path:T.Optional[T.Path]  # Either path or key (or both)
    key:T.Optional[T.Path]   # arguments MUST be specified
    mtime:T.DateTime
    owner:idm.base.User
    group:idm.base.Group
    size:int

    def __post_init__(self) -> None:
        if self.path is None and self.key is None:
            raise TypeError("At least a path or key argument must be specified")

    @classmethod
    def FS(cls, path:T.Path, idm:idm.base.IdentityManager) -> File:
        """ Construct from filesystem """
        stat = path.stat()
        return cls(device = stat.st_dev,
                   inode  = stat.st_ino,
                   path   = path,
                   key    = None,
                   mtime  = time.epoch(stat.st_mtime),
                   owner  = idm.user(uid=stat.st_uid),
                   group  = idm.group(gid=stat.st_gid),
                   size   = stat.st_size)


@dataclass
class GroupSummary:
    path:T.Path  # Common path prefix
    count:int    # Count of files
    size:int     # Total size of files (bytes)

    def __add__(self, other:GroupSummary) -> GroupSummary:
        return GroupSummary(path  = T.Path(os.path.commonpath([self.path, other.path])),
                            count = self.count + other.count,
                            size  = self.size  + other.size)

_UserAccumulatorT = T.Dict[idm.base.Group, GroupSummary]

class UserFileCollection(persistence.base.FileCollection):
    """
    File collection/accumulator for user-specific files

    NOTE The user (file stakeholder) for such collections is assumed to
    to be fixed (i.e., either the file owner or an owner of the file's
    group), so the accumulator is free to ignore any distinction therein

    The accumulator partitions by group and aggregates the count, common
    path prefix and size of the container's files
    """
    _accumulator:_UserAccumulatorT

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._accumulator = {}

    def _accumulate(self, file:File) -> None:
        # Group files by group and aggregate count, path and size
        assert file.path is not None
        acc  = self._accumulator
        key  = file.group
        zero = GroupSummary(path=file.path, count=0, size=0)

        acc[key] = acc.get(key, zero) \
                 + GroupSummary(path=file.path, count=1, size=file.size)

    @property
    def accumulator(self) -> _UserAccumulatorT:
        return self._accumulator


class StagedQueueFileCollection(persistence.base.FileCollection):
    """
    File collection/accumulator for the staging queue

    The accumulator writes the vault key paths, NULL-delimited, to a
    binary buffer
    """
    _accumulator:T.BinaryIO

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._accumulator = io.BytesIO()

    def _accumulate(self, file:File) -> None:
        assert file.key is not None
        self._accumulator.write(bytes(file.key))
        self._accumulator.write(b"\0")

    @property
    def accumulator(self) -> T.BinaryIO:
        # Rewind the accumulator and return it
        self._accumulator.seek(0)
        return self._accumulator


class Deleted(persistence.base.State):
    """ File deleted """

class Staged(persistence.base.State):
    """ File staged """

@dataclass
class Warned(persistence.base.State):
    """ File warned for deletion """
    tminus:T.Union[T.TimeDelta, persistence.Anything]
