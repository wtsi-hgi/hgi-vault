"""
Copyright (c) 2019, 2020 Genome Research Limited

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

import os
from abc import ABCMeta, abstractmethod
from contextlib import AbstractContextManager
from enum import Enum
from functools import singledispatch
from pathlib import Path

from psycopg2 import Error as PGError
from psycopg2.errors import RaiseException
from psycopg2.extensions import cursor as Cursor, connection as Connection
from psycopg2.extras import NamedTupleCursor, execute_batch
from psycopg2.pool import AbstractConnectionPool, ThreadedConnectionPool
from psycopg2.sql import SQL, Identifier

from common import types as T
from common.models.filesystems.types import BaseFilesystem
from ..types import BaseStateProtocol
from ..exceptions import BackendException, LogicException, NoFilesystemConvertor


# Get connection pool size constraints from environment, if available
_POOL_MIN = int(os.getenv("PG_POOL_MIN", "1"))
_POOL_MAX = int(os.getenv("PG_POOL_MAX", "10"))


class AdvisoryLockID(Enum):
    """ Enumeration of application-specific advisory lock IDs """
    DDL = 0

class LockingMode(Enum):
    """ PostgreSQL locking mode enumeration """
    AccessShare          = "access share"
    RowShare             = "row share"
    RowExclusive         = "row exclusive"
    ShareUpdateExclusive = "share update exclusive"
    Share                = "share"
    ShareRowExclusive    = "share row exclusive"
    Exclusive            = "exclusive"
    AccessExclusive      = "access exclusive"


_ExcT = T.TypeVar("_ExcT", bound=BackendException)

def _exception(heading:str, pg_exc:PGError, exc_type:T.Type[_ExcT]) -> _ExcT:
    message = f"{heading} {pg_exc.pgcode}"
    if pg_exc.pgerror:
        message += f"\n{pg_exc.pgerror}"

    return exc_type(message)

@singledispatch
def _exception_mapper(exc:PGError) -> BackendException:
    # Fallback to BackendException
    return _exception("PostgreSQL error", exc, BackendException)

@_exception_mapper.register
def _(exc:RaiseException) -> LogicException:
    # RaiseException -> LogicException
    return _exception("PL/pgSQL exception", exc, LogicException)

class _BaseSession(AbstractContextManager, metaclass=ABCMeta):
    """ Abstract base class for session context managers """
    _connection:Connection
    _cursor:Cursor

    def __enter__(self) -> Cursor:
        self.session()
        return self._cursor

    def __exit__(self, *exception) -> bool:
        _, exc, _ = exception
        raised = exc is not None

        try:
            if raised:
                self._connection.rollback()
                if isinstance(exc, PGError):
                    raise _exception_mapper(exc)
            else:
                self._connection.commit()

        finally:
            self.teardown()

        return False

    @abstractmethod
    def session(self) -> None:
        """ Initialise session state """

    @abstractmethod
    def teardown(self) -> None:
        """ Teardown session state """


class _LockableNamedTupleCursor(NamedTupleCursor):
    """ NamedTupleCursor with a locking context managers """
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        cursor = self

        class _Lock(_BaseSession):
            """ Base lock """
            _entry_query:T.Optional[T.Tuple[T.Union[str, SQL], ...]]
            _exit_query:T.Optional[T.Tuple[T.Union[str, SQL], ...]]

            def session(self) -> None:
                self._connection = cursor.connection
                self._cursor = cursor

                if self._entry_query is not None:
                    self._cursor.execute(*self._entry_query)

            def teardown(self) -> None:
                if self._exit_query is not None:
                    self._cursor.execute(*self._exit_query)

        class _AdvisoryLock(_Lock):
            """
            Acquire a session-level advisory lock context manager with
            the given advisory lock ID

            @oaram  lock_id  Advisory lock ID
            """
            def __init__(self, lock_id:AdvisoryLockID):
                self._entry_query = ("select pg_advisory_lock(%s);", (lock_id.value,))
                self._exit_query  = ("select pg_advisory_unlock(%s);", (lock_id.value,))

        class _TableLock(_Lock):
            """
            Acquire a table lock context manager on the given tables
            with the specified locking mode

            @param  tables     PostgreSQL tables
            @param  lock_mode  Locking mode (defaults to "access exclusive")
            """
            # NOTE Given that we've effectively serialised everything
            # with advisory locks, explicit table locking is a bit
            # redundant
            def __init__(self, *tables:str, lock_mode:LockingMode = LockingMode.AccessExclusive):
                to_lock = SQL(", ").join(Identifier(t) for t in tables)
                self._entry_query = (SQL("""
                    begin transaction;
                    lock table {tables} in """ f"{lock_mode.value}" """ mode;
                """).format(tables=to_lock),)
                self._exit_query = None

        self.advisory_lock = _AdvisoryLock
        self.table_lock = _TableLock


class PostgreSQL(BaseStateProtocol):
    """
    PostgreSQL Wrapper

    Maintain a thread-safe connection pool and provide convenience
    methods for downstream, with dotted access to cursor results
    """
    _pool:AbstractConnectionPool

    def __init__(self, *, database:str, user:str, password:str, host:str, port:int = 5432) -> None:
        self._filesystems = {}

        dsn = f"dbname={database} user={user} password={password} host={host} port={port}"
        self._pool = pool = ThreadedConnectionPool(_POOL_MIN, _POOL_MAX, dsn, cursor_factory=_LockableNamedTupleCursor)

        class _Transaction(_BaseSession):
            """
            Transaction context manager, using the connection pool

            @param  autocommit  Transaction autocommit mode (defaults to False)
            """
            _pool:AbstractConnectionPool
            _autocommit:bool

            def __init__(self, *, autocommit:bool = False) -> None:
                self._pool = pool
                self._autocommit = autocommit

            def session(self) -> None:
                self._connection = self._pool.getconn()
                self._connection.autocommit = self._autocommit
                self._cursor = self._connection.cursor()

                # Acquire and release all advisory locks
                # NOTE This will necessarily serialise transactions
                execute_batch(self._cursor, """
                    select pg_advisory_lock(%(lock_id)s);
                    select pg_advisory_unlock(%(lock_id)s);
                """, [{"lock_id": lock_id.value} for lock_id in AdvisoryLockID])

                # Start transaction
                self._cursor.execute("begin transaction;")

            def teardown(self) -> None:
                self._pool.putconn(self._connection)

        self.transaction = _Transaction

    def __del__(self) -> None:
        self._pool.closeall()

    def execute_script(self, sql:Path) -> None:
        """
        Execute the given SQL script against the database

        @param  sql  Path to SQL script
        """
        with self.transaction(autocommit=True) as c:
            with c.advisory_lock(AdvisoryLockID.DDL):
                c.execute(sql.read_text())

    def filesystem_convertor(self, name:str) -> BaseFilesystem:
        if name not in self._filesystems:
            raise NoFilesystemConvertor(f"Cannot convert \"{name}\" into a recognised instance")

        return self._filesystems[name]
