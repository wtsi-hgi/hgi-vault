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
from tempfile import TemporaryDirectory

from core import typing as T, idm as IdM
from core.utils import base64
from api.vault import _VaultFileKey


_DUMMY = T.Path("foo/bar/quux")
_B64_DUMMY = base64.encode(_DUMMY)

# For convenience
VFK = lambda inode, path: _VaultFileKey(inode=inode, path=path)
VFK_k = lambda path: _VaultFileKey(key_path=path)

class TestVaultFileKey(unittest.TestCase):
    def test_constructor(self):
        self.assertEqual(VFK(0x1,    _DUMMY).path, T.Path(f"01-{_B64_DUMMY}"))
        self.assertEqual(VFK(0x1,    _DUMMY).path, T.Path(f"01-{_B64_DUMMY}"))
        self.assertEqual(VFK(0x12,   _DUMMY).path, T.Path(f"12-{_B64_DUMMY}"))
        self.assertEqual(VFK(0x123,  _DUMMY).path, T.Path(f"01/23-{_B64_DUMMY}"))
        self.assertEqual(VFK(0x1234, _DUMMY).path, T.Path(f"12/34-{_B64_DUMMY}"))

        self.assertRaises(TypeError, _VaultFileKey)
        self.assertRaises(TypeError, _VaultFileKey, inode=123)
        self.assertRaises(TypeError, _VaultFileKey, path=_DUMMY)
        self.assertRaises(TypeError, _VaultFileKey, inode=123, key_path=_DUMMY)
        self.assertRaises(TypeError, _VaultFileKey, path=_DUMMY, key_path=_DUMMY)
        self.assertRaises(TypeError, _VaultFileKey, inode=123, path=_DUMMY, key_path=_DUMMY)

    def test_resolve(self):
        self.assertEqual(VFK(0, _DUMMY).source, _DUMMY)
        self.assertEqual(VFK_k(T.Path(f"01-{_B64_DUMMY}")).source, _DUMMY)

    def test_equality(self):
        self.assertEqual(VFK(0x12,  _DUMMY), VFK_k(T.Path(f"12-{_B64_DUMMY}")))
        self.assertEqual(VFK(0x123, _DUMMY), VFK_k(T.Path(f"01/23-{_B64_DUMMY}")))


class _DummyUser(IdM.base.User):
    def __init__(self, uid):
        self._id = uid

class _DummyGroup(IdM.base.Group):
    _owner:_DummyUser
    _member:_DummyUser

    def __init__(self, gid, owner, member=None):
        self._id = gid
        self._owner = owner
        self._member = member or owner

    @property
    def owners(self):
        yield self._owner

    @property
    def members(self):
        yield self._member

class _DummyIdM(IdM.base.IdentityManager):
    _user:_DummyUser

    def __init__(self, dummy_uid):
        self._user = _DummyUser(dummy_uid)

    def user(self, uid):
        pass

    def group(self, gid):
        return _DummyGroup(gid, self._user)


# TODO Test Vault and VaultFile
# * Vault root setting
# * Vault and branch creation
# * Vault owners


if __name__ == "__main__":
    unittest.main()
