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

from dataclasses import dataclass

from core import idm, persistence, typing as T
from api.persistence.postgres import Transaction
from .file import File


# Convenience aliases for types we use regularly
_Anything = persistence.Anything
_MaybeStakeholder = T.Union[idm.base.User, T.Type[_Anything]]
_SQLSnippet = T.Tuple[str, T.Tuple]


class _PersistedState(persistence.base.State):
    """ Base for our persistence operations """
    db_type: T.ClassVar[str]

    def exists(self, t: Transaction, file: File) -> T.Optional[int]:
        """
        Check the status exists for a given file

        @param   t     Transaction
        @param   file  File
        @return  The status ID, if available, or None otherwise
        """
        assert hasattr(file, "db_id")

        t.execute("""
            select id
            from   status
            where  state = %s
            and    file  = %s;
        """, (self.db_type, file.db_id))

        if (record := t.fetchone()) is None:
            return None
        return record.id

    def persist(self, t: Transaction, file: File) -> int:
        """
        Persist the status for a given file

        @param   t     Transaction
        @param   file  File
        @return  New status ID
        """
        assert hasattr(file, "db_id")

        t.execute("""
            insert into status (file, state)
            values (%s, %s)
            returning id;
        """, (file.db_id, self.db_type))
        state_id = t.fetchone().id

        # Set the notification status for all stakeholders, if required
        # (this should never happen in production)
        if self.notified:
            self.mark_notified(t, file, _Anything)

        return state_id

    def mark_notified(self, t: Transaction, file: File,
                      stakeholder: _MaybeStakeholder) -> None:
        """
        Set the notification state to true for a file and stakeholder

        @param   t            Transaction
        @param   file         File
        @param   stakeholder  Stakeholder
        """
        if (state_id := self.exists(t, file)) is None:
            state_id = self.persist(t, file)

        query_params = (state_id, file.db_id)
        query_sql = """
            select id,
                   stakeholder
            from   stakeholder_notified
            where  (not notified)
            and    id   = %s
            and    file = %s
        """

        if stakeholder != _Anything:
            query_params += (stakeholder.uid,)
            query_sql += """
                and stakeholder = %s
            """

        t.execute(f"""
            insert into notifications (status, stakeholder)
            {query_sql}
            on conflict do nothing;
        """, query_params)

    def file_cte(self, stakeholder: _MaybeStakeholder) -> _SQLSnippet:
        """
        Return the SQL CTE snippet and parameters to fetch the file IDs
        satisfying the present state for the given stakeholder

        @param   stakeholder  Stakeholder
        @return  SQL CTE snippet and parameters
        """
        # NOTE This interface is a bit kludgy; rather than returning SQL
        # snippets to the persistence engine, we could return the actual
        # files. However, that would need a reference to the persistence
        # engine (and the IdM), so this is "the least bad" compromise!
        params = (self.db_type,)
        sql = """
            select distinct file
            from   stakeholder_notified
            where  state = %s
        """

        if self.notified != _Anything:
            params += (self.notified,)
            sql += """
                and notified = %s
            """

        if stakeholder != _Anything:
            params += (stakeholder.uid,)
            sql += """
                and stakeholder = %s
            """

        return sql, params


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
        tminus: T.Union[T.TimeDelta, T.Type[_Anything]]

        def exists(self, t: Transaction, file: File) -> T.Optional[int]:
            # Warnings are special, so we override the superclass
            assert hasattr(file, "db_id")
            assert self.tminus != _Anything

            t.execute("""
                select status.id
                from   warnings
                join   status
                on     status.id       = warnings.status
                where  status.file     = %s
                and    warnings.tminus = %s;
            """, (file.db_id, self.tminus))

            if (record := t.fetchone()) is None:
                return None
            return record.id

        def persist(self, t: Transaction, file: File) -> int:
            # Warnings are special, so we extend the superclass
            assert hasattr(file, "db_id")
            assert self.tminus != _Anything

            state_id = super().persist(t, file)
            t.execute("""
                insert into warnings (status, tminus)
                values (%s, %s);
            """, (state_id, self.tminus))

            return state_id

        def file_cte(self, stakeholder: _MaybeStakeholder) -> _SQLSnippet:
            # Warnings are special, so we override the superclass
            # TODO There's scope for abstraction here: the query is the
            # same, with an additional join and possible parameter
            params = (self.db_type,)
            sql = """
                select distinct stakeholder_notified.file
                from   stakeholder_notified
                join   warnings
                on     warnings.status = stakeholder_notified.id
                where  stakeholder_notified.state = %s
            """

            if self.notified != _Anything:
                params += (self.notified,)
                sql += """
                    and stakeholder_notified.notified = %s
                """

            if stakeholder != _Anything:
                params += (stakeholder.uid,)
                sql += """
                    and stakeholder_notified.stakeholder = %s
                """

            if self.tminus != _Anything:
                params += (self.tminus,)
                sql += """
                    and warnings.tminus = %s
                """

            return sql, params
