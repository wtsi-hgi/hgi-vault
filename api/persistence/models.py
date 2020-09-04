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
from .postgres import Transaction


@dataclass(eq=False)
class File(persistence.base.File):
    """ File metadata """
    device:int
    inode:int
    path:T.Path
    key:T.Optional[T.Path]
    mtime:T.DateTime
    owner:idm.base.User
    group:idm.base.Group
    size:int

    @classmethod
    def FromFS(cls, path:T.Path, idm:idm.base.IdentityManager) -> File:
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

    @classmethod
    def FromDB(cls, record:T.NamedTuple, idm:idm.base.IdentityManager) -> File:
        """ Construct from database record """
        return cls(device = record.device,
                   inode  = record.inode,
                   path   = T.Path(record.path),
                   key    = T.Path(record.key) if record.key is not None else None,
                   mtime  = time.epoch(record.mtime),
                   owner  = self._idm.user(uid=record.owner),
                   group  = self._idm.group(uid=record.group_id),
                   size   = record.size)

    def __eq__(self, other:File) -> bool:
        """ Equality predicate """
        # We don't care if the vault keys don't match
        return self.device == other.device \
           and self.inode  == other.inode \
           and self.path   == other.path \
           and self.mtime  == other.mtime \
           and self.owner  == other.owner \
           and self.group  == other.group \
           and self.size   == other.size

    @property
    def record(self) -> T.Tuple:
        """ Representation as a record tuple """
        return (self.device,
                self.inode,
                str(self.path),
                str(self.key) if self.key is not None else None,
                time.timestamp(self.mtime),
                self.owner.uid,
                self.group.gid,
                self.size)


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


class _PersistedState(persistence.base.State):
    """ Base for our persistence operations """
    db_type:T.ClassVar[str]

    def is_set(self, t:Transaction, file:int) -> bool:
        """
        Check the status is set for a given file

        @param   t     Transaction
        @param   file  File ID
        @return  Set predicate
        """
        t.execute("""
            select 1
            from   status
            where  state = %s
            and    file  = %s;
        """, (self.db_type, file))
        return t.fetchone() is not None

    def set(self, t:Transaction, file:int) -> int:
        """
        Set the status for a given file

        @param   t     Transaction
        @param   file  File ID
        @return  New status ID
        """
        t.execute("""
            insert into status (file, state)
            values (%s, %s)
            returning id;
        """, (file, self.db_type))
        return t.fetchone().id

class State(T.SimpleNamespace):
    """ Namespace of file states to make importing easier """
    class Deleted(_PersistedState):
        """ File deleted """
        db_type = "deleted"

    class Staged(_PersistedState):
        """ File staged """
        db_type = "staged"

    @dataclass
    class Warned(_PersistedState):
        """ File warned for deletion """
        db_type = "warned"
        tminus:T.Union[T.TimeDelta, T.Type[persistence.Anything]]

        def is_set(self, t:Transaction, file:int) -> bool:
            assert self.tminus != persistence.Anything

            t.execute("""
                select 1
                from   warnings
                join   status
                on     status.id       = warnings.status
                where  status.file     = %s
                and    warnings.tminus = make_interval(secs => %s);
            """, (file_id, time.seconds(state.tminus)))
            return t.fetchone().id

        def set(self, t:Transaction, file:int) -> int:
            assert self.tminus != persistence.Anything

            state_id = super().set(t, file)
            t.execute("""
                insert into warnings (status, tminus)
                values (%s, make_interval(secs => %s));
            """, (state_id, self.tminus.total_seconds()))

            return state_id
