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

import stat
import unittest
from dataclasses import dataclass
from tempfile import TemporaryDirectory

from core import typing as T
from core.utils import base64, umask


@dataclass
class _DUMMY:
    value:T.Stringable

    def __str__(self) -> str:
        return str(self.value)

class TestBase64(unittest.TestCase):
    def test_encode(self):
        self.assertEqual(base64.encode("foo"),         "Zm9v")
        self.assertEqual(base64.encode(b"foo"),        "Zm9v")
        self.assertEqual(base64.encode(_DUMMY("foo")), "Zm9v")

    def test_decode(self):
        self.assertEqual(base64.decode("Zm9v"),  b"foo")
        self.assertEqual(base64.decode(b"Zm9v"), b"foo")
        self.assertRaises(TypeError, base64.decode, 123)


S_IRWXA = stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO

class TestUmask(unittest.TestCase):
    _tmp:TemporaryDirectory

    def setUp(self):
        self._tmp = TemporaryDirectory()

    def tearDown(self):
        self._tmp.cleanup()

    def test_umask(self):
        tmp = T.Path(self._tmp.name)

        with umask(0):
            (zero := tmp / "zero").touch(S_IRWXA)
            self.assertEqual(zero.stat().st_mode & S_IRWXA, S_IRWXA)

        with umask(stat.S_IRWXG | stat.S_IRWXO):
            (user := tmp / "user").touch(S_IRWXA)
            self.assertEqual(user.stat().st_mode & S_IRWXA, stat.S_IRWXU)


if __name__ == "__main__":
    unittest.main()
