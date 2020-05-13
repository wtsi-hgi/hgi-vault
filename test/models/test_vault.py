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
from unittest.mock import patch

from core import typing as T
from core.utils import base64
from models.vault import _VaultFileKey


class TestVaultFileKey(unittest.TestCase):
    @patch("core.file.inode_id")
    def test_constructor(self, mock_inode_id):
        dummy      = "foo/bar/quux"
        dummy_file = T.Path(dummy)
        b64_dummy  = base64.encode(dummy)

        mock_inode_id.return_value = 0x1
        self.assertEqual(_VaultFileKey(dummy_file).path,
                         T.Path(f"01-{b64_dummy}"))

        mock_inode_id.return_value = 0x12
        self.assertEqual(_VaultFileKey(dummy_file).path,
                         T.Path(f"12-{b64_dummy}"))

        mock_inode_id.return_value = 0x123
        self.assertEqual(_VaultFileKey(dummy_file).path,
                         T.Path(f"01/23-{b64_dummy}"))

        mock_inode_id.return_value = 0x1234
        self.assertEqual(_VaultFileKey(dummy_file).path,
                         T.Path(f"12/34-{b64_dummy}"))


if __name__ == "__main__":
    unittest.main()
