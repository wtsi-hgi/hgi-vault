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
from os import stat
from tempfile import NamedTemporaryFile

from core import file, typing as T


class TestFile(unittest.TestCase):
    _tmp:T.IO[bytes]

    def setUp(self) -> None:
        self._tmp = NamedTemporaryFile(delete=True)

    def tearDown(self) -> None:
        self._tmp.close()

    def test_inode_id(self) -> None:
        path = T.Path(self._tmp.name)
        inode_id = stat(path).st_ino

        self.assertEqual(file.inode_id(path), inode_id)


if __name__ == "__main__":
    unittest.main()
