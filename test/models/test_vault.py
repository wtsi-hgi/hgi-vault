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
from tempfile import TemporaryDirectory

from core import typing as T
from core.utils import base64
from models.vault import _VaultFileKey


_DUMMY = "foo/bar/quux"
_DUMMY_FILE = T.Path(_DUMMY)
_DUMMY_ENC = base64.encode(_DUMMY)

# For convenience
VFK = lambda inode, path: _VaultFileKey(inode=inode, path=path)
VFK_k = lambda path: _VaultFileKey(key_path=path)

class TestVaultFileKey(unittest.TestCase):
    def test_constructor(self):
        self.assertEqual(VFK(0x1,    _DUMMY_FILE).path, T.Path(f"01-{_DUMMY_ENC}"))
        self.assertEqual(VFK(0x1,    _DUMMY_FILE).path, T.Path(f"01-{_DUMMY_ENC}"))
        self.assertEqual(VFK(0x12,   _DUMMY_FILE).path, T.Path(f"12-{_DUMMY_ENC}"))
        self.assertEqual(VFK(0x123,  _DUMMY_FILE).path, T.Path(f"01/23-{_DUMMY_ENC}"))
        self.assertEqual(VFK(0x1234, _DUMMY_FILE).path, T.Path(f"12/34-{_DUMMY_ENC}"))

        self.assertRaises(TypeError, _VaultFileKey)
        self.assertRaises(TypeError, _VaultFileKey, inode=123)
        self.assertRaises(TypeError, _VaultFileKey, path=_DUMMY_FILE)
        self.assertRaises(TypeError, _VaultFileKey, inode=123, key_path=_DUMMY_FILE)
        self.assertRaises(TypeError, _VaultFileKey, path=_DUMMY_FILE, key_path=_DUMMY_FILE)
        self.assertRaises(TypeError, _VaultFileKey, inode=123, path=_DUMMY_FILE, key_path=_DUMMY_FILE)

    def test_resolve(self):
        self.assertEqual(VFK(0, _DUMMY_FILE).source, _DUMMY_FILE)
        self.assertEqual(VFK_k(T.Path(f"01-{_DUMMY_ENC}")).source, _DUMMY_FILE)

    def test_equality(self):
        self.assertEqual(VFK(0x12,  _DUMMY_FILE), VFK_k(T.Path(f"12-{_DUMMY_ENC}")))
        self.assertEqual(VFK(0x123, _DUMMY_FILE), VFK_k(T.Path(f"01/23-{_DUMMY_ENC}")))

    # TODO Migrate to VaultFile testing
    #def test_alternate(self):
    #    key = VFK(0x1234, _DUMMY_FILE)

    #    alternate = "some/other/path"
    #    alt_key = VFK(0x1234, T.Path(alternate))

    #    with TemporaryDirectory() as tmp:
    #        tmp = T.Path(tmp)
    #        (tmp / "12").mkdir()

    #        # No alternate exists
    #        self.assertIsNone(key.alternate(tmp))

    #        # Original key exists
    #        original = f"12/34-{_DUMMY_ENC}"
    #        (tmp / original).touch()
    #        self.assertIsNone(key.alternate(tmp))

    #        # Create alternate
    #        alt_enc = f"12/34-{base64.encode(alternate)}"
    #        (tmp / original).rename(tmp / alt_enc)
    #        self.assertEqual(key.alternate(tmp), alt_key)


if __name__ == "__main__":
    unittest.main()
