"""
Copyright (c) 2022 Genome Research Limited

Author: Michael Grace <mg38@sanger.ac.uk>

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
import unittest
from dataclasses import dataclass
from pathlib import Path
from test.common import DummyIDM
from unittest import mock

import psycopg2

from api.config import Executable
from api.persistence.engine import Persistence
from bin.common import clear_config_cache, generate_config
from core import typing as T
from core.file import BaseFile
from core.persistence import Anything, Filter
from core.persistence import base as PersistenceBase


@dataclass
class DummyState(PersistenceBase.State):
    db_type: str


@dataclass
class DummyFile(BaseFile):
    def __init__(self, path: T.Path) -> None:
        self._path = path

    @property
    def path(self) -> T.Path:
        return self._path

    @property
    def age(self) -> T.TimeDelta:
        return T.TimeDelta(days=0)


class TestPersistence(unittest.TestCase):
    """we'll test what we can without having to set
    up an actual postgres instance

    what does that actually mean? well, i guess we'll
    test converting objects to SQL queries and just
    see what SQL we get

    whether the DB can actually cope with that after
    is another problem
    """

    def test_get_states_sql(self):
        def _normalise(s: str, p: T.Tuple[T.Any, ...]
                       ) -> T.Tuple[str, T.Tuple[T.Any, ...]]:
            s = s.strip().replace("\n", " ").replace("\t", "")
            while s.count("  ") > 0:
                s = s.replace("  ", " ")
            s = s.replace("( ", "(").replace(" )", ")")

            return s, p

        _BASE_SQL = """
            select status.* from warnings
            inner join status
            on warnings.status = status.id
            inner join files
            on status.file = files.id
        """

        # 1. No Filters
        self.assertEquals(_normalise(*Persistence.states_sql(Filter(
            state=Anything
        ))), _normalise(_BASE_SQL, tuple([])))

        # 2. File Path Filter
        self.assertEquals(_normalise(*Persistence.states_sql(Filter(
            state=Anything, file=DummyFile(Path("file/path"))
        ))), _normalise(_BASE_SQL + "where files.path = %s", ("file/path",)))

        # 3. State Filter
        self.assertEqual(_normalise(*Persistence.states_sql(Filter(
            state=DummyState(notified=Anything, db_type="test")
        ))), _normalise(_BASE_SQL + "where status.state = %s", ("test",)))

        # 4. State Notified Filter
        self.assertEqual(
            _normalise(
                *Persistence.states_sql(Filter(
                    state=DummyState(notified=True, db_type="test")
                ))
            ), _normalise(
                _BASE_SQL + """where status.state = %s and
                    status.id in (
                        select distinct status
                        from notifications
                    )""", ("test",)))

        # 5. State and File Filter
        self.assertEqual(
            _normalise(
                *Persistence.states_sql(Filter(
                    state=DummyState(notified=True, db_type="test"),
                    file=DummyFile(Path("file/path"))
                ))
            ), _normalise(
                _BASE_SQL + """where files.path = %s
                and status.state = %s
                and status.id in (
                    select distinct status
                    from notifications
                )""", ("file/path", "test")
            )
        )


class TestPostgres(unittest.TestCase):
    def setUp(self) -> None:
        clear_config_cache()

    def test_connection(self):
        try:
            config, _ = generate_config(Executable.SANDMAN)
            idm = DummyIDM(config)
            Persistence(config.persistence, idm)
        except psycopg2.OperationalError as err:
            raise Exception("""If you are running in HGI's Farm environment, try setting SANDMAN_FARM_TEST to '1'
            By deafult, this test uses .eg/sandmanrc, which maybe doesn't suit your testing environment""") from err
