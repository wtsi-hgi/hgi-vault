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
from core.utils import base64, human_size, human_time, umask


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

    def test_altchars(self):
        self.assertEqual(base64.encode(b"\xfa"), "+g==")
        self.assertEqual(base64.encode(b"\xff"), "_w==")

        self.assertEqual(base64.decode("+g=="), b"\xfa")
        self.assertEqual(base64.decode("_w=="), b"\xff")


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


class TestHumanFormat(unittest.TestCase):
    def test_size_iec(self):
        # NOTE No threshold testing
        self.assertEqual(human_size(0),          "0 ")
        self.assertEqual(human_size(800),        "800 ")
        self.assertEqual(human_size(1024 * 0.9), "0.9 Ki")
        self.assertEqual(human_size(1024),       "1 Ki")
        self.assertEqual(human_size(1024 * 1.5), "1.5 Ki")
        self.assertEqual(human_size(1024 ** 2),  "1 Mi")
        self.assertEqual(human_size(1024 ** 3),  "1 Gi")
        self.assertEqual(human_size(1024 ** 4),  "1 Ti")
        self.assertEqual(human_size(1024 ** 5),  "1 Pi")

    def test_size_si(self):
        # NOTE No threshold testing
        self.assertEqual(human_size(0, 1000),          "0 ")
        self.assertEqual(human_size(800, 1000),        "800 ")
        self.assertEqual(human_size(1000 * 0.9, 1000), "0.9 k")
        self.assertEqual(human_size(1000, 1000),       "1 k")
        self.assertEqual(human_size(1000 * 1.5, 1000), "1.5 k")
        self.assertEqual(human_size(1000 ** 2, 1000),  "1 M")
        self.assertEqual(human_size(1000 ** 3, 1000),  "1 G")
        self.assertEqual(human_size(1000 ** 4, 1000),  "1 T")
        self.assertEqual(human_size(1000 ** 5, 1000),  "1 P")

    def test_time(self):
        # NOTE No threshold testing
        self.assertEqual(human_time(0),                "less than 1 second")
        self.assertEqual(human_time(0.8),              "nearly 1 second")
        self.assertEqual(human_time(1),                "1 second")
        self.assertEqual(human_time(30),               "30 seconds")
        self.assertEqual(human_time(48),               "nearly 1 minute")
        self.assertEqual(human_time(60),               "1 minute")
        self.assertEqual(human_time(30 * 60),          "30 minutes")
        self.assertEqual(human_time(48 * 60),          "nearly 1 hour")
        self.assertEqual(human_time(60 * 60),          "1 hour")
        self.assertEqual(human_time(12 * 60 * 60),     "12 hours")
        self.assertEqual(human_time(20 * 60 * 60),     "nearly 1 day")
        self.assertEqual(human_time(24 * 60 * 60),     "1 day")
        self.assertEqual(human_time(2 * 24 * 60 * 60), "2 days")


if __name__ == "__main__":
    unittest.main()
