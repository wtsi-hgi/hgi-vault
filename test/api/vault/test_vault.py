"""
Copyright (c) 2020, 2021 Genome Research Limited

Author: Piyush Ahuja <pa11@sanger.ac.uk>

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
import shutil
import unittest
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock

from core import typing as T, idm as IdM
from core.vault import exception
from api.vault import Vault, Branch
from api.vault.file import VaultFile
from .utils import VFK

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
    def name(self):
        raise NotImplementedError

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

# class TestVaultFile(unittest.TestCase):
#     idm_user_one = _DummyIdM(1)

    def setUp(self) -> None:
        """
        The following tests will emulate the following directory structure
            +- tmp
                +- parent/
                    +- child_dir_one
                        +- a
                        +- b
                        +-.vault/
                            +- keep
                            +- archive
                            ...
                    +- child_dir_two
                        +- c
        """
        self._tmp = TemporaryDirectory()
        self._path = path = T.Path(self._tmp.name).resolve()
        # Form a directory hierarchy
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
        self.tmp_file_c.touch()
        # The permissions of the file ought to be least ug+rw; 660+
        # The user and group permissions of the file are equal;66* or 77*
        # Thefile's parent directory permissions are at least ug+wx. 330+
        self.tmp_file_a.chmod(0o660)
        self.tmp_file_b.chmod(0o644)
        self.tmp_file_c.chmod(0o777)
        self.child_dir_one.chmod(0o330)
        self.parent_dir.chmod(0o777)
        Vault._find_root = MagicMock(return_value = self._path / T.Path("parent_dir/child_dir_one"))
        self.vault = Vault(relative_to = self._path / T.Path("parent_dir/child_dir_one/a"), idm = self.idm_user_one)

    def test_constructor(self):

        inode_no = self.tmp_file_a.stat().st_ino
        vault_file_key_path = VFK(T.Path("a"), inode_no).path
        vault_file_path = self._path / T.Path("parent_dir/child_dir_one/.vault/keep") / vault_file_key_path
        # Test source and path
        self.assertEqual(VaultFile(vault= self.vault, branch = Branch.Keep, path = self.tmp_file_a).path, vault_file_path )
        self.assertEqual(VaultFile(vault= self.vault, branch = Branch.Keep, path = self.tmp_file_a).source, self.tmp_file_a)

    def test_constructor_directory(self):
        self.assertRaises(exception.NotRegularFile, VaultFile, self.vault, Branch.Keep, self.child_dir_one)

    def test_can_add_right_permission(self):
        # A file needs to have at least ug+rw permissions. Here tmp_file_a has 644 (default)
        self.assertEqual(VaultFile(vault= self.vault, branch = Branch.Keep, path = self.tmp_file_a).can_add, True)
        # A file needs to have at least ug+rw permissions. Here tmp_file_b has 644 (default)

    def test_can_add_incorrect_permission(self):
        # A file needs to have at least ug+rw permissions. Here tmp_file_a has 644 (default)
        self.assertEqual(VaultFile(vault= self.vault, branch = Branch.Keep, path = self.tmp_file_a).can_add, True)

    def test_can_not_regular_file(self):
        # A file needs to have at least ug+rw permissions. Here tmp_file_a has 644 (default)
        self.assertRaises(exception.NotRegularFile, VaultFile, self.vault, Branch.Keep, self.child_dir_one)

    def test_can_add_incorrect_vault(self):
        # A file needs to be in the homogroupic subtree of the vault group.
        self.assertRaises(exception.IncorrectVault, VaultFile, self.vault, Branch.Keep, self.tmp_file_c)

    def test_can_remove_added(self):
        self.vault.add(Branch.Keep, self.tmp_file_a)
        self.assertEqual(VaultFile(vault= self.vault, branch = Branch.Keep, path = self.tmp_file_a).can_remove, True)

    def test_can_remove_not_added(self):
        self.assertEqual(VaultFile(vault= self.vault, branch = Branch.Keep, path = self.tmp_file_a).can_remove, True)

    def tearDown(self) -> None:
        self._tmp.cleanup()
        del self._path


class TestVault(unittest.TestCase):
    _tmp: TemporaryDirectory
    _path: T.Path
    # user_one = _DummyUser(1)
    # user_two = _DummyUser(2)
    # group_one = _DummyGroup(1, user_one)
    # group_two = _DummyGroup(2, user_two)
    idm_user_one = _DummyIdM(1)

    def setUp(self) -> None:
        """
        The following tests will emulate the following directory structure
            +- tmp
                +- parent/
                    +- child_dir_one
                        +- a
                        +- b
                        +-.vault/
                            +- keep
                            +- archive
                            ...
                    +- child_dir_two
                        +- c
        """
        self._tmp = TemporaryDirectory()
        self._path = path = T.Path(self._tmp.name).resolve()

         # Form a directory hierarchy
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
        self.tmp_file_c.touch()

        # The following conditions should be checked upfront for each file and, if not satisfied, that action should fail for that file, logged appropriately:
        #     Check that the permissions of the file are at least ug+rw; 660+
        #     Check that the user and group permissions of the file are equal;66* or 77*
        #     Check that the file's parent directory permissions are at least ug+wx. 330+

        # Default file permissions can be unsuitable for archiving, like 644 (rw-r--r--, where owner and group dont have same permissions.
        self.tmp_file_a.chmod(0o660) # rw, rw, _
        self.tmp_file_b.chmod(0o644) # rw, r, r
        self.tmp_file_c.chmod(0o777) # rwx, rwx, rwx

        # Default parent dir permissions can be unsuitable for archiving, like 755 -  write permissions are missing.
        self.child_dir_one.chmod(0o730) # wx, wx, _
        self.parent_dir.chmod(0o777) # rwx, rwx, rwx

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
        self.vault.add(Branch.Keep, self.tmp_file_d)
        inode_no = self.tmp_file_a.stat().st_ino
        vault_file_key_path = VFK(T.Path("a"),inode_no).path
        vault_file_path = self._path / T.Path("parent_dir/child_dir_one/.vault/keep") / vault_file_key_path
        self.assertTrue(os.path.isfile(vault_file_path))

    def test_add_long(self):
        """
        A new directory tree (this/path/is/going/..) is added here, to test the case of long relative paths.
            +- tmp
                +- parent/
                    +- child_dir_one
                        +- a
                        +- b
                        + this/
                            + path/
                                + ....
                        +-.vault/
                            +- keep/
                            +- archive/
                            ...
                    +- child_dir_two
                        +- c
        """
        # File with really long relative path
        dummy_long = T.Path("this/path/is/going/to/be/much/much/much/much/much/much/much/much/much/much/much/much/much/much/much/much/much/much/much/much/much/much/much/much/much/much/much/much/much/much/much/much/much/much/much/much/much/much/much/much/much/much/much/much/longer/than/two/hundred/and/fifty/five/characters")
        # child_dir_one is the root of our vault
        self.long_subdirectory = self.child_dir_one / dummy_long
        self.long_subdirectory.mkdir(parents=True, exist_ok=True)
        self.tmp_file_d = self.long_subdirectory / "d"
        self.tmp_file_d.touch()

        # Subdirectories are made rwx for user so that os.walk is able to read into it.

        for dirpath, dirname, filenames in os.walk(self.parent_dir):
            for momo in dirname:
                dname = T.Path(os.path.join(dirpath,momo))
                dname.chmod(0o730)
            for filename in filenames:
                fname = T.Path(os.path.join(dirpath, filename))
                fname.chmod(0o777)
        self.vault.add(Branch.Limbo, self.tmp_file_d)

    def test_add_incorrect_parent_perms(self):
        # Add child_dir_one/tmp_file_b to vault and check whether hard link exists at desired location.
        self.child_dir_one.chmod(0o577)
        self.assertRaises(Exception, self.vault.add, Branch.Keep, self.tmp_file_a)
        self.child_dir_one.chmod(0o677)
        self.assertRaises(Exception, self.vault.add, Branch.Keep, self.tmp_file_a)
        self.child_dir_one.chmod(0o757)
        self.assertRaises(exception.PermissionDenied, self.vault.add, Branch.Keep, self.tmp_file_a)
        self.child_dir_one.chmod(0o767)
        self.assertRaises(exception.PermissionDenied, self.vault.add, Branch.Keep, self.tmp_file_a)
        self.child_dir_one.chmod(0o755)
        self.assertRaises(exception.PermissionDenied, self.vault.add, Branch.Keep, self.tmp_file_a)

    def test_add_already_existing(self):
        self.vault.add(Branch.Keep, self.tmp_file_a)

        inode_no = self.tmp_file_a.stat().st_ino
        vault_file_key_path = VFK(T.Path("a"), inode_no).path
        vault_file_path = self._path / T.Path("parent_dir/child_dir_one/.vault/keep") / vault_file_key_path
        self.assertTrue(os.path.isfile(vault_file_path))
        # Add again
        self.vault.add(Branch.Keep, self.tmp_file_a)
        inode_no = self.tmp_file_a.stat().st_ino
        vault_file_key_path = VFK( T.Path("a"), inode_no).path
        vault_file_path = self._path / T.Path("parent_dir/child_dir_one/.vault/keep") / vault_file_key_path
        self.assertTrue(os.path.isfile(vault_file_path))

    def test_add_incorrect_permission(self):
        self.assertRaises(exception.PermissionDenied, self.vault.add, Branch.Keep, self.tmp_file_b)

    def test_change_location_of_vaulted_file(self):
        self.child_of_child_dir_one = self.child_dir_one / "child_of_child_dir_one"
        self.child_of_child_dir_one.mkdir()
        self.child_of_child_dir_one.chmod(0o330)
        self.new_location_tmp_file_a = self.child_of_child_dir_one / "new_location_tmp_file_a"

        self.vault.add(Branch.Keep, self.tmp_file_a)
        inode_no_old = self.tmp_file_a.stat().st_ino
        vault_file_key_path_old= VFK( T.Path("a"), inode_no_old).path
        vault_file_path_old = self._path / T.Path("parent_dir/child_dir_one/.vault/keep") / vault_file_key_path_old
        self.assertTrue(os.path.isfile(vault_file_path_old))

        shutil.move(self.tmp_file_a, self.new_location_tmp_file_a)
        self.vault.add(Branch.Keep, self.new_location_tmp_file_a)

        inode_no = self.new_location_tmp_file_a.stat().st_ino
        vault_file_key_path= VFK( T.Path("child_of_child_dir_one") / "new_location_tmp_file_a", inode_no).path
        vault_file_path = self._path / T.Path("parent_dir/child_dir_one/.vault/keep") / vault_file_key_path
        self.assertTrue(os.path.isfile(vault_file_path))
        self.assertFalse(os.path.isfile(vault_file_path_old))

    def test_change_location_of_vaulted_file_outside(self):

        self.new_location_tmp_file_a = self.child_dir_two / "new_location_tmp_file_a"

        self.vault.add(Branch.Keep, self.tmp_file_a)
        inode_no_old = self.tmp_file_a.stat().st_ino
        vault_file_key_path_old= VFK(T.Path("a"), inode_no_old).path
        vault_file_path_old = self._path / T.Path("parent_dir/child_dir_one/.vault/keep") / vault_file_key_path_old
        self.assertTrue(os.path.isfile(vault_file_path_old))

        shutil.move(self.tmp_file_a, self.new_location_tmp_file_a)
        self.assertRaises(exception.IncorrectVault, self.vault.remove, Branch.Keep, self.new_location_tmp_file_a)

    def test_add_directory(self):
        self.assertRaises(exception.NotRegularFile, self.vault.add, Branch.Keep, self.child_dir_one)

    def test_add_change_location(self):
        # Add child_dir_one/tmp_file_b to vault and check whether hard link exists at desired location.
        self.assertRaises(exception.NotRegularFile, self.vault.add, Branch.Keep, self.child_dir_one)

    def test_list(self):
        self.vault.add(Branch.Keep, self.tmp_file_a)
        inode_no = self.tmp_file_a.stat().st_ino
        vault_file_path = self._path / T.Path("parent_dir/child_dir_one/.vault/keep") / VFK(T.Path("a"), inode_no).path
        self.assertEqual(next(self.vault.list(Branch.Keep)), self.tmp_file_a)

    def test_remove_existing_file(self):
        self.vault.add(Branch.Keep, self.tmp_file_a)
        inode_no = self.tmp_file_a.stat().st_ino
        vault_file_key_path = VFK(T.Path("a"), inode_no).path
        vault_file_path = self._path / T.Path("parent_dir/child_dir_one/.vault/keep") / vault_file_key_path
        self.assertTrue(os.path.isfile(vault_file_path))
        self.vault.remove(Branch.Keep, self.tmp_file_a)
        self.assertFalse(os.path.isfile(vault_file_path))

    def test_remove_not_existing_file(self):
        inode_no = self.tmp_file_b.stat().st_ino
        vault_file_key_path = VFK(T.Path("a"), inode_no).path
        vault_file_path = self._path / T.Path("parent_dir/child_dir_one/.vault/keep") / VFK(T.Path("a"), inode_no).path
        self.assertFalse(os.path.isfile(vault_file_path))
        self.vault.remove(Branch.Keep, self.tmp_file_a)
        self.assertFalse(os.path.isfile(vault_file_path))

    def test_remove_directory(self):
        self.assertRaises(exception.NotRegularFile, self.vault.remove, Branch.Keep, self.child_dir_one)

    def test_existing_file_but_incorrect_vault(self):
        self.assertRaises(exception.IncorrectVault, self.vault.remove, Branch.Keep, self.tmp_file_c)

    def test_incorrect_parent_directory_permissions(self):
        self.assertRaises(exception.IncorrectVault, self.vault.remove, Branch.Keep, self.tmp_file_c)

    # To test:
    # Remove raises PermissionDenied if the current user is not owner of the file or group and tries to add or remove (294-295, 419)
    # VaultConflict if a file exists at .vault, .vault/{keep, archive, staged, .audit} locations (339-340, 354-356)
    # Root finding (364-369)
    # if (group := self._idm.group(gid=self.group)) is None (380)

if __name__ == "__main__":
    unittest.main()
