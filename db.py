"""
Copyright (c) 2019 Genome Research Limited

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
from pathlib import Path

from psycopg2.extras import NamedTupleCursor
from psycopg2.pool import AbstractConnectionPool, ThreadedConnectionPool
from psycopg2.sql import SQL, Identifier


# Get connection pool size constraints from environment, if available
_POOL_MIN = int(os.getenv("PG_POOL_MIN", "1"))
_POOL_MAX = int(os.getenv("PG_POOL_MAX", "10"))


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
    """ NamedTupleCursor with a table locking context manager """
    @contextmanager
    def lock(self, table:str, lock_mode:LockingMode = LockingMode.AccessExclusive):
        """
        Acquire a lock context manager on the given PostgreSQL table
        with the specified locking mode

        @param  table      PostgreSQL table
        @param  lock_mode  Locking mode (defaults to "access exclusive")
        """
        try:
            _ = self.execute(SQL("""
                begin transaction;
                lock table {table} in """ f"{lock_mode.value}" """ mode;
            """).format(table=Identifier(table)))
            yield self

        finally:
            self.connection.commit()


class PostgreSQL:
    """
    PostgreSQL Wrapper

    Maintain a thread-safe connection pool and provide convenience
    methods for downstream, with dotted access to cursor results
    """
    _pool:AbstractConnectionPool

    def __init__(self, *, database:str, user:str, password:str, host:str, port:int = 5432) -> None:
        dsn = f"dbname={database} user={user} password={password} host={host} port={port}"
        self._pool = ThreadedConnectionPool(_POOL_MIN, _POOL_MAX, dsn, cursor_factory=_LockableNamedTupleCursor)

    def __del__(self) -> None:
        self._pool.closeall()

    @contextmanager
    def cursor(self):
        """ Get a cursor context manager from the connection pool """
        conn = self._pool.getconn()

        try:
            yield conn.cursor()

        finally:
            self._pool.putconn(conn)

    def execute_script(self, sql:Path) -> None:
        """
        Execute the given SQL script against the database

        @param   sql  Path to SQL script
        """
        conn = self._pool.getconn()
        conn.autocommit = True

        with conn.cursor() as c:
            c.execute(sql.read_text())

        self._pool.putconn(conn)
