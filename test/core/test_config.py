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

from __future__ import annotations

import os
from functools import singledispatchmethod
import unittest
from unittest.mock import PropertyMock, patch
from tempfile import TemporaryDirectory

from core import typing as T
from core.config import base, exception, utils


class DummyConfig(base.Config):

    @staticmethod
    def _build(source):
        return {"foo": "bar"}

    @property
    def _is_valid(self):
        return True


class TestUtils(unittest.TestCase):
    _tmp: TemporaryDirectory
    _cfg: T.Path

    def setUp(self):
        self._tmp = tmp = TemporaryDirectory()

        self._cfg = cfg = (T.Path(tmp.name) / "config").resolve()
        cfg.touch()
        os.environ["TEST_CONFIG"] = str(cfg)

    def tearDown(self):
        del os.environ["TEST_CONFIG"]
        self._tmp.cleanup()

    def test_path(self):
        cfg = self._cfg

        self.assertEqual(utils.path("TEST_CONFIG"), cfg)
        self.assertRaises(exception.ConfigurationNotFound,
                          utils.path, "NO_SUCH_ENVVAR")
        self.assertEqual(utils.path("NO_SUCH_ENVVAR", str(cfg)), cfg)
        self.assertRaises(exception.ConfigurationNotFound,
                          utils.path, "NO_SUCH_ENVVAR", "no/such/path")
        self.assertEqual(utils.path("NO_SUCH_ENVVAR",
                         "no/such/path", str(cfg)), cfg)


class TestBaseConfig(unittest.TestCase):
    def test_source(self) -> None:
        cfg = DummyConfig(0)
        self.assertEqual(cfg.foo, "bar")
        with self.assertRaises(exception.NoSuchSetting):
            _ = cfg.does_not_exist

    def test_invalid(self) -> None:
        with patch("test.core.test_config.DummyConfig._is_valid", new_callable=PropertyMock) as mock_valid:
            mock_valid.return_value = False
            self.assertRaises(exception.InvalidSemantics, DummyConfig, 0)

        self.assertRaises(exception.InvalidConfiguration, DummyConfig, None)

    def test_tree(self) -> None:
        cfg = DummyConfig({
            "foo": 123,
            "bar": [1, 2, 3],
            "quux": {
                "xyzzy": "hello",
                "test": {
                    "abc": "def"
                }
            }
        })

        self.assertEqual(cfg.foo, 123)
        self.assertEqual(cfg.bar, [1, 2, 3])
        self.assertEqual(cfg.quux.xyzzy, "hello")
        self.assertEqual(cfg.quux.test.abc, "def")


if __name__ == "__main__":
    unittest.main()
