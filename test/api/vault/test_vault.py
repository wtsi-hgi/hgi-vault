"""
Copyright (c) 2020, 2021, 2022 Genome Research Limited

Authors:
    * Piyush Ahuja <pa11@sanger.ac.uk>
    * Michael Grace <mg38@sanger.ac.uk>

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
import stat
import unittest
from tempfile import TemporaryDirectory
from test.common import DummyIDM
from unittest.mock import MagicMock

from api.vault import Branch, Vault
from api.vault.file import VaultExc, VaultFile
from bin.common import Executable, generate_config
from core import typing as T
from core import file
from core.vault import exception

from .mock_file import MockOtherUserOwnedVaultFile, MockRootOwnedVaultFile
from .utils import VFK

# TODO Test Vault and VaultFile
# * Vault root setting
# * Vault and branch creation
# * Vault owners

config, _ = generate_config(Executable.VAULT)


class TestVaultFile(unittest.TestCase):

    def setUp(self) -> None:
        """
        The following tests will emulate the following directory structure
            +- tmp
                +- parent/
                    +- child_dir_one
                        +- a
                        +- b
                        +- perms_mod
                        +- perms_mod_dir
                            +- d
                        +-.vault/
                            +- keep
                            +- archive
                            ...
                    +- child_dir_two
                        +- c
        """
        _dummy_idm = DummyIDM(config)

        self._tmp = TemporaryDirectory()
        self._path = path = T.Path(self._tmp.name).resolve()
        # Form a directory hierarchy
        self.parent_dir = path / "parent_dir"
        self.child_dir_one = self.parent_dir / "child_dir_one"
        self.child_dir_two = self.parent_dir / "child_dir_two"
        self.tmp_file_a = self.child_dir_one / "a"
        self.tmp_file_b = self.child_dir_one / "b"
        self.tmp_file_c = self.child_dir_two / "c"
        self.perms_mod = self.child_dir_one / "perms_mod"
        self.perms_mod_dir = self.child_dir_one / "perms_mod_dir"
        self.tmp_file_d = self.perms_mod_dir / "d"
        self.child_dir_one.mkdir(parents=True, exist_ok=True)
        self.child_dir_two.mkdir(parents=True, exist_ok=True)
        self.perms_mod_dir.mkdir(parents=True, exist_ok=True)
        self.tmp_file_a.touch()
        self.tmp_file_b.touch()
        self.tmp_file_c.touch()
        self.perms_mod.touch()
        self.tmp_file_d.touch()
        # The permissions of the file ought to be least ug+rw; 660+
        # The user and group permissions of the file are equal;66* or 77*
        # Thefile's parent directory permissions are at least ug+wx. 330+
        self.tmp_file_a.chmod(0o660)
        self.tmp_file_b.chmod(0o644)
        self.tmp_file_c.chmod(0o777)
        self.child_dir_one.chmod(0o330)
        self.parent_dir.chmod(0o777)
        self.perms_mod_dir.chmod(0o777)
        self.tmp_file_d.chmod(0o664)
        Vault._find_root = MagicMock(
            return_value=self._path / T.Path("parent_dir/child_dir_one"))
        self.vault = Vault(relative_to=self._path /
                           T.Path("parent_dir/child_dir_one/a"), idm=_dummy_idm)

    def test_constructor(self):

        inode_no = self.tmp_file_a.stat().st_ino
        vault_file_key_path = VFK(T.Path("a"), inode_no).path
        vault_file_path = self._path / \
            T.Path("parent_dir/child_dir_one/.vault/keep") / \
            vault_file_key_path
        # Test source and path
        self.assertEqual(VaultFile(vault=self.vault, branch=Branch.Keep,
                         path=self.tmp_file_a).path, vault_file_path)
        self.assertEqual(VaultFile(vault=self.vault, branch=Branch.Keep,
                         path=self.tmp_file_a).source, self.tmp_file_a)

    def test_constructor_directory(self):
        self.assertRaises(exception.NotRegularFile, VaultFile,
                          self.vault, Branch.Keep, self.child_dir_one)

    def test_can_add_not_regular_file(self):
        """
        We shouldn't be able to add a file that isn't regular.
        It can be rejected in either the initialisation of the VaultFile
        or during the can_add checks. We're happy with either.
        """
        res = False
        try:
            res = VaultFile(self.vault, Branch.Keep,
                            self.child_dir_one).can_add
        except exception.NotRegularFile:
            res = True
        return res

    def _perms_and_check(self, u: int, g: int, o: int) -> bool:
        """
        Change the permissions of self.perms_mod to `ugo` as passed,
        and runs can_add against that file
        """
        self.perms_mod.chmod(int(f"{u}{g}{o}", 8))
        return VaultFile(self.vault, Branch.Keep, self.perms_mod).can_add

    def test_can_add_incorrect_permissions(self):
        """
        A file needs to be read writable by both user and group
        """
        self.assertTrue(all(
            not self._perms_and_check(*perms)
            for perms in (
                *((u, g, o) for u in range(6)
                  for g in range(8) for o in range(8)),
                *((u, g, o) for u in [6, 7] for g in range(6) for o in range(8))
            )
        ))

    def test_can_add_mismatching_permissions(self):
        """
            A files user and group permissions need to match
        """
        self.assertTrue(all(
            not self._perms_and_check(*perms)
            for perms in (
                *((6, 7, o) for o in range(8)),
                *((7, 6, o) for o in range(8))
            )
        ))

    def test_can_add_parent_directory_wrong_permissions(self):
        """The parent directory of the file also needs to
        have user and group write and execute permissions"""

        def _parent_dir_perms_and_check(u: int, g: int, o: int) -> bool:
            self.perms_mod_dir.chmod(int(f"{u}{g}{o}", 8))
            return VaultFile(self.vault, Branch.Keep, self.tmp_file_d).can_add

        self.assertTrue(all(
            not _parent_dir_perms_and_check(u, g, o)
            for u in range(8) for g in range(8) for o in range(8)
            # if user has x permission (we can't test otherwise)
            if u & stat.S_IXOTH
            and (not u & stat.S_IWOTH  # if user doesn't have write permission we test it
                 or (u & stat.S_IWOTH and not (g & stat.S_IXOTH and g & stat.S_IWOTH)))  # if user has write permission but group doesn't have w and x
        ))

    def test_can_add_owned_by_root(self):
        """A file owned by the root user can't be added to the Vault

        To simulate this, we use a MockRootOwnedVaultFile (inherits from VaultFile)
        """
        self.assertRaises(file.exception.UnactionableFile,
                          lambda: MockRootOwnedVaultFile(
                              self.vault, Branch.Keep, self.tmp_file_a).can_add)

    def test_can_add_not_owner_or_in_group(self):
        """A file can't be added to the Vault if we're not the owner
        or in the group

        To simulate this, we use a MockOtherUserOwnedVaultFile (inherits from VaultFile)
        """
        self.assertFalse(MockOtherUserOwnedVaultFile(
            self.vault, Branch.Keep, self.tmp_file_a).can_add)

    def test_can_add_all_good_to_add_file(self):
        """A file with all the right permissions should be able to be added"""
        self.assertTrue(
            VaultFile(self.vault, Branch.Keep, self.tmp_file_a), True)

    def test_can_add_incorrect_vault(self):
        # A file needs to be in the homogroupic subtree of the vault group.
        self.assertRaises(exception.IncorrectVault, VaultFile,
                          self.vault, Branch.Keep, self.tmp_file_c)

    def test_can_remove_added(self):
        self.vault.add(Branch.Keep, self.tmp_file_a)
        self.assertEqual(VaultFile(
            vault=self.vault, branch=Branch.Keep, path=self.tmp_file_a).can_remove, True)

    def test_can_remove_user_isnt_owner_or_vault_owner(self):
        """We can't remove from the vault if we're not an owner or vault owner

        We simulate this with MockOtherUserOwnedVaultFile (inherits from VaultFile)
        """
        self.vault.add(Branch.Keep, self.tmp_file_a)
        self.assertFalse(MockOtherUserOwnedVaultFile(
            self.vault, Branch.Keep, self.tmp_file_a).can_remove)

    def test_can_remove_not_added(self):
        self.assertEqual(VaultFile(
            vault=self.vault, branch=Branch.Keep, path=self.tmp_file_a).can_remove, True)

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

        _dummy_idm = DummyIDM(config)

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
        # Check that the file's parent directory permissions are at least
        # ug+wx. 330+

        # Default file permissions can be unsuitable for archiving, like 644
        # (rw-r--r--, where owner and group dont have same permissions.
        self.tmp_file_a.chmod(0o660)  # rw, rw, _
        self.tmp_file_b.chmod(0o644)  # rw, r, r
        self.tmp_file_c.chmod(0o777)  # rwx, rwx, rwx

        # Default parent dir permissions can be unsuitable for archiving, like
        # 755 -  write permissions are missing.
        self.child_dir_one.chmod(0o730)  # wx, wx, _
        self.parent_dir.chmod(0o777)  # rwx, rwx, rwx

        Vault._find_root = MagicMock(
            return_value=self._path / T.Path("parent_dir/child_dir_one"))
        self.vault = Vault(relative_to=self._path /
                           T.Path("parent_dir/child_dir_one/a"), idm=_dummy_idm)

    def tearDown(self) -> None:
        self._tmp.cleanup()
        del self._path

    def test_constructor(self):
        # Test Location
        self.assertEqual(self.vault.location, self._path /
                         T.Path("parent_dir/child_dir_one/.vault"))
        # Test Ownerships
        self.assertEqual(next(self.vault.owners), 1)
        self.assertEqual(self.vault.group, self.child_dir_one.stat().st_gid)
        # Test Branch Creation
        self.assertTrue(os.path.isdir(
            self._path / T.Path("parent_dir/child_dir_one/.vault/keep")))
        self.assertTrue(os.path.isdir(
            self._path / T.Path("parent_dir/child_dir_one/.vault/archive")))
        self.assertTrue(os.path.isdir(
            self._path / T.Path("parent_dir/child_dir_one/.vault/.staged")))

    def test_add(self):
        # Add child_dir_one/tmp_file_b to vault and check whether hard link
        # exists at desired location.
        self.vault.add(Branch.Keep, self.tmp_file_a)
        inode_no = self.tmp_file_a.stat().st_ino
        vault_file_key_path = VFK(T.Path("a"), inode_no).path
        vault_file_path = self._path / \
            T.Path("parent_dir/child_dir_one/.vault/keep") / \
            vault_file_key_path
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
        dummy_long = T.Path('this/path/is/going/to/be/much/much/much/much/much'
                            '/much/much/much/much/much/much/much/much/much/much/much/much/much'
                            '/much/much/much/much/much/much/much/much/much/much/much/much/much'
                            '/much/much/much/much/much/much/much/much/much/much/much/much/much'
                            '/longer/than/two/hundred/and/fifty/five/characters')
        # child_dir_one is the root of our vault
        self.long_subdirectory = self.child_dir_one / dummy_long
        self.long_subdirectory.mkdir(parents=True, exist_ok=True)
        self.tmp_file_d = self.long_subdirectory / "d"
        self.tmp_file_d.touch()

        # Subdirectories are made rwx for user so that os.walk is able to read
        # into it.

        for dirpath, dirname, filenames in os.walk(self.parent_dir):
            for momo in dirname:
                dname = T.Path(os.path.join(dirpath, momo))
                dname.chmod(0o730)
            for filename in filenames:
                fname = T.Path(os.path.join(dirpath, filename))
                fname.chmod(0o777)
        self.vault.add(Branch.Limbo, self.tmp_file_d)

    def test_add_incorrect_parent_perms(self):
        # Add child_dir_one/tmp_file_b to vault and check whether hard link
        # exists at desired location.
        self.child_dir_one.chmod(0o577)
        self.assertRaises(Exception, self.vault.add,
                          Branch.Keep, self.tmp_file_a)
        self.child_dir_one.chmod(0o677)
        self.assertRaises(Exception, self.vault.add,
                          Branch.Keep, self.tmp_file_a)
        self.child_dir_one.chmod(0o757)
        self.assertRaises(exception.PermissionDenied,
                          self.vault.add, Branch.Keep, self.tmp_file_a)
        self.child_dir_one.chmod(0o767)
        self.assertRaises(exception.PermissionDenied,
                          self.vault.add, Branch.Keep, self.tmp_file_a)
        self.child_dir_one.chmod(0o755)
        self.assertRaises(exception.PermissionDenied,
                          self.vault.add, Branch.Keep, self.tmp_file_a)

    def test_add_already_existing(self):
        self.vault.add(Branch.Keep, self.tmp_file_a)

        inode_no = self.tmp_file_a.stat().st_ino
        vault_file_key_path = VFK(T.Path("a"), inode_no).path
        vault_file_path = self._path / \
            T.Path("parent_dir/child_dir_one/.vault/keep") / \
            vault_file_key_path
        self.assertTrue(os.path.isfile(vault_file_path))
        # Add again
        self.vault.add(Branch.Keep, self.tmp_file_a)
        inode_no = self.tmp_file_a.stat().st_ino
        vault_file_key_path = VFK(T.Path("a"), inode_no).path
        vault_file_path = self._path / \
            T.Path("parent_dir/child_dir_one/.vault/keep") / \
            vault_file_key_path
        self.assertTrue(os.path.isfile(vault_file_path))

    def test_add_incorrect_permission(self):
        self.assertRaises(exception.PermissionDenied,
                          self.vault.add, Branch.Keep, self.tmp_file_b)

    def test_change_location_of_vaulted_file(self):
        self.child_of_child_dir_one = self.child_dir_one / "child_of_child_dir_one"
        self.child_of_child_dir_one.mkdir()
        self.child_of_child_dir_one.chmod(0o330)
        self.new_location_tmp_file_a = self.child_of_child_dir_one / "new_location_tmp_file_a"

        self.vault.add(Branch.Keep, self.tmp_file_a)
        inode_no_old = self.tmp_file_a.stat().st_ino
        vault_file_key_path_old = VFK(T.Path("a"), inode_no_old).path
        vault_file_path_old = self._path / \
            T.Path("parent_dir/child_dir_one/.vault/keep") / \
            vault_file_key_path_old
        self.assertTrue(os.path.isfile(vault_file_path_old))

        shutil.move(self.tmp_file_a, self.new_location_tmp_file_a)
        self.vault.add(Branch.Keep, self.new_location_tmp_file_a)

        inode_no = self.new_location_tmp_file_a.stat().st_ino
        vault_file_key_path = VFK(
            T.Path("child_of_child_dir_one") / "new_location_tmp_file_a", inode_no).path
        vault_file_path = self._path / \
            T.Path("parent_dir/child_dir_one/.vault/keep") / \
            vault_file_key_path
        self.assertTrue(os.path.isfile(vault_file_path))
        self.assertFalse(os.path.isfile(vault_file_path_old))

    def test_change_location_of_vaulted_file_outside(self):

        self.new_location_tmp_file_a = self.child_dir_two / "new_location_tmp_file_a"

        self.vault.add(Branch.Keep, self.tmp_file_a)
        inode_no_old = self.tmp_file_a.stat().st_ino
        vault_file_key_path_old = VFK(T.Path("a"), inode_no_old).path
        vault_file_path_old = self._path / \
            T.Path("parent_dir/child_dir_one/.vault/keep") / \
            vault_file_key_path_old
        self.assertTrue(os.path.isfile(vault_file_path_old))

        shutil.move(self.tmp_file_a, self.new_location_tmp_file_a)
        self.assertRaises(exception.IncorrectVault, self.vault.remove,
                          Branch.Keep, self.new_location_tmp_file_a)

    def test_add_directory(self):
        self.assertRaises(exception.NotRegularFile,
                          self.vault.add, Branch.Keep, self.child_dir_one)

    def test_add_change_location(self):
        # Add child_dir_one/tmp_file_b to vault and check whether hard link
        # exists at desired location.
        self.assertRaises(exception.NotRegularFile,
                          self.vault.add, Branch.Keep, self.child_dir_one)

    def test_list(self):
        self.vault.add(Branch.Keep, self.tmp_file_a)
        inode_no = self.tmp_file_a.stat().st_ino
        vault_file_path = self._path / \
            T.Path("parent_dir/child_dir_one/.vault/keep") / \
            VFK(T.Path("a"), inode_no).path
        self.assertEqual(next(self.vault.list(Branch.Keep)),
                         (self.tmp_file_a, vault_file_path))

    def test_remove_existing_file(self):
        self.vault.add(Branch.Keep, self.tmp_file_a)
        inode_no = self.tmp_file_a.stat().st_ino
        vault_file_key_path = VFK(T.Path("a"), inode_no).path
        vault_file_path = self._path / \
            T.Path("parent_dir/child_dir_one/.vault/keep") / \
            vault_file_key_path
        self.assertTrue(os.path.isfile(vault_file_path))
        self.vault.remove(Branch.Keep, self.tmp_file_a)
        self.assertFalse(os.path.isfile(vault_file_path))

    def test_remove_not_existing_file(self):
        inode_no = self.tmp_file_b.stat().st_ino
        vault_file_key_path = VFK(T.Path("a"), inode_no).path
        vault_file_path = self._path / \
            T.Path("parent_dir/child_dir_one/.vault/keep") / \
            VFK(T.Path("a"), inode_no).path
        self.assertFalse(os.path.isfile(vault_file_path))
        self.vault.remove(Branch.Keep, self.tmp_file_a)
        self.assertFalse(os.path.isfile(vault_file_path))

    def test_remove_directory(self):
        self.assertRaises(exception.NotRegularFile,
                          self.vault.remove, Branch.Keep, self.child_dir_one)

    def test_existing_file_but_incorrect_vault(self):
        self.assertRaises(exception.IncorrectVault,
                          self.vault.remove, Branch.Keep, self.tmp_file_c)

    def test_incorrect_parent_directory_permissions(self):
        self.assertRaises(exception.IncorrectVault,
                          self.vault.remove, Branch.Keep, self.tmp_file_c)

    # To test:
    # Remove raises PermissionDenied if the current user is not owner of the file or group and tries to add or remove (294-295, 419)
    # VaultConflict if a file exists at .vault, .vault/{keep, archive, staged, .audit} locations (339-340, 354-356)
    # Root finding (364-369)
    # if (group := self._idm.group(gid=self.group)) is None (380)


class TestCreatingVault(unittest.TestCase):

    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self._path = T.Path(self._tmp.name).resolve()
        self._path.chmod(0o770)
        Vault._find_root = lambda *_: self._path

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_create_vault_not_enough_group_owners(self):
        self.assertRaises(
            VaultExc.MinimumNumberOfOwnersNotMet,
            Vault, relative_to=self._path, idm=DummyIDM(
                config, num_grp_owners=int(config.min_group_owners) - 1
            )
        )

    def test_create_vault_enough_group_owners(self):
        # shouldn't raise exception

        # Minumum Required
        Vault(relative_to=self._path, idm=DummyIDM(
            config, num_grp_owners=int(config.min_group_owners)
        ))

        # More than Required
        Vault(relative_to=self._path, idm=DummyIDM(
            config, num_grp_owners=int(config.min_group_owners) + 1
        ))


if __name__ == "__main__":
    unittest.main()
