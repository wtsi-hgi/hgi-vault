"""
Copyright (c) 2021 Genome Research Limited

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
os.environ["VAULTRC"] = "eg/.vaultrc"
from tempfile import TemporaryDirectory
import unittest
from unittest import mock
from unittest.mock import MagicMock

from core import typing as T, idm as IdM, time, file
from core.vault import exception as VaultExc
import core.file
from api.config import Config
from api.vault import Branch, Vault
from api.vault.file import VaultFile
from api.vault.key import VaultFileKey as VFK
from bin.sandman.sweep import Sweeper
from bin.sandman.walk import BaseWalker, File
from bin.common import idm, config

class _DummyWalker(BaseWalker):
    def __init__(self, walk):
        self._walk = walk

    def files(self):
        yield from self._walk


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


dummy_idm = _DummyIdM(1)

class TestSweeper(unittest.TestCase):
    _tmp: TemporaryDirectory
    _path: T.Path

    def setUp(self) -> None:
        """
        The following tests will emulate the following directory structure
            +- parent/
                +- .vault
                +- some/
                |  +- file2
                |  +- file3
                +- file1
        """
        self._tmp = TemporaryDirectory()
        self.parent = path = T.Path(self._tmp.name).resolve() / "parent"
        self.some = path / "some"
        self.some.mkdir(parents=True, exist_ok=True)
        self.file_one = path /  "file1"
        self.file_two = path / self.some / "file2"
        self.file_three = path / self.some / "file3"
        self.wrong_perms = path / "wrong_perms_file"
        self.file_one.touch()
        self.file_two.touch()
        self.file_three.touch()
        self.wrong_perms.touch()
        # Ensure permissions are right for the vault add api to work.
        # The default permissions do not fly.
        # For files, ensure they are readable, writable and u=g (66x) is sufficient.
        # Parent directories should be executable and should have u=g(33x)
        self.file_one.chmod(0o660)
        self.file_two.chmod(0o660)
        self.file_three.chmod(0o660)
        self.wrong_perms.chmod(0o640)
        self.parent.chmod(0o330)
        self.some.chmod(0o330)
        # Monkey patch Vault._find_root so that it returns the directory we want
        Vault._find_root = MagicMock(return_value = self.parent)
        self.vault = Vault(relative_to = self.file_one, idm = idm)

    def tearDown(self) -> None:
        self._tmp.cleanup()
        del self.parent

    # Behavior:  Sweeper does not delete anything if its a dry run
    @mock.patch('bin.sandman.walk.idm', new = dummy_idm)
    @mock.patch('bin.vault._create_vault')
    def test_basic_case(self, vault_mock):
        vault_file_one = self.vault.add(Branch.Keep, self.file_one)
        vault_file_two = self.vault.add(Branch.Archive, self.file_two)
        vault_file_three = self.vault.add(Branch.Limbo, self.file_three)

        walk = [(self.vault, File.FromFS(vault_file_one.path), VaultExc.PhysicalVaultFile()),
        (self.vault, File.FromFS(vault_file_two.path), VaultExc.PhysicalVaultFile()),
            (self.vault, File.FromFS(vault_file_three.path), VaultExc.PhysicalVaultFile())]
        dummy_walker = _DummyWalker(walk)
        dummy_persistence = MagicMock()
        sweeper = Sweeper(dummy_walker, dummy_persistence, False)

        self.assertTrue(os.path.isfile(self.file_one))
        self.assertTrue(os.path.isfile(self.file_two))
        self.assertTrue(os.path.isfile(self.file_three))
        self.assertTrue(os.path.isfile(vault_file_one.path))
        self.assertTrue(os.path.isfile(vault_file_two.path))
        self.assertTrue(os.path.isfile(vault_file_three.path))

    # Behavior:  Sweeper does not delete staged files
    @mock.patch('bin.sandman.walk.idm', new = dummy_idm)
    @mock.patch('bin.vault._create_vault')
    def test_basic_case(self, vault_mock):
        vault_file_one = self.vault.add(Branch.Staged, self.file_one)
        self.file_one.unlink()

        walk = [(self.vault, File.FromFS(vault_file_one.path), VaultExc.PhysicalVaultFile())]
        dummy_walker = _DummyWalker(walk)
        dummy_persistence = MagicMock()
        sweeper = Sweeper(dummy_walker, dummy_persistence, False)

        self.assertFalse(os.path.isfile(self.file_one))
        self.assertTrue(os.path.isfile(vault_file_one.path))

    # Behavior: When the source file of a vault file in Keep is deleted, Sweeper does not delete the vault file in Keep if its a dry run
    @mock.patch('bin.sandman.walk.idm', new = dummy_idm)
    @mock.patch('bin.vault._create_vault')
    def test_keep_corruption_case_dry_run(self, vault_mock):
        vault_file_one = self.vault.add(Branch.Keep, self.file_one)
        vault_file_two = self.vault.add(Branch.Archive, self.file_two)
        vault_file_three = self.vault.add(Branch.Limbo, self.file_three)
        self.file_one.unlink()

        walk = [(self.vault, File.FromFS(vault_file_one.path), VaultExc.PhysicalVaultFile()),
        (self.vault, File.FromFS(vault_file_two.path), VaultExc.PhysicalVaultFile()),
            (self.vault, File.FromFS(vault_file_three.path), VaultExc.PhysicalVaultFile())]
        dummy_walker = _DummyWalker(walk)
        dummy_persistence = MagicMock()
        sweeper = Sweeper(dummy_walker, dummy_persistence, False)

        self.assertFalse(os.path.isfile(self.file_one))
        self.assertTrue(os.path.isfile(vault_file_one.path))
        self.assertTrue(os.path.isfile(self.file_two))
        self.assertTrue(os.path.isfile(vault_file_two.path))
        self.assertTrue(os.path.isfile(self.file_three))
        self.assertTrue(os.path.isfile(vault_file_three.path))

    # Behavior: When the source file of a vaultfile in Keep is deleted, Sweeper deletes the vault file in Keep.
    @mock.patch('bin.sandman.walk.idm', new = dummy_idm)
    @mock.patch('bin.vault._create_vault')
    def test_keep_corruption_case_actual(self, vault_mock):

        vault_file_one = self.vault.add(Branch.Keep, self.file_one)
        vault_file_two = self.vault.add(Branch.Archive, self.file_two)
        vault_file_three = self.vault.add(Branch.Limbo, self.file_three)
        self.file_one.unlink()

        walk = [(self.vault, File.FromFS(vault_file_one.path), VaultExc.PhysicalVaultFile()),
        (self.vault, File.FromFS(vault_file_two.path), VaultExc.PhysicalVaultFile()),
            (self.vault, File.FromFS(vault_file_three.path), VaultExc.PhysicalVaultFile())]
        dummy_walker = _DummyWalker(walk)
        dummy_persistence = MagicMock()
        sweeper = Sweeper(dummy_walker, dummy_persistence, True)

        self.assertFalse(os.path.isfile(self.file_one))
        self.assertFalse(os.path.isfile(vault_file_one.path))
        self.assertTrue(os.path.isfile(self.file_two))
        self.assertTrue(os.path.isfile(vault_file_two.path))
        self.assertTrue(os.path.isfile(self.file_three))
        self.assertTrue(os.path.isfile(vault_file_three.path))

    # Behavior: When the source file of a vault file in Archive is deleted, Sweeper does not delete the vault file if its a dry run
    @mock.patch('bin.sandman.walk.idm', new = dummy_idm)
    @mock.patch('bin.vault._create_vault')
    def test_archive_corruption_case_dry_run(self, vault_mock):
        vault_file_one = self.vault.add(Branch.Keep, self.file_one)
        vault_file_two = self.vault.add(Branch.Archive, self.file_two)
        vault_file_three = self.vault.add(Branch.Limbo, self.file_three)

        self.file_two.unlink()

        walk = [(self.vault, File.FromFS(vault_file_one.path), VaultExc.PhysicalVaultFile()),
        (self.vault, File.FromFS(vault_file_two.path), VaultExc.PhysicalVaultFile()),
            (self.vault, File.FromFS(vault_file_three.path), VaultExc.PhysicalVaultFile())]
        dummy_walker = _DummyWalker(walk)
        dummy_persistence = MagicMock()
        sweeper = Sweeper(dummy_walker, dummy_persistence, False)

        self.assertTrue(os.path.isfile(self.file_one))
        self.assertTrue(os.path.isfile(vault_file_one.path))
        self.assertFalse(os.path.isfile(self.file_two))
        self.assertTrue(os.path.isfile(vault_file_two.path))

        self.assertTrue(os.path.isfile(self.file_three))
        self.assertTrue(os.path.isfile(vault_file_three.path))

    # Behavior: When the source file of a vault file in Archive is deleted, Sweeper deletes the vault file
    @mock.patch('bin.sandman.walk.idm', new = dummy_idm)
    @mock.patch('bin.vault._create_vault')
    def test_archive_corruption_case_actual(self, vault_mock):
        vault_file_one = self.vault.add(Branch.Keep, self.file_one)
        vault_file_two = self.vault.add(Branch.Archive, self.file_two)
        vault_file_three = self.vault.add(Branch.Limbo, self.file_three)

        self.file_one.unlink()
        self.file_two.unlink()

        walk = [(self.vault, File.FromFS(vault_file_one.path), VaultExc.PhysicalVaultFile()),
        (self.vault, File.FromFS(vault_file_two.path), VaultExc.PhysicalVaultFile()),
            (self.vault, File.FromFS(vault_file_three.path), VaultExc.PhysicalVaultFile())]
        dummy_walker = _DummyWalker(walk)
        dummy_persistence = MagicMock()

        sweeper = Sweeper(dummy_walker, dummy_persistence, True)

        self.assertFalse(os.path.isfile(self.file_one))
        self.assertFalse(os.path.isfile(vault_file_one.path))
        self.assertFalse(os.path.isfile(self.file_two))
        self.assertFalse(os.path.isfile(vault_file_two.path))

        self.assertTrue(os.path.isfile(self.file_three))
        self.assertTrue(os.path.isfile(vault_file_three.path))

    # Behavior: 
    # The vault file is in Stash, but has less than one hardlink: corruption islogged.
    # The vault file is in Staged, but has more than one hardlink: there is no corruption.
    # The vault file is in Limbo, but has more than one hardlink: corruption is merely logged.
    @mock.patch('bin.sandman.walk.idm', new = dummy_idm)
    @mock.patch('bin.vault._create_vault')
    def test_archive_corruption_case_actual(self, vault_mock):

        vault_file_one = self.vault.add(Branch.Staged, self.file_one)
        vault_file_two = self.vault.add(Branch.Limbo, self.file_two)
        walk = [(self.vault, File.FromFS(vault_file_one.path), VaultExc.PhysicalVaultFile("File is in Staged and can have to hardlinks if the file was archived with the stash option")),
        (self.vault, File.FromFS(vault_file_two.path), VaultExc.PhysicalVaultFile("File is in Limbo and has two hardlinks"))]
        dummy_walker = _DummyWalker(walk)
        dummy_persistence = MagicMock()
        sweeper = Sweeper(dummy_walker, dummy_persistence, True)

        self.assertTrue(os.path.isfile(self.file_one))
        self.assertTrue(os.path.isfile(vault_file_one.path))
        self.assertTrue(os.path.isfile(self.file_two))
        self.assertTrue(os.path.isfile(vault_file_two.path))

   # Behavior: Regular, tracked, non-vault file. 
   # If the file is marked for Keep: nothing is done. 
   # If the file has a corresponding hardlink in Staged, its NOT a case of VaultCorruption
   # If the file has a corresponding hardlink in Limbo, its a case of VaultCorruption and yet nothing is done. 
    @mock.patch('bin.sandman.walk.idm', new = dummy_idm)
    @mock.patch('bin.vault._create_vault')
    def test_tracked_file_non_archive(self, vault_mock):
        vault_file_one = self.vault.add(Branch.Keep, self.file_one)
        vault_file_two = self.vault.add(Branch.Staged, self.file_two)
        vault_file_three = self.vault.add(Branch.Limbo, self.file_three)

        walk = [(self.vault, File.FromFS(self.file_one), Branch.Keep), (self.vault, File.FromFS(self.file_two), Branch.Stash), (self.vault, File.FromFS(self.file_three), VaultExc.VaultCorruption(f"{self.file_three} is limboed in the vault in {self.vault.root}, but also exists outside the vault"))]
        dummy_walker = _DummyWalker(walk)
        dummy_persistence = MagicMock()
        sweeper = Sweeper(dummy_walker, dummy_persistence, True)

        self.assertTrue(os.path.isfile(self.file_one))
        self.assertTrue(os.path.isfile(vault_file_one.path))
        self.assertTrue(os.path.isfile(self.file_two))
        self.assertTrue(os.path.isfile(vault_file_two.path))
        self.assertTrue(os.path.isfile(self.file_three))
        self.assertTrue(os.path.isfile(vault_file_three.path))

    # Behavior: Regular, tracked, non-vault file.
    # If the file has a corresponding hardlink in Archive, then the source file is deleted and the archive file is moved to staged.
    @mock.patch('bin.sandman.walk.idm', new = dummy_idm)
    @mock.patch('bin.vault._create_vault')
    def test_tracked_file_archived(self, vault_mock):

        vault_file_one_archive = self.vault.add(Branch.Archive, self.file_one)

        walk = [(self.vault, File.FromFS(self.file_one), Branch.Archive)]

        # Find the destination staged vault file for vault_file_three
        inode_no = self.file_one.stat().st_ino
        vault_relative_path = self.file_one.relative_to(self.parent)
        staged_root = self.parent/ ".vault"/ Branch.Staged
        vault_file_one_staged = staged_root / VFK(vault_relative_path, inode_no).path

        dummy_walker = _DummyWalker(walk)
        dummy_persistence = MagicMock()
        sweeper = Sweeper(dummy_walker, dummy_persistence, True)

        self.assertFalse(os.path.isfile(self.file_one))
        self.assertFalse(os.path.isfile(vault_file_one_archive.path))
        self.assertTrue(os.path.isfile(vault_file_one_staged))

    # Behavior: Regular, tracked, non-vault file.
    # If the file has a corresponding hardlink in Stash, then the source file is NOT deleted and the stashed file is moved to staged.
    @mock.patch('bin.sandman.walk.idm', new = dummy_idm)
    @mock.patch('bin.vault._create_vault')
    def test_tracked_file_stashed(self, vault_mock):

        vault_file_one_stash = self.vault.add(Branch.Stash, self.file_one)

        walk = [(self.vault, File.FromFS(self.file_one), Branch.Stash)]

        # Find the destination staged vault file for vault_file_three
        inode_no = self.file_one.stat().st_ino
        vault_relative_path = self.file_one.relative_to(self.parent)
        staged_root = self.parent/ ".vault"/ Branch.Staged
        vault_file_one_staged = staged_root / VFK(vault_relative_path, inode_no).path

        dummy_walker = _DummyWalker(walk)
        dummy_persistence = MagicMock()
        sweeper = Sweeper(dummy_walker, dummy_persistence, True)

        self.assertTrue(os.path.isfile(self.file_one))
        self.assertFalse(os.path.isfile(vault_file_one_stash.path))
        self.assertTrue(os.path.isfile(vault_file_one_staged))

    # Behavior: When a regular, untracked, non-vault file has been there for more than the deletion threshold, the source is deleted and a hardlink created in Limbo
    @mock.patch('bin.sandman.walk.idm', new = dummy_idm)
    @mock.patch('bin.vault._create_vault')
    def test_deletion_threshold_passed(self, vault_mock):
        new_time = time.now() - config.deletion.threshold - time.delta(seconds = 1)
        file.touch(self.file_one, mtime=new_time, atime=new_time)

        walk = [(self.vault, File.FromFS(self.file_one), None)]
        dummy_walker = _DummyWalker(walk)
        dummy_persistence = MagicMock()
        # Find the corresponding vault file
        inode_no = self.file_one.stat().st_ino
        vault_relative_path = self.file_one.relative_to(self.parent)
        limbo_root = self.parent/ ".vault"/ Branch.Limbo
        vault_file_path = limbo_root / VFK(vault_relative_path, inode_no).path

        sweeper = Sweeper(dummy_walker, dummy_persistence, True)
        # Check if the untracked file has been deleted
        self.assertFalse(os.path.isfile(self.file_one))
        # Check if the file has been added to Limbo
        self.assertTrue(os.path.isfile(vault_file_path))

    # Behavior: When a regular, untracked, non-vault file has been modified more than the deletion threshold ago, but read recently, the source is not deleted and a hardlink is not created in Limbo
    @mock.patch('bin.sandman.walk.idm', new = dummy_idm)
    @mock.patch('bin.vault._create_vault')
    def test_deletion_threshold_not_passed_for_access(self, vault_mock):
        new_mtime = time.now() - config.deletion.threshold - time.delta(seconds = 1)
        file.touch(self.file_one, mtime=new_mtime, atime=time.now())

        walk = [(self.vault, File.FromFS(self.file_one), None)]
        dummy_walker = _DummyWalker(walk)
        dummy_persistence = MagicMock()
        # Find the corresponding vault file
        inode_no = self.file_one.stat().st_ino
        vault_relative_path = self.file_one.relative_to(self.parent)
        limbo_root = self.parent/ ".vault"/ Branch.Limbo
        vault_file_path = limbo_root / VFK(vault_relative_path, inode_no).path

        sweeper = Sweeper(dummy_walker, dummy_persistence, True)
        # Check if the untracked file has been deleted
        self.assertTrue(os.path.isfile(self.file_one))
        # Check if the file has been added to Limbo
        self.assertFalse(os.path.isfile(vault_file_path))

    # Behavior: When a Limbo file has been there for more than the limbo threshold, it is deleted
    @mock.patch('bin.sandman.walk.idm', new = dummy_idm)
    @mock.patch('bin.vault._create_vault')
    def test_limbo_deletion_threshold_passed(self, vault_mock):
        vault_file_one = self.vault.add(Branch.Limbo, self.file_one)
        new_time = time.now() - config.deletion.limbo - time.delta(seconds = 1)
        file.touch(vault_file_one.path, mtime=new_time, atime=new_time)
        self.file_one.unlink()

        walk = [(self.vault, File.FromFS(vault_file_one.path), VaultExc.PhysicalVaultFile("File is in Limbo"))]
        dummy_walker = _DummyWalker(walk)
        dummy_persistence = MagicMock()
        sweeper = Sweeper(dummy_walker, dummy_persistence, True)

        self.assertFalse(os.path.isfile(self.file_one))
        self.assertFalse(os.path.isfile(vault_file_one.path))

    # Behavior: When a Limbo file was modifed more than the limbo threshold ago, but read recently, it is not deleted
    @mock.patch('bin.sandman.walk.idm', new = dummy_idm)
    @mock.patch('bin.vault._create_vault')
    def test_limbo_deletion_threshold_not_passed_for_access(self, vault_mock):
        vault_file_one = self.vault.add(Branch.Limbo, self.file_one)
        new_mtime = time.now() - config.deletion.limbo - time.delta(seconds = 1)
        file.touch(vault_file_one.path, mtime=new_mtime, atime=time.now())
        self.file_one.unlink()

        walk = [(self.vault, File.FromFS(vault_file_one.path), VaultExc.PhysicalVaultFile("File is in Limbo"))]
        dummy_walker = _DummyWalker(walk)
        dummy_persistence = MagicMock()
        sweeper = Sweeper(dummy_walker, dummy_persistence, True)

        self.assertFalse(os.path.isfile(self.file_one))
        self.assertTrue(os.path.isfile(vault_file_one.path))

    # Behavior: When a Limbo file has been there for less than the limbo threshold, it is not deleted
    @mock.patch('bin.sandman.walk.idm', new = dummy_idm)
    @mock.patch('bin.vault._create_vault')
    def test_limbo_deletion_threshold_not_passed(self, vault_mock):
        vault_file_one = self.vault.add(Branch.Limbo, self.file_one)
        new_time = time.now() - config.deletion.limbo + time.delta(seconds = 1)
        file.touch(vault_file_one.path, mtime=new_time, atime=new_time)
        self.file_one.unlink()

        walk = [(self.vault, File.FromFS(vault_file_one.path), VaultExc.PhysicalVaultFile("File is in Limbo"))]
        dummy_walker = _DummyWalker(walk)
        dummy_persistence = MagicMock()
        sweeper = Sweeper(dummy_walker, dummy_persistence, True)

        self.assertFalse(os.path.isfile(self.file_one))
        self.assertTrue(os.path.isfile(vault_file_one.path))

    def test_unactionable_file_wont_be_actioned(self):
        """Gets the Sweeper to try and action a file
        with the wrong permissions. The file won't be actionable,
        and it should throw the exception.

        Anything in the file `can_add` criteria will throw this
        exception.

        """
        dummy_walker = _DummyWalker([(self.vault, File.FromFS(self.wrong_perms), None)])
        dummy_persistence = MagicMock()
        self.assertRaises(core.file.exception.UnactionableFile, lambda: Sweeper(dummy_walker, dummy_persistence, True))
