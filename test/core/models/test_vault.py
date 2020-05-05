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
from core.models import vault


class TestVault(unittest.TestCase):
    @patch("core.file.inode_id")
    def test_path_to_vault_key(self, mock_inode_id):
        dummy_file = "foo/bar"
        b64_dummy  = "Zm9vL2Jhcg=="

        mock_inode_id.return_value = 0x1
        self.assertEqual(vault._path_to_vault_key(dummy_file),
                         T.Path(f"01-{b64_dummy}"))

        mock_inode_id.return_value = 0x12
        self.assertEqual(vault._path_to_vault_key(dummy_file),
                         T.Path(f"12-{b64_dummy}"))

        mock_inode_id.return_value = 0x123
        self.assertEqual(vault._path_to_vault_key(dummy_file),
                         T.Path(f"01/23-{b64_dummy}"))

        mock_inode_id.return_value = 0x1234
        self.assertEqual(vault._path_to_vault_key(dummy_file),
                         T.Path(f"12/34-{b64_dummy}"))


if __name__ == "__main__":
    unittest.main()
