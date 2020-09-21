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

from core import idm, persistence, typing as T


@dataclass
class GroupSummary:
    """ Summary aggregation """
    # NOTE We do the aggregation here, in code, rather than with an
    # aggregate query because we need both the full listings and the
    # summary; this is probably slower, but it's easier to maintain.
    # Also, we'd need a custom "commonpath" aggregation function in the
    # schema, which would be non-trivial to write.
    path:T.Path  # Common path prefix
    count:int    # Count of files
    size:int     # Total size of files (bytes)

    def __add__(self, other:GroupSummary) -> GroupSummary:
        return GroupSummary(path  = T.Path(os.path.commonpath([self.path, other.path])),
                            count = self.count + other.count,
                            size  = self.size  + other.size)

_UserAccumulatorT = T.Dict[idm.base.Group, GroupSummary]

class _User(persistence.base.FileCollection):
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


class _StagedQueue(persistence.base.FileCollection):
    """
    File collection/accumulator for the staging queue

    The accumulator simply aggregates the total file size
    """
    _accumulator:int

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._accumulator = 0

    def _accumulate(self, file:File) -> None:
        self._accumulator += file.size


class FileCollection(T.SimpleNamespace):
    """ Namespace of collections to make importing easier """
    User        = _User
    StagedQueue = _StagedQueue