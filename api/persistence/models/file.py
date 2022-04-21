"""
Copyright (c) 2020, 2022 Genome Research Limited

Author:
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

from dataclasses import dataclass, field

from core import idm, persistence, time, typing as T
from api.persistence.postgres import Transaction


@dataclass(eq=False, order=False)
class File(persistence.base.File):
    """ File metadata """
    db_id:int = field(init=False, repr=False)

    device:int
    inode:int
    key:T.Optional[T.Path]
    mtime:T.DateTime
    atime: T.DateTime
    ctime: T.DateTime
    owner:idm.base.User
    group:idm.base.Group

    ## Alternative Constructors ########################################

    @classmethod
    def FromFS(cls, path:T.Path, idm:idm.base.IdentityManager) -> File:
        """ Construct from filesystem """
        stat = path.stat()
        return cls(device = stat.st_dev,
                   inode  = stat.st_ino,
                   path   = path,
                   key    = None,
                   mtime  = time.epoch(stat.st_mtime),
                   atime  = time.epoch(stat.st_atime),
                   ctime  = time.epoch(stat.st_ctime),
                   owner  = idm.user(uid=stat.st_uid),
                   group  = idm.group(gid=stat.st_gid),
                   size   = stat.st_size)

    @classmethod
    def FromDBRecord(cls, record:T.NamedTuple, idm:idm.base.IdentityManager) -> File:
        """ Construct from database record """
        file = cls(device = record.device,
                   inode  = record.inode,
                   path   = T.Path(record.path),
                   key    = T.Path(record.key) if record.key is not None else None,
                   mtime  = time.to_utc(record.mtime),
                   atime  = time.to_utc(record.mtime),
                   ctime  = time.to_utc(record.mtime),
                   owner  = idm.user(uid=record.owner),
                   group  = idm.group(gid=record.group_id),
                   size   = record.size)

        file.db_id = record.id
        return file

    @classmethod
    def FromDBQuery(cls, t:Transaction, file:File, idm:idm.base.IdentityManager) -> T.Optional[File]:
        """ Construct from database query, if found """
        if hasattr(file, "db_id"):
            # Don't search for something we've already found
            return file

        t.execute("""
            select *
            from   files
            where  device = %s
            and    inode  = %s;
        """, (file.device, file.inode))
        if (record := t.fetchone()) is None:
            return None

        return cls.FromDBRecord(record, idm)

    ## Methods #########################################################

    def __eq__(self, other:File) -> bool:
        """ Equality predicate """
        # We don't care if the vault keys don't match
        # *** need test for this needing atime check as well
        return self.device == other.device \
           and self.inode  == other.inode \
           and self.path   == other.path \
           and self.mtime  == other.mtime \
           and self.atime  == other.atime \
           and self.owner  == other.owner \
           and self.group  == other.group \
           and self.size   == other.size

    def persist(self, t:Transaction) -> File:
        """ Persist to the database """
        # NOTE This depends on the group record being created first
        assert not hasattr(self, "db_id")

        # NOTE We allow keys to be updated if the record already exists
        t.execute("""
            insert into files (device, inode, path, key, mtime, owner, group_id, size)
            values (%s, %s, %s, %s, %s, %s, %s, %s)
            on conflict (device, inode) do update set key = excluded.key
            returning id;
        """, (self.device,
              self.inode,
              str(self.path),
              str(self.key) if self.key is not None else None,
              self.mtime,
              self.owner.uid,
              self.group.gid,
              self.size))

        self.db_id = t.fetchone().id
        return self

    def purge(self, t:Transaction) -> None:
        """ Purge from the database """
        assert hasattr(self, "db_id")
        t.execute("delete from files where id = %s;", (self.db_id,))
        return None
