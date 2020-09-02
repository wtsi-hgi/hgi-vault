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

import os.path
from dataclasses import dataclass

from core import idm, persistence, time, typing as T


@dataclass(init=False)
class File(persistence.base.File):
    """ File metadata """
    # NOTE This must refer to a file that is physically outside the
    # vault (rather the any hardlink that is contained within it)
    device:int
    inode:int
    path:T.Path
    mtime:T.DateTime
    owner:idm.base.User
    group:idm.base.Group
    size:int

    def __init__(self, path:T.Path, idm:idm.base.IdentityManager) -> None:
        self.path = path

        stat = path.stat()
        self.device = stat.st_dev
        self.inode  = stat.st_ino
        self.mtime  = time.epoch(stat.st_mtime)
        self.owner  = idm.user(uid=stat.st_uid)
        self.group  = idm.group(gid=stat.st_gid)
        self.size   = stat.st_size


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

    We're only interested in the total number of files, which is already
    provided by __len__, so the accumulator does nothing
    """
    def _accumulate(self, _) -> None:
        pass

    @property
    def accumulator(self) -> int:
        return len(self)


class Deleted(persistence.base.State):
    """ File deleted """

class Staged(persistence.base.State):
    """ File staged """

@dataclass
class Warned(persistence.base.State):
    """ File warned for deletion """
    tminus:T.Union[T.TimeDelta, persistence.Anything]
