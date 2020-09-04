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

import importlib.resources as resource

from api.logging import Loggable
from core import config, idm, persistence, typing as T
from . import models
from .models import State
from .postgres import PostgreSQL


_StateT = T.Union[State.Deleted, State.Staged, State.Warned]
_FileCollectionT = T.Union[models.UserFileCollection, models.StagedQueueFileCollection]

class Persistence(persistence.base.Persistence, Loggable):
    """ PostgreSQL-backed persistence implementation """
    _pg:PostgreSQL
    _idm:idm.base.IdentityManager

    _known_groups:T.Set[int]

    def __init__(self, config:config.base.Config, idm:idm.base.IdentityManager) -> None:
        self._pg = PostgreSQL(host     = config.postgres.host,
                              port     = config.postgres.port,
                              database = config.database,
                              user     = config.user,
                              password = config.password)
        self._idm = idm

        # Create schema (idempotent)
        try:
            with resource.path("api.persistence", "schema.sql") as schema:
                self._pg.execute_script(schema)
        except persistence.exception.LogicException:
            self.log.error("Could not create database schema")
            raise

        self._refresh_groups()

    def _refresh_groups(self) -> None:
        """ Clear known group owners and repopulate from the IdM """
        with self._pg.transaction() as t:
            self.log.info("Refreshing group ownership records")

            t.execute("truncate group_owners;")
            self._known_groups = set()

            t.execute("select gid from groups;")
            for group in t:
                self._persist_group(self._idm.group(gid=group.gid))

    def _persist_group(self, group:idm.base.Group) -> None:
        """ Persist a group and its owners from the IdM """
        if (gid := group.gid) in self._known_groups:
            # Don't refresh groups that are known to the session
            return

        with self._pg.transaction() as t:
            self.log.debug(f"Persisting group {gid}")

            t.execute("""
                insert into groups (gid) values (%s)
                on conflict do nothing;
            """, (gid,))

            for user in group.owners:
                self.log.debug(f"Recording user {user.uid} as an owner of group {gid}")
                t.execute("""
                    insert into group_owners (gid, owner) values (%s, %s)
                    on conflict do nothing;
                """, (gid, user.uid))

            self._known_groups.add(gid)

    def persist(self, file:models.File, state:_StateT) -> None:
        """
        Persist a file to the database with the specified state

        @param   file   File model to persist
        @param   state  State in which to set the state
        """
        assert not state.notified
        fs_id = f"{file.device}:{file.inode}"

        # If a persisted file's status (mtime, size, etc.) has changed
        # in the meantime, we need to delete that record and start over;
        # the cascade delete will remove the old statuses appropriately.
        # Ideally, PostgreSQL would do this for us with a rule or
        # trigger, but for now we implement it manually.
        with self._pg.transaction() as t:
            file_id = None
            self._persist_group(file.group)

            t.execute("""
                select *
                from   files
                where  device = %s
                and    inode  = %s;
            """, (file.device, file.inode))

            if (record := t.fetchone()) is not None:
                # File is known...
                file_id  = record.id
                previous = models.File.FromDB(record, self._idm)

                if file != previous:
                    # ...delete it if it differs
                    self.log.debug(f"Deleting records for file {fs_id}")
                    t.execute("delete from files where id = %s;", (file_id,))
                    file_id = None

            # Insert the file record, if necessary
            if file_id is None:
                self.log.debug(f"Persisting file {fs_id}")
                t.execute("""
                    insert into files (device, inode, path, key, mtime, owner, group_id, size)
                    values (%s, %s, %s, %s, to_timestamp(%s), %s, %s, %s)
                    returning id;
                """, file.record)

                file_id = t.fetchone().id

            # Set state, if not already
            if not state.is_set(t, file_id):
                self.log.debug(f"Setting {state.db_type} status for file {fs_id}")
                state.set(t, file_id)

    @property
    def stakeholders(self) -> T.Iterator[idm.base.User]:
        with self._pg.transaction() as t:
            t.execute("select uid from stakeholders;")
            yield from (self._idm.user(uid=user.uid) for user in t)

    def files(self, criteria:persistence.Filter) -> _FileCollectionT:
        raise NotImplementedError

    def clean(self, criteria:persistence.Filter) -> None:
        raise NotImplementedError
