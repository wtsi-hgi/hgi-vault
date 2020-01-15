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
from contextlib import contextmanager
from enum import Enum
from functools import singledispatch
from pathlib import Path

import psycopg2
from psycopg2.errors import RaiseException
from psycopg2.extras import NamedTupleCursor
from psycopg2.pool import AbstractConnectionPool, ThreadedConnectionPool
from psycopg2.sql import SQL, Identifier

from common import types as T
from common.models.filesystems.types import BaseFilesystem
from ..types import BaseStateProtocol
from ..exceptions import BackendException, LogicException, NoFilesystemConvertor


# Get connection pool size constraints from environment, if available
_POOL_MIN = int(os.getenv("PG_POOL_MIN", "1"))
_POOL_MAX = int(os.getenv("PG_POOL_MAX", "10"))


# Advisory lock IDs
_ADVISORY_LOCKS = {
    "DDL": 0
}


_ExcT = T.TypeVar("_ExcT", bound=BackendException)

def _exception(heading:str, pg_exc:psycopg2.Error, exc_type:T.Type[_ExcT]) -> _ExcT:
    message = f"{heading} {pg_exc.pgcode}"
    if pg_exc.pgerror:
        message += f"\n{pg_exc.pgerror}"

    return exc_type(message)

@singledispatch
def _exception_mapper(exc:psycopg2.Error) -> BackendException:
    # Fallback to BackendException
    return _exception("PostgreSQL error", exc, BackendException)

@_exception_mapper.register
def _(exc:RaiseException) -> LogicException:
    # RaiseException -> LogicException
    return _exception("PL/pgSQL exception", exc, LogicException)


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


class _LockableNamedTupleCursor(NamedTupleCursor):
    """ NamedTupleCursor with a locking context managers """
    @contextmanager
    def advisory_lock(self, lock_id:int):
        """
        Acquire a session-level advisory lock context manager with the
        given advisory lock ID

        @oaram  lock_id  Advisory lock ID
        """
        # FIXME These context managers are all very similar!
        failed = False

        try:
            self.execute("select pg_advisory_lock(%s);", (lock_id,))
            yield self

        except psycopg2.Error as e:
            failed = True
            self.connection.rollback()
            raise _exception_mapper(e)

        finally:
            if not failed:
                self.connection.commit()

            self.execute("select pg_advisory_unlock(%s);", (lock_id,))

    @contextmanager
    def table_lock(self, *tables:str, lock_mode:LockingMode = LockingMode.AccessExclusive):
        """
        Acquire a table lock context manager on the given tables with
        the specified locking mode

        @param  tables     PostgreSQL tables
        @param  lock_mode  Locking mode (defaults to "access exclusive")
        """
        # FIXME These context managers are all very similar!
        # NOTE Given that we've effectively serialised everything with
        # advisory locks, explicit table locking is a bit redundant
        failed = False

        try:
            to_lock = SQL(", ").join(Identifier(t) for t in tables)
            self.execute(SQL("""
                begin transaction;
                lock table {tables} in """ f"{lock_mode.value}" """ mode;
            """).format(tables=to_lock))

            yield self

        except psycopg2.Error as e:
            failed = True
            self.connection.rollback()
            raise _exception_mapper(e)

        finally:
            if not failed:
                self.connection.commit()


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
        self._pool = ThreadedConnectionPool(_POOL_MIN, _POOL_MAX, dsn, cursor_factory=_LockableNamedTupleCursor)

    def __del__(self) -> None:
        self._pool.closeall()

    @contextmanager
    def transaction(self, *, autocommit:bool = False):
        """ Transaction context manager, using the connection pool """
        # FIXME These context managers are all very similar!
        failed = False

        try:
            connection = self._pool.getconn()
            connection.autocommit = autocommit
            cursor = connection.cursor()

            # Acquire and release all advisory locks
            # NOTE This will necessarily serialise transactions
            cursor.executemany("""
                select pg_advisory_lock(%(lock_id)s);
                select pg_advisory_unlock(%(lock_id)s);
            """, [{"lock_id": lock_id} for lock_id in _ADVISORY_LOCKS.values()])

            yield cursor

        except psycopg2.Error as e:
            failed = True
            connection.rollback()
            raise _exception_mapper(e)

        finally:
            if not autocommit and not failed:
                connection.commit()

            self._pool.putconn(connection)

    def execute_script(self, sql:Path) -> None:
        """
        Execute the given SQL script against the database

        @param  sql  Path to SQL script
        """
        with self.transaction(autocommit=True) as c:
            with c.advisory_lock(_ADVISORY_LOCKS["DDL"]):
                c.execute(sql.read_text())

    def filesystem_convertor(self, name:str) -> BaseFilesystem:
        if name not in self._filesystems:
            raise NoFilesystemConvertor(f"Cannot convert \"{name}\" into a recognised instance")

        return self._filesystems[name]
