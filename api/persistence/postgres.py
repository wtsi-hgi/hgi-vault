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
from functools import singledispatch

from psycopg2 import Error as PGError
from psycopg2.errors import RaiseException
from psycopg2.extensions import cursor as BaseCursor, connection as BaseConnection
from psycopg2.extras import NamedTupleCursor
from psycopg2.pool import AbstractConnectionPool, ThreadedConnectionPool

from core import persistence, typing as T


# Get connection pool size constraints from environment, if available
_POOL_MIN = int(os.getenv("PG_POOL_MIN", "1"))
_POOL_MAX = int(os.getenv("PG_POOL_MAX", "10"))


_ExcT = T.TypeVar("_ExcT", bound=persistence.exception.BackendException)


def _exception(heading: str, pg_exc: PGError,
               exc_type: T.Type[_ExcT]) -> _ExcT:
    message = f"{heading} {pg_exc.pgcode}"
    if pg_exc.pgerror:
        message += f"\n{pg_exc.pgerror}"

    return exc_type(message)


@singledispatch
def _exception_mapper(exc: PGError) -> persistence.exception.BackendException:
    # Fallback to BackendException
    return _exception("PostgreSQL error", exc,
                      persistence.exception.BackendException)


@_exception_mapper.register
def _(exc: RaiseException) -> persistence.exception.LogicException:
    # RaiseException -> LogicException
    return _exception("PL/pgSQL exception", exc,
                      persistence.exception.LogicException)


class _BaseSession(AbstractContextManager, metaclass=ABCMeta):
    """ Abstract base class for session context managers """
    _connection: BaseConnection
    _cursor: BaseCursor

    def __enter__(self) -> BaseCursor:
        self.session()
        return self._cursor

    def __exit__(self, *exc) -> bool:
        try:
            if not all(exc):
                self._connection.commit()

            else:
                self._connection.rollback()
                _, thrown, _ = exc
                if isinstance(thrown, PGError):
                    raise _exception_mapper(thrown)

        finally:
            self.teardown()

        return False

    @abstractmethod
    def session(self) -> None:
        """ Initialise session state """

    @abstractmethod
    def teardown(self) -> None:
        """ Teardown session state """


class Transaction(_BaseSession):
    """ Transaction context manager, using an injected connection pool """
    _pool: AbstractConnectionPool
    _autocommit: bool

    def __init__(self, *, pool: AbstractConnectionPool,
                 autocommit: bool) -> None:
        self._pool = pool
        self._autocommit = autocommit

    def session(self) -> None:
        self._connection = self._pool.getconn()
        self._connection.autocommit = self._autocommit
        self._cursor = self._connection.cursor()

        # Start transaction
        self._cursor.execute("begin transaction;")

    def teardown(self) -> None:
        self._pool.putconn(self._connection)


class PostgreSQL:
    """
    PostgreSQL Wrapper

    Maintain a thread-safe connection pool and provide convenience
    methods for downstream, with dotted access to cursor results
    """
    _pool: AbstractConnectionPool

    def __init__(self, *, database: str, user: str, password: str,
                 host: str, port: int = 5432) -> None:
        dsn = f"dbname={database} user={user} password={password} host={host} port={port}"
        self._pool = ThreadedConnectionPool(
            _POOL_MIN, _POOL_MAX, dsn, cursor_factory=NamedTupleCursor)

    def __del__(self) -> None:
        self._pool.closeall()

    def transaction(self, autocommit: bool = False) -> Transaction:
        return Transaction(pool=self._pool, autocommit=autocommit)

    def execute_script(self, sql: T.Path) -> None:
        """
        Execute the given SQL script against the database

        @param  sql  Path to SQL script
        """
        with self.transaction(autocommit=True) as t:
            t.execute(sql.read_text())
