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

from core import persistence, time, typing as T
from api.persistence.postgres import Transaction


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
            # Warnings are special, so we override the superclass
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
            # Warnings are special, so we extend the superclass
            assert self.tminus != persistence.Anything

            state_id = super().set(t, file)
            t.execute("""
                insert into warnings (status, tminus)
                values (%s, make_interval(secs => %s));
            """, (state_id, time.seconds(self.tminus)))

            return state_id
