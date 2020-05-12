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

import os
import unittest
from sys import version_info
from tempfile import TemporaryDirectory

from core import file, typing as T


class TestFile(unittest.TestCase):
    # NOTE These tests are somewhat pointless
    _tmp:TemporaryDirectory
    _path:T.Path

    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self._path = path = T.Path(self._tmp.name)

        tmp_file = path / "foo"
        tmp_file.touch()

        symlink = path / "bar"
        symlink.symlink_to(tmp_file)

        hardlink = path / "quux"
        if version_info < (3, 8):
            os.link(tmp_file, hardlink)
        else:
            # NOTE Path.link_to is only available from Python 3.8
            hardlink.link_to(tmp_file)

    def tearDown(self) -> None:
        self._tmp.cleanup()
        del self._path

    def test_inode_id(self) -> None:
        tmp_file = self._path / "foo"
        inode_id = tmp_file.stat().st_ino
        self.assertEqual(file.inode_id(tmp_file), inode_id)

        hardlink = self._path / "quux"
        self.assertEqual(file.inode_id(tmp_file), file.inode_id(hardlink))

    def test_is_regular(self) -> None:
        tmp_file = self._path / "foo"
        symlink  = self._path / "bar"

        self.assertTrue(file.is_regular(tmp_file))
        self.assertFalse(file.is_regular(T.Path("/")))
        self.assertFalse(file.is_regular(symlink))

    def test_hardlinks(self) -> None:
        tmp_file = self._path / "foo"
        self.assertTrue(file.hardlinks(tmp_file), 2)


if __name__ == "__main__":
    unittest.main()
