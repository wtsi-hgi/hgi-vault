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

from dataclasses import dataclass

from core import idm, persistence, time, typing as T


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
