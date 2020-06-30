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

import unittest
from unittest.mock import PropertyMock, patch

from core import typing as T
from core.config import base, exception


class DummyConfig(base.Config):
    @staticmethod
    def build(source):
        return {"foo": "bar"}

    @property
    def is_valid(self):
        return True


class TestBaseConfig(unittest.TestCase):
    def test_source(self) -> None:
        cfg = DummyConfig(0)
        self.assertEqual(cfg.foo, "bar")
        with self.assertRaises(exception.NoSuchSetting):
            _ = cfg.does_not_exist

    def test_invalid(self) -> None:
        with patch("test.core.test_config.DummyConfig.is_valid", new_callable=PropertyMock) as mock_valid:
            mock_valid.return_value = False
            self.assertRaises(exception.InvalidConfiguration, DummyConfig, 0)

    def test_tree(self) -> None:
        cfg = DummyConfig(contents={
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
