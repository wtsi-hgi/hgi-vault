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
from unittest.mock import MagicMock
from tempfile import TemporaryDirectory

from core import typing as T, idm as IdM
from core.vault import exception
from core.utils import base64
from api.vault import _VaultFileKey, VaultFile, Vault, Branch



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
   
    @property
    def name(self):
        raise NotImplementedError

    @property
    def email(self):
        raise NotImplementedError




class _DummyGroup(IdM.base.Group):
    _owner:_DummyUser
    _member:_DummyUser

    def __init__(self, gid, owner, member=None):
        self._id = gid
        self._owner = owner
        self._member = member or owner

    @property
    def owners(self):
        return iter([self._owner])

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

class TestVault(unittest.TestCase):
    _tmp: TemporaryDirectory
    _path: T.Path
    user_one = _DummyUser(1)
    user_two = _DummyUser(2)
    group_one = _DummyGroup(1, user_one)
    group_two = _DummyGroup(2, user_two)
    idm_user_one = _DummyIdM(1) 


    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self._path = path = T.Path(self._tmp.name).resolve()
    
        self.parent_dir = path / "parent_dir"
        self.child_dir_one = self.parent_dir / "child_dir_one"
        self.child_dir_two = self.parent_dir / "child_dir_two"
        self.tmp_file_a = self.child_dir_one / "a"
        self.tmp_file_b = self.child_dir_one / "b"
        self.tmp_file_c = self.child_dir_two / "c"
        self.child_dir_one.mkdir(parents=True, exist_ok=True)
        self.child_dir_two.mkdir(parents=True, exist_ok=True)
        self.tmp_file_a.touch()
        self.tmp_file_b.touch()
        # self.tmp_file_c.touch()
        # self.tmp_file_a.chmod(0o77)
        self.tmp_file_b.chmod(0o777)
        # self.tmp_file_c.chmod(0o777)
        self.child_dir_one.chmod(0o777)
        # self.parent_dir.chmod(0o777)

        Vault._find_root = MagicMock(return_value = self._path / T.Path("parent_dir/child_dir_one"))
        self.vault = Vault(relative_to = self._path / T.Path("parent_dir/child_dir_one/a"), idm = self.idm_user_one)

    def tearDown(self) -> None:
        self._tmp.cleanup()
        del self._path

    def test_constructor(self):

        # Test Location
        self.assertEqual(self.vault.location, self._path / T.Path("parent_dir/child_dir_one/.vault"))
        # Test Ownerships
        self.assertEqual(next(self.vault.owners), 1)
        self.assertEqual(self.vault.group, self.child_dir_one.stat().st_gid)
        # Test Branch Creation
        self.assertTrue(os.path.isdir(self._path / T.Path("parent_dir/child_dir_one/.vault/keep")))
        self.assertTrue(os.path.isdir(self._path / T.Path("parent_dir/child_dir_one/.vault/archive")))
        self.assertTrue(os.path.isdir(self._path / T.Path("parent_dir/child_dir_one/.vault/.staged")))
  
    def test_add(self):
        # Add child_dir_one/tmp_file_b to vault and check whether hard link exists at desired location. 
        self.vault.add(Branch.Keep, self.tmp_file_b)
        inode_no = self.tmp_file_b.stat().st_ino
        vault_file_key_path = VFK(inode_no, T.Path("b")).path
        vault_file_path = self._path / T.Path("parent_dir/child_dir_one/.vault/keep") / vault_file_key_path
        self.assertTrue(os.path.isfile(vault_file_path))    

    def test_list(self):
        self.vault.add(Branch.Keep, self.tmp_file_b)
        inode_no = self.tmp_file_b.stat().st_ino
        vault_file_path = self._path / T.Path("parent_dir/child_dir_one/.vault/keep") / VFK(inode_no, T.Path("b")).path  
        self.assertEqual(next(self.vault.list(Branch.Keep)), self.tmp_file_b)

    def test_remove_existing_file(self):
        self.vault.add(Branch.Keep, self.tmp_file_b)
        inode_no = self.tmp_file_b.stat().st_ino
        vault_file_key_path = VFK(inode_no, T.Path("b")).path
        vault_file_path = self._path / T.Path("parent_dir/child_dir_one/.vault/keep") / vault_file_key_path
        self.assertTrue(os.path.isfile(vault_file_path))    
        self.vault.remove(Branch.Keep, self.tmp_file_b)
        self.assertFalse(os.path.isfile(vault_file_path)) 

    def test_remove_not_existing_file(self):
        
        inode_no = self.tmp_file_b.stat().st_ino
        vault_file_key_path = VFK(inode_no, T.Path("b")).path
        vault_file_path = self._path / T.Path("parent_dir/child_dir_one/.vault/keep") / VFK(inode_no, T.Path("b")).path
        self.assertFalse(os.path.isfile(vault_file_path)) 
        self.vault.remove(Branch.Keep, self.tmp_file_b)
        self.assertFalse(os.path.isfile(vault_file_path)) 

    def test_existing_file_but_no_permission(self):
        
        inode_no = self.tmp_file_b.stat().st_ino
        vault_file_key_path = VFK(inode_no, T.Path("a")).path
        vault_file_path = self._path / T.Path("parent_dir/child_dir_one/.vault/keep") / VFK(inode_no, T.Path("a")).path
        self.assertRaises(exception.PermissionDenied, self.vault.add,Branch.Keep, self.tmp_file_a)
        self.assertRaises(exception.PermissionDenied, self.vault.remove,Branch.Keep, self.tmp_file_a)
       
        

# _DummyBranch, _DummyPath
# class TestVaultFile(unittest.TestCase):
#     def test_constructor(self):
#         self.assertEqual(VaultFile(vault= _DummyVault, branch = _DummyBranch, path = _DummyPath).path, T.Path(_DummyPath))
#         self.assertEqual(VaultFile(vault= _DummyVault, branch = _DummyBranch, path = _DummyPath).source, T.Path(_DummyPath))
#         self.assertEqual(VaultFile(vault= _DummyVault, branch = _DummyBranch, path = _DummyPath), _DummyVaultFile)
#         self.assertEqual(VaultFile(vault= _DummyVault, branch = _DummyBranch, path = _DummyPath).can_remove, True)
#         self.assertEqual(VaultFile(vault= _DummyVault, branch = _DummyBranch, path = _DummyPath).can_add, False))



if __name__ == "__main__":
    unittest.main()
