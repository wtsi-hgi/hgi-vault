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

from functools import singledispatchmethod
import importlib.resources as resource

from api.logging import Loggable
from core import config, idm, persistence, typing as T
from .models import File, State, FileCollection
from .postgres import PostgreSQL, Transaction


_StateT = T.Union[State.Deleted, State.Staged, State.Warned]
_FileCollectionT = T.Union[FileCollection.User, FileCollection.StagedQueue]

class Persistence(persistence.base.Persistence, Loggable):
    """ PostgreSQL-backed persistence implementation """
    _pg:PostgreSQL
    _idm:idm.base.IdentityManager

    # Groups are not modelled explicitly, so we handle them here
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
            for group in t.fetchall():
                self._persist_group(t, self._idm.group(gid=group.gid))

    def _persist_group(self, t:Transaction, group:idm.base.Group) -> None:
        """ Persist a group and its owners from the IdM """
        if (gid := group.gid) in self._known_groups:
            # Don't refresh groups that are known to the session
            return

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

    def persist(self, file:File, state:_StateT) -> None:
        """
        Persist a file to the database with the specified state

        @param   file   File model to persist
        @param   state  State in which to set the state
        """
        assert not hasattr(file, "db_id")
        file_id = f"{file.device}:{file.inode}"

        # If a persisted file's status (mtime, size, etc.) has changed
        # in the meantime, we need to delete that record and start over;
        # the cascade delete will remove the old statuses appropriately.
        # Ideally, PostgreSQL would do this for us with a rule or
        # trigger, but for now we implement it manually.
        with self._pg.transaction() as t:
            self._persist_group(t, file.group)

            known = File.FromDBQuery(t, file, self._idm)
            if known is not None and file != known:
                # Delete known file if it differs
                self.log.debug(f"Deleting records for file {file_id}")
                known = known.purge(t)

            if known is None:
                # Insert the file record, if necessary
                self.log.debug(f"Persisting file {file_id}")
                known = file.persist(t)

            if state.exists(t, known) is None:
                # Set state, if not already
                self.log.debug(f"Setting {state.db_type} status for file {file_id}")
                state.persist(t, known)

    @property
    def stakeholders(self) -> T.Iterator[idm.base.User]:
        with self._pg.transaction() as t:
            t.execute("select stakeholder from stakeholders;")
            yield from (self._idm.user(uid=user.stakeholder) for user in t)

    def files(self, criteria:persistence.Filter) -> _FileCollectionT:
        """
        Fetch the collection of files based on the given criteria

        @param   criteria  Search criteria
        @return  Appropriate file collection
        """
        # Normally, we want a User collection...
        collection_type = FileCollection.User
        if isinstance(criteria.state, State.Staged) and criteria.state.notified:
            # ...but for notified, staged files, we want a StagedQueue
            collection_type = FileCollection.StagedQueue

        collection = collection_type(self, criteria)

        with self._pg.transaction() as t:
            # CTE snippet for state
            state_cte, state_params = criteria.state.file_cte

            # CTE snippet for stakeholder
            stakeholder_params = ()
            stakeholder_cte = """
                select distinct file
                from   file_stakeholders
            """

            if criteria.stakeholder != persistence.Anything:
                stakeholder_params += (criteria.stakeholder.uid,)
                stakeholder_cte += """
                    where uid = %s
                """

            # Altogether
            t.execute(f"""
                with state_files as (
                    {state_cte}
                ),
                stakeholder_files as (
                    {stakeholder_cte}
                )
                select files.*
                from   files
                join   state_files
                on     state_files.file = files.id
                join   stakeholder_files
                on     stakeholder_files.file = files.id;
            """, state_params + stakeholder_params)

            for record in t:
                self.log.debug(f"Adding {record.device}:{record.inode} to collection")
                collection += File.FromDBRecord(record, self._idm)

        return collection

    @singledispatchmethod
    def clean(self, files):
        # NOTE This should never happen
        self.log.error("Cannot clean unknown file collection type")

    @clean.register
    def _(self, files:FileCollection.User) -> None:
        """ Set the notification state of the files in the collection """
        # Once notified, deleted and warning states will be cleaned up
        # automatically (or deferred) on subsequent instantiations
        state = files.criteria.state
        stakeholder = files.criteria.stakeholder

        with self._pg.transaction() as t:
            for file in files:
                state.mark_notified(t, file, stakeholder)

    @clean.register
    def _(self, files:FileCollection.StagedQueue) -> None:
        """ Delete the files in the staging queue """
        assert isinstance(files.criteria.state, State.Staged)
        assert files.criteria.state.notified

        with self._pg.transaction() as t:
            for file in files:
                file.purge(t)
