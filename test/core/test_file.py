"""
Copyright (c) 2020, 2021 Genome Research Limited

Author: 
* Christopher Harrison <ch12@sanger.ac.uk>
* Piyush Ahuja <pa11@sanger.ac.uk>

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
from tempfile import TemporaryDirectory
from core import file, time, typing as T


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
        tmp_file.link_to(hardlink)

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

    def test_update_mtime(self) -> None:
        tmp_file = self._path / "foo"
        dt_now = time.now()

        file.update_mtime(tmp_file, dt_now)

        unix_time = time.timestamp(dt_now)
        self.assertEqual(tmp_file.stat().st_mtime, unix_time)

    def test_update_mtime_with_diff_tz(self) -> None:
        tmp_file = self._path / "foo"
        tz_dummy = time.timezone(time.timedelta(seconds=14400))
        time_dummy = time.datetime(2007, 12, 6, 15, 29, 43, 79060, tzinfo = tz_dummy)
        file.update_mtime(tmp_file, time_dummy)
        self.assertEqual(tmp_file.stat().st_mtime, time.timestamp(time_dummy))

   

if __name__ == "__main__":
    unittest.main()
