"""
Copyright (c) 2021, 2022 Genome Research Limited

Authors:
    - Piyush Ahuja <pa11@sanger.ac.uk>
    - Michael Grace <mg38@sanger.ac.uk>
    - Sendu Bala <sb10@sanger.ac.uk>

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

from __future__ import annotations

import os
import unittest
from datetime import datetime, timedelta
from tempfile import TemporaryDirectory
from test.common import DummyGroup, DummyIDM, DummyUser
from unittest import mock
from unittest.mock import MagicMock

import core.file
from api.mail import MessageNamespace
from api.persistence import models
from api.persistence.engine import Persistence
from api.vault import Branch, Vault
from api.vault.key import VaultFileKey as VFK
from bin.common import Executable, clear_config_cache, generate_config
from bin.sandman.sweep import Sweeper
from bin.sandman.walk import BaseWalker, File
from core import idm as IdM
from core import time
from core import typing as T
from core.vault import exception as VaultExc
from eg.mock_mailer import MockMailer

config, idm = generate_config(Executable.SANDMAN)


class _DummyWalker(BaseWalker):
    def __init__(self, walk):
        self._walk = walk

    def files(self):
        yield from self._walk


class _DummyFile(models.File):
    @classmethod
    def FromFS(cls, path: T.Path, idm: IdM.base.IdentityManager,
               ctime: datetime = time.now(), atime: datetime = time.now(),
               mtime: datetime = time.now()) -> File:
        file = models.File.FromFS(path, idm)
        file.ctime = ctime
        file.atime = atime
        file.mtime = mtime
        return File(file)


def after_deletion_threshold() -> datetime:
    return time.now() - config.deletion.threshold - time.delta(seconds=1)


def make_file_seem_old(path: T.Path) -> File:
    long_ago = after_deletion_threshold()
    return _DummyFile.FromFS(path, ctime=long_ago,
                             mtime=long_ago, atime=long_ago, idm=DummyIDM(config))


def make_file_seem_old_but_read_recently(path: T.Path) -> File:
    long_ago = after_deletion_threshold()
    return _DummyFile.FromFS(path, idm, ctime=long_ago,
                             mtime=long_ago)


def make_file_seem_modified_long_ago(path: T.Path) -> File:
    long_ago = after_deletion_threshold()
    return _DummyFile.FromFS(path, idm, ctime=time.now(),
                             mtime=long_ago)


dummy_idm = DummyIDM(config)


class TestSweeper(unittest.TestCase):
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

        clear_config_cache()

        self._tmp = TemporaryDirectory()
        self.parent = path = T.Path(self._tmp.name).resolve() / "parent"
        self.some = path / "some"
        self.some.mkdir(parents=True, exist_ok=True)
        self.file_one = path / "file1"
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
        # Monkey patch Vault._find_root so that it returns the directory we
        # want
        Vault._find_root = MagicMock(return_value=self.parent)
        self.vault = Vault(relative_to=self.file_one, idm=dummy_idm)
        MockMailer.file_path = T.Path(self._tmp.name).resolve() / "mail"

    def tearDown(self) -> None:
        self._tmp.cleanup()
        del self.parent

    def determine_vault_path(self, path: T.Path, branch: Branch) -> T.Path:
        inode_no = path.stat().st_ino
        vault_relative_path = path.relative_to(self.parent)
        root = self.parent / ".vault" / branch
        return root / VFK(vault_relative_path, inode_no).path

    # Behavior:  Sweeper does not delete anything if its a dry run
    @mock.patch('bin.sandman.walk.idm', new=dummy_idm)
    @mock.patch('bin.vault._create_vault')
    def test_dryrun_basic(self, vault_mock):
        vault_file_one = self.vault.add(Branch.Keep, self.file_one)
        vault_file_two = self.vault.add(Branch.Archive, self.file_two)
        vault_file_three = self.vault.add(Branch.Limbo, self.file_three)

        walk = [(self.vault, make_file_seem_old(vault_file_one.path), VaultExc.PhysicalVaultFile()),
                (self.vault, make_file_seem_old(vault_file_two.path),
                 VaultExc.PhysicalVaultFile()),
                (self.vault, make_file_seem_old(vault_file_three.path),
                 VaultExc.PhysicalVaultFile()),
                (self.vault, make_file_seem_old(self.file_three), None)]
        dummy_walker = _DummyWalker(walk)
        dummy_persistence = MagicMock()
        Sweeper(dummy_walker, dummy_persistence, False, False)

        self.assertTrue(os.path.isfile(self.file_one))
        self.assertTrue(os.path.isfile(self.file_two))
        self.assertTrue(os.path.isfile(self.file_three))
        self.assertTrue(os.path.isfile(vault_file_one.path))
        self.assertTrue(os.path.isfile(vault_file_two.path))
        self.assertTrue(os.path.isfile(vault_file_three.path))

    # Behavior:  Sweeper does not delete staged files
    @mock.patch('bin.sandman.walk.idm', new=dummy_idm)
    @mock.patch('bin.vault._create_vault')
    def test_staged_not_deleted(self, vault_mock):
        vault_file_one = self.vault.add(Branch.Staged, self.file_one)
        self.file_one.unlink()

        walk = [(self.vault, make_file_seem_old(
            vault_file_one.path), VaultExc.PhysicalVaultFile())]
        dummy_walker = _DummyWalker(walk)
        dummy_persistence = MagicMock()
        Sweeper(dummy_walker, dummy_persistence, False, True)

        self.assertFalse(os.path.isfile(self.file_one))
        self.assertTrue(os.path.isfile(vault_file_one.path))

    # Behavior: When the source file of a vault file in Keep is deleted,
    # Sweeper does not delete the vault file in Keep if its a dry run
    @mock.patch('bin.sandman.walk.idm', new=dummy_idm)
    @mock.patch('bin.vault._create_vault')
    def test_keep_corruption_case_dry_run(self, vault_mock):
        vault_file_one = self.vault.add(Branch.Keep, self.file_one)
        vault_file_two = self.vault.add(Branch.Archive, self.file_two)
        vault_file_three = self.vault.add(Branch.Limbo, self.file_three)
        self.file_one.unlink()

        walk = [(self.vault, File.FromFS(vault_file_one.path), VaultExc.PhysicalVaultFile()),
                (self.vault, File.FromFS(vault_file_two.path),
                 VaultExc.PhysicalVaultFile()),
                (self.vault, File.FromFS(vault_file_three.path), VaultExc.PhysicalVaultFile())]
        dummy_walker = _DummyWalker(walk)
        dummy_persistence = MagicMock()
        Sweeper(dummy_walker, dummy_persistence, False, False)

        self.assertFalse(os.path.isfile(self.file_one))
        self.assertTrue(os.path.isfile(vault_file_one.path))
        self.assertTrue(os.path.isfile(self.file_two))
        self.assertTrue(os.path.isfile(vault_file_two.path))
        self.assertTrue(os.path.isfile(self.file_three))
        self.assertTrue(os.path.isfile(vault_file_three.path))

    # Behavior: When the source file of a vaultfile in Keep is deleted,
    # Sweeper deletes the vault file in Keep.
    @mock.patch('bin.sandman.walk.idm', new=dummy_idm)
    @mock.patch('bin.vault._create_vault')
    def test_keep_corruption_case_actual(self, vault_mock):
        vault_file_one = self.vault.add(Branch.Keep, self.file_one)
        vault_file_two = self.vault.add(Branch.Archive, self.file_two)
        vault_file_three = self.vault.add(Branch.Limbo, self.file_three)
        self.file_one.unlink()

        walk = [(self.vault, File.FromFS(vault_file_one.path), VaultExc.PhysicalVaultFile()),
                (self.vault, File.FromFS(vault_file_two.path),
                 VaultExc.PhysicalVaultFile()),
                (self.vault, File.FromFS(vault_file_three.path), VaultExc.PhysicalVaultFile())]
        dummy_walker = _DummyWalker(walk)
        dummy_persistence = MagicMock()
        Sweeper(dummy_walker, dummy_persistence, True, False)

        self.assertFalse(os.path.isfile(self.file_one))
        self.assertFalse(os.path.isfile(vault_file_one.path))
        self.assertTrue(os.path.isfile(self.file_two))
        self.assertTrue(os.path.isfile(vault_file_two.path))
        self.assertTrue(os.path.isfile(self.file_three))
        self.assertTrue(os.path.isfile(vault_file_three.path))

    # Behavior: When the source file of a vault file in Archive is deleted,
    # Sweeper does not delete the vault file if its a dry run
    @mock.patch('bin.sandman.walk.idm', new=dummy_idm)
    @mock.patch('bin.vault._create_vault')
    def test_archive_corruption_case_dry_run(self, vault_mock):
        vault_file_one = self.vault.add(Branch.Keep, self.file_one)
        vault_file_two = self.vault.add(Branch.Archive, self.file_two)
        vault_file_three = self.vault.add(Branch.Limbo, self.file_three)

        self.file_two.unlink()

        walk = [(self.vault, File.FromFS(vault_file_one.path), VaultExc.PhysicalVaultFile()),
                (self.vault, File.FromFS(vault_file_two.path),
                 VaultExc.PhysicalVaultFile()),
                (self.vault, File.FromFS(vault_file_three.path), VaultExc.PhysicalVaultFile())]
        dummy_walker = _DummyWalker(walk)
        dummy_persistence = MagicMock()
        Sweeper(dummy_walker, dummy_persistence, False, False)

        self.assertTrue(os.path.isfile(self.file_one))
        self.assertTrue(os.path.isfile(vault_file_one.path))
        self.assertFalse(os.path.isfile(self.file_two))
        self.assertTrue(os.path.isfile(vault_file_two.path))

        self.assertTrue(os.path.isfile(self.file_three))
        self.assertTrue(os.path.isfile(vault_file_three.path))

    # Behavior: When the source file of a vault file in Archive is deleted,
    # Sweeper deletes the vault file
    @mock.patch('bin.sandman.walk.idm', new=dummy_idm)
    @mock.patch('bin.vault._create_vault')
    def test_archive_source_deleted(self, vault_mock):
        vault_file_one = self.vault.add(Branch.Keep, self.file_one)
        vault_file_two = self.vault.add(Branch.Archive, self.file_two)
        vault_file_three = self.vault.add(Branch.Limbo, self.file_three)

        self.file_one.unlink()
        self.file_two.unlink()

        walk = [(self.vault, File.FromFS(vault_file_one.path), VaultExc.PhysicalVaultFile()),
                (self.vault, File.FromFS(vault_file_two.path),
                 VaultExc.PhysicalVaultFile()),
                (self.vault, File.FromFS(vault_file_three.path), VaultExc.PhysicalVaultFile())]
        dummy_walker = _DummyWalker(walk)
        dummy_persistence = MagicMock()

        Sweeper(dummy_walker, dummy_persistence, False, True)

        self.assertFalse(os.path.isfile(self.file_one))
        self.assertFalse(os.path.isfile(vault_file_one.path))
        self.assertFalse(os.path.isfile(self.file_two))
        self.assertFalse(os.path.isfile(vault_file_two.path))

        self.assertTrue(os.path.isfile(self.file_three))
        self.assertTrue(os.path.isfile(vault_file_three.path))

    # Behavior:
    # The vault file is in Stash, but has less than one hardlink: corruption is logged.
    # The vault file is in Staged, but has more than one hardlink: there is no corruption.
    # The vault file is in Limbo, but has more than one hardlink: corruption
    # is logged.
    @mock.patch('bin.sandman.walk.idm', new=dummy_idm)
    @mock.patch('bin.vault._create_vault')
    def test_archive_corruption_case_actual(self, vault_mock):
        vault_file_one = self.vault.add(Branch.Staged, self.file_one)
        vault_file_two = self.vault.add(Branch.Limbo, self.file_two)
        walk = [(self.vault, File.FromFS(vault_file_one.path),
                VaultExc.PhysicalVaultFile("File is in Staged and can have to hardlinks if the file was archived with the stash option")),
                (self.vault, File.FromFS(vault_file_two.path), VaultExc.PhysicalVaultFile("File is in Limbo and has two hardlinks"))]
        dummy_walker = _DummyWalker(walk)
        dummy_persistence = MagicMock()
        Sweeper(dummy_walker, dummy_persistence, True, True)

        self.assertTrue(os.path.isfile(self.file_one))
        self.assertTrue(os.path.isfile(vault_file_one.path))
        self.assertTrue(os.path.isfile(self.file_two))
        self.assertTrue(os.path.isfile(vault_file_two.path))

    # Behavior: Regular, tracked, non-vault file.
    # If the file is marked for Keep: nothing is done.
    # If the file has a corresponding hardlink in Staged, its NOT a case of VaultCorruption
    # If the file has a corresponding hardlink in Limbo, its a case of
    # VaultCorruption and yet nothing is done.
    @mock.patch('bin.sandman.walk.idm', new=dummy_idm)
    @mock.patch('bin.vault._create_vault')
    def test_tracked_file_non_archive(self, vault_mock):
        vault_file_one = self.vault.add(Branch.Keep, self.file_one)
        vault_file_two = self.vault.add(Branch.Staged, self.file_two)
        vault_file_three = self.vault.add(Branch.Limbo, self.file_three)

        walk = [(self.vault, File.FromFS(self.file_one), Branch.Keep), (self.vault, File.FromFS(self.file_two), Branch.Stash), (self.vault, File.FromFS(
            self.file_three), VaultExc.VaultCorruption(f"{self.file_three} is limboed in the vault in {self.vault.root}, but also exists outside the vault"))]
        dummy_walker = _DummyWalker(walk)
        dummy_persistence = MagicMock()
        Sweeper(dummy_walker, dummy_persistence, True, True)

        self.assertTrue(os.path.isfile(self.file_one))
        self.assertTrue(os.path.isfile(vault_file_one.path))
        self.assertTrue(os.path.isfile(self.file_two))
        self.assertTrue(os.path.isfile(vault_file_two.path))
        self.assertTrue(os.path.isfile(self.file_three))
        self.assertTrue(os.path.isfile(vault_file_three.path))

    # Behavior: Regular, tracked, non-vault file.
    # If the file has a corresponding hardlink in Archive, then the source
    # file is deleted and the archive file is moved to staged.
    @mock.patch('bin.sandman.walk.idm', new=dummy_idm)
    @mock.patch('bin.vault._create_vault')
    def test_tracked_file_archived(self, vault_mock):
        vault_file_one_archive = self.vault.add(Branch.Archive, self.file_one)

        walk = [(self.vault, File.FromFS(self.file_one), Branch.Archive)]

        vault_file_one_staged = self.determine_vault_path(
            self.file_one, Branch.Staged)

        dummy_walker = _DummyWalker(walk)
        dummy_persistence = MagicMock()
        Sweeper(dummy_walker, dummy_persistence, True, True)

        self.assertFalse(os.path.isfile(self.file_one))
        self.assertFalse(os.path.isfile(vault_file_one_archive.path))
        self.assertTrue(os.path.isfile(vault_file_one_staged))

    # Behavior: Regular, tracked, non-vault file.
    # If the file has a corresponding hardlink in Stash, then the source file
    # is NOT deleted and the stashed file is moved to staged.
    @mock.patch('bin.sandman.walk.idm', new=dummy_idm)
    @mock.patch('bin.vault._create_vault')
    def test_tracked_file_stashed(self, vault_mock):
        vault_file_one_stash = self.vault.add(Branch.Stash, self.file_one)

        walk = [(self.vault, File.FromFS(self.file_one), Branch.Stash)]

        vault_file_one_staged = self.determine_vault_path(
            self.file_one, Branch.Staged)

        dummy_walker = _DummyWalker(walk)
        dummy_persistence = MagicMock()
        Sweeper(dummy_walker, dummy_persistence, True, True)

        self.assertTrue(os.path.isfile(self.file_one))
        self.assertFalse(os.path.isfile(vault_file_one_stash.path))
        self.assertTrue(os.path.isfile(vault_file_one_staged))

    # Behavior: When a regular, untracked, non-vault file has been there for
    # more than the deletion threshold, and it has been notifed to somebody,
    # the source is deleted and a hardlink created in Limbo
    def test_deletion_threshold_passed_previously_notified(self):
        config, _ = generate_config(Executable.SANDMAN)
        walker = _DummyWalker(
            ((self.vault, make_file_seem_old(self.file_one), None),)
        )
        persistence = Persistence(config.persistence, DummyIDM(config))

        vault_file_path = self.determine_vault_path(
            self.file_one, Branch.Limbo)

        # Add a previous notification
        persistence.persist(models.File(self.file_one, 0, 0, 0, None, datetime.now(), datetime.now(), datetime.now(), DummyUser(0), DummyGroup(0)),
                            models.State.Warned(notified=True, tminus=timedelta(days=1)))

        Sweeper(walker, persistence, True, False, postman=MockMailer)

        # Check if the untracked file has been deleted
        self.assertFalse(os.path.isfile(self.file_one))
        # Check if the file has been added to Limbo
        self.assertTrue(os.path.isfile(vault_file_path))

    # Behavior: When a regular, untracked, non-vault file has been there for
    # more than the deletion threshold, but it has never been notified
    # to someone, the file remains, is notified to someone, and then
    # on the next run is deleted, the source is deleted and a hardlink
    # created in Limbo
    def test_deletion_threshold_passed_never_notified(self):
        config, _ = generate_config(Executable.SANDMAN)
        walker = _DummyWalker(
            ((self.vault, make_file_seem_old(self.file_one), None),))
        persistence = Persistence(config.persistence, DummyIDM(config))

        vault_file_path = self.determine_vault_path(
            self.file_one, Branch.Limbo)

        Sweeper(walker, persistence, True, False, postman=MockMailer)

        # Check if the untracked file has been deleted (it shouldn't be)
        self.assertTrue(os.path.isfile(self.file_one))
        # Check if the file has been added to Limbo (it shouldn't be)
        self.assertFalse(os.path.isfile(vault_file_path))

        # Theoretically, that now "sends" the notification
        # Let's run it again
        Sweeper(walker, persistence, True, False, postman=MockMailer)

        # Check untracked file has now been deleted
        self.assertFalse(os.path.isfile(self.file_one))
        # check the file has been added to limbo
        self.assertTrue(os.path.isfile(vault_file_path))

    # Behavior: When a regular, untracked, non-vault file has been modified
    # more than the deletion threshold ago, but read recently, the source is
    # not deleted and a hardlink is not created in Limbo
    @mock.patch('bin.sandman.walk.idm', new=dummy_idm)
    @mock.patch('bin.vault._create_vault')
    def test_deletion_threshold_not_passed_for_access(self, vault_mock):
        walk = [
            (self.vault, make_file_seem_old_but_read_recently(self.file_one), None)]
        dummy_walker = _DummyWalker(walk)
        dummy_persistence = MagicMock()

        vault_file_path = self.determine_vault_path(
            self.file_one, Branch.Limbo)

        Sweeper(dummy_walker, dummy_persistence, True, False)

        # Check if the untracked file has been deleted
        self.assertTrue(os.path.isfile(self.file_one))
        # Check if the file has been added to Limbo
        self.assertFalse(os.path.isfile(vault_file_path))

    # Behavior: When a regular, untracked, non-vault file has been modified
    # more than the deletion threshold ago, but created recently, the source
    # is not deleted and a hardlink is not created in Limbo
    @mock.patch('bin.sandman.walk.idm', new=dummy_idm)
    @mock.patch('bin.vault._create_vault')
    def test_deletion_threshold_not_passed_for_creation(self, vault_mock):
        walk = [
            (self.vault,
             make_file_seem_modified_long_ago(
                 self.file_one),
                None)]
        dummy_walker = _DummyWalker(walk)
        dummy_persistence = MagicMock()

        vault_file_path = self.determine_vault_path(
            self.file_one, Branch.Limbo)

        Sweeper(dummy_walker, dummy_persistence, True, False)

        # Check if the untracked file has been deleted
        self.assertTrue(os.path.isfile(self.file_one))
        # Check if the file has been added to Limbo
        self.assertFalse(os.path.isfile(vault_file_path))

    # Behavior: When a Limbo file has been there for more than the limbo
    # threshold, it is deleted
    @mock.patch('bin.sandman.walk.idm', new=dummy_idm)
    @mock.patch('bin.vault._create_vault')
    def test_limbo_deletion_threshold_passed(self, vault_mock):
        vault_file_one = self.vault.add(Branch.Limbo, self.file_one)
        self.file_one.unlink()

        walk = [(self.vault, make_file_seem_old(vault_file_one.path),
                 VaultExc.PhysicalVaultFile("File is in Limbo"))]
        dummy_walker = _DummyWalker(walk)
        dummy_persistence = MagicMock()
        Sweeper(dummy_walker, dummy_persistence, True, False)

        self.assertFalse(os.path.isfile(self.file_one))
        self.assertFalse(os.path.isfile(vault_file_one.path))

    # Behavior: When a Limbo file was modifed more than the limbo threshold
    # ago, but read recently, it is not deleted
    @mock.patch('bin.sandman.walk.idm', new=dummy_idm)
    @mock.patch('bin.vault._create_vault')
    def test_limbo_deletion_threshold_not_passed_for_access(self, vault_mock):
        vault_file_one = self.vault.add(Branch.Limbo, self.file_one)
        self.file_one.unlink()

        walk = [(self.vault, make_file_seem_old_but_read_recently(
            vault_file_one.path), VaultExc.PhysicalVaultFile("File is in Limbo"))]
        dummy_walker = _DummyWalker(walk)
        dummy_persistence = MagicMock()
        Sweeper(dummy_walker, dummy_persistence, True, False)

        self.assertFalse(os.path.isfile(self.file_one))
        self.assertTrue(os.path.isfile(vault_file_one.path))

    # Behavior: When a Limbo file has been there for less than the limbo
    # threshold, it is not deleted
    @mock.patch('bin.sandman.walk.idm', new=dummy_idm)
    @mock.patch('bin.vault._create_vault')
    def test_limbo_deletion_threshold_not_passed(self, vault_mock):
        vault_file_one = self.vault.add(Branch.Limbo, self.file_one)
        new_time = time.now() - config.deletion.limbo + time.delta(seconds=1)
        self.file_one.unlink()

        walk = [(self.vault, _DummyFile.FromFS(vault_file_one.path, idm, ctime=new_time,
                 mtime=new_time, atime=new_time), VaultExc.PhysicalVaultFile("File is in Limbo"))]
        dummy_walker = _DummyWalker(walk)
        dummy_persistence = MagicMock()
        Sweeper(dummy_walker, dummy_persistence, True, False)

        self.assertFalse(os.path.isfile(self.file_one))
        self.assertTrue(os.path.isfile(vault_file_one.path))

    def test_unactionable_file_wont_be_actioned(self):
        """Gets the Sweeper to try and action a file
        with issues that can't be corrected by wrstat. The file won't be
        actionable, and it should throw the exception.

        `can_add`'s owned-by-root criteria will throw this exception.
        """
        with mock.patch('api.vault.VaultFile.source') as source:
            source.stat.return_value.st_uid = 0
            dummy_walker = _DummyWalker(
                [(self.vault, File.FromFS(self.file_one), None)])
            dummy_persistence = MagicMock()
            self.assertRaises(core.file.exception.UnactionableFile,
                              lambda: Sweeper(dummy_walker, dummy_persistence, True, True))

    def test_bad_permissions_file_skipped(self):
        """Gets the Sweeper to try and action a file
        with the wrong permissions. The file won't be actionable,
        and it should be skipped.
        """
        dummy_walker = _DummyWalker(
            [(self.vault, make_file_seem_old(self.wrong_perms), None)])
        dummy_persistence = MagicMock()
        Sweeper(dummy_walker, dummy_persistence, True, True)

        vault_file_path = self.determine_vault_path(
            self.wrong_perms, Branch.Limbo)

        self.assertTrue(os.path.isfile(self.wrong_perms))
        self.assertFalse(os.path.isfile(vault_file_path))

    def test_only_archiving_doesnt_delete_expired_files(self):
        """runs the sweeper with archving but not fully weaponised

        files marked as archive or stashed should be dealt with, but
        files that are simply expired shouldn't be touched"""

        _archive_vault_file = self.vault.add(Branch.Archive, self.file_one)
        _stash_vault_file = self.vault.add(Branch.Stash, self.file_two)

        _archived_file_staged_path = self.determine_vault_path(
            self.file_one, Branch.Staged)
        _stashed_file_staged_path = self.determine_vault_path(
            self.file_two, Branch.Staged)

        _files = [
            (self.vault, File.FromFS(self.file_one), Branch.Archive),
            (self.vault, File.FromFS(self.file_two), Branch.Stash),
            (self.vault, make_file_seem_old(self.file_three), None)
        ]

        # run twice to give deletion opportunity to files not previously warned
        Sweeper(
            _DummyWalker(_files),
            MagicMock(),
            weaponised=False,
            archive=True)

        # archived file gone by this point
        Sweeper(_DummyWalker(_files[1:]), MagicMock(),
                weaponised=False, archive=True)

        self.assertFalse(os.path.isfile(self.file_one))
        self.assertTrue(os.path.isfile(self.file_two))
        self.assertTrue(os.path.isfile(self.file_three))

        self.assertFalse(os.path.isfile(_archive_vault_file.path))
        self.assertFalse(os.path.isfile(_stash_vault_file.path))

        self.assertTrue(os.path.isfile(_archived_file_staged_path))
        self.assertTrue(os.path.isfile(_stashed_file_staged_path))

    def test_only_deleting_doesnt_touch_archive_files(self):
        _archive_vault_file = self.vault.add(Branch.Archive, self.file_one)
        _stash_vault_file = self.vault.add(Branch.Stash, self.file_two)

        _archived_file_staged_path = self.determine_vault_path(
            self.file_one, Branch.Staged)
        _stashed_file_staged_path = self.determine_vault_path(
            self.file_two, Branch.Staged)

        _walker = _DummyWalker([
            (self.vault, File.FromFS(self.file_one), Branch.Archive),
            (self.vault, File.FromFS(self.file_two), Branch.Stash),
            (self.vault, make_file_seem_old(self.file_three), None)
        ])

        _persistence = Persistence(config.persistence, DummyIDM(config))

        # run twice to ensure deletion of files not previously warned
        Sweeper(
            _walker,
            _persistence,
            weaponised=True,
            archive=False,
            postman=MockMailer)
        Sweeper(
            _walker,
            _persistence,
            weaponised=True,
            archive=False,
            postman=MockMailer)

        self.assertTrue(os.path.isfile(self.file_one))
        self.assertTrue(os.path.isfile(self.file_two))
        self.assertFalse(os.path.isfile(self.file_three))

        self.assertTrue(os.path.isfile(_archive_vault_file.path))
        self.assertTrue(os.path.isfile(_stash_vault_file.path))

        self.assertFalse(os.path.isfile(_archived_file_staged_path))
        self.assertFalse(os.path.isfile(_stashed_file_staged_path))


class TestEmailStakeholders(unittest.TestCase):

    def setUp(self) -> None:
        self.config, _ = generate_config(Executable.SANDMAN)

        self._tmp = TemporaryDirectory()
        self.parent = path = T.Path(self._tmp.name).resolve() / "parent"
        self.some = path / "some"
        self.some.mkdir(parents=True, exist_ok=True)
        self.file_one = path / "file1"

        self.file_one.touch()

        self.file_one.chmod(0o660)
        self.parent.chmod(0o330)
        self.some.chmod(0o330)

        Vault._find_root = MagicMock(return_value=self.parent)
        self.vault = Vault(relative_to=self.file_one, idm=dummy_idm)

        MockMailer.file_path = T.Path(self._tmp.name).resolve() / "mail"

    def tearDown(self) -> None:
        clear_config_cache()
        MockMailer.clean()

    def test_emails_stakeholders_warnings(self):
        """We're going to get a file close to the threshold,
        and then check if the email that is generated mentions
        the right information
        """
        new_time: T.DateTime = time.now() - self.config.deletion.threshold + \
            max(self.config.deletion.warnings) - time.delta(seconds=1)
        walker = _DummyWalker([(self.vault, _DummyFile.FromFS(
            self.file_one, idm=DummyIDM(self.config), ctime=new_time, mtime=new_time, atime=new_time), None)])
        Sweeper(walker, Persistence(self.config.persistence, DummyIDM(self.config)), True, False,
                MockMailer)  # this will make the email

        sent_emails = MockMailer.get_sent_mail(
            subject=MessageNamespace.WarnedEmail.subject)
        # the file should be in the emails of as many warnings as we get
        self.assertEqual(len({x for x in sent_emails if str(
            self.file_one) in x.body}), len(config.deletion.warnings) - 1)

    def test_emails_stakeholders_archival(self):
        """We're going to archive a file"""
        self.vault.add(Branch.Archive, self.file_one)
        walker = _DummyWalker([(self.vault, _DummyFile.FromFS(
            self.file_one, idm=DummyIDM(self.config)), Branch.Archive)])

        Sweeper(walker, Persistence(self.config.persistence,
                DummyIDM(self.config)), False, True, MockMailer)

        sent_emails = MockMailer.get_sent_mail(
            subject=MessageNamespace.StagedEmail.subject)
        self.assertTrue(any(self.file_one.name in x.body for x in sent_emails))

    def test_emails_stakeholders_urgent(self):
        """We're going to get a file notified last minute"""
        new_time: T.TimeDelta = time.now() - self.config.deletion.threshold - \
            time.delta(days=1)
        walker = _DummyWalker([(self.vault, _DummyFile.FromFS(self.file_one, idm=DummyIDM(
            self.config), ctime=new_time, mtime=new_time, atime=new_time), None)])
        Sweeper(walker, Persistence(self.config.persistence,
                DummyIDM(self.config)), True, False, MockMailer)

        sent_emails = MockMailer.get_sent_mail(
            subject=MessageNamespace.UrgentEmail.subject)
        self.assertTrue(any(self.file_one.name in x.body for x in sent_emails))

    def test_emails_stakeholders_deletion(self):
        """We're going to get some files deleted (need to run sweeper
        twice for this - urgent email gets sent first time)"""
        new_time: T.TimeDelta = time.now() - self.config.deletion.threshold - \
            time.delta(days=1)
        walker = _DummyWalker([(self.vault, _DummyFile.FromFS(self.file_one, idm=DummyIDM(
            self.config), ctime=new_time, mtime=new_time, atime=new_time), None)])

        # have to do this twice, cause the first time will send an urgent email
        Sweeper(walker, Persistence(self.config.persistence,
                DummyIDM(self.config)), True, False, MockMailer)
        Sweeper(walker, Persistence(self.config.persistence,
                DummyIDM(self.config)), True, False, MockMailer)

        sent_emails = MockMailer.get_sent_mail(
            subject=MessageNamespace.DeletedEmail.subject)
        self.assertTrue(any(self.file_one.name in x.body for x in sent_emails))

    def test_emails_stakeholders_many_files(self):
        """we're going to put a lot of files in an urgent email,
        and check they don't end up in the message body, but in
        an attachment"""

        _files = []
        for i in range(int(self.config.email.max_filelist_in_body) + 1):
            # create some files
            _f = self.parent / f"file{i}"
            _f.touch()
            _f.chmod(0o660)
            _files.append(_f)

        new_time: T.TimeDelta = time.now() - self.config.deletion.threshold - \
            time.delta(days=1)
        walker = _DummyWalker([(self.vault, _DummyFile.FromFS(_file, idm=DummyIDM(
            self.config), ctime=new_time, mtime=new_time, atime=new_time), None) for _file in _files])
        Sweeper(walker, Persistence(self.config.persistence,
                DummyIDM(self.config)), True, False, MockMailer)

        # check its not in the body of the email
        sent_emails = MockMailer.get_sent_mail(
            subject=MessageNamespace.UrgentEmail.subject)
        self.assertFalse(
            any(self.file_one.name in x.body for x in sent_emails))

        # check its in an attachment
        _found_in_attachments = False
        for email in sent_emails:
            if email.attachments is not None:
                for attachment in email.attachments:
                    if self.file_one.name in attachment:
                        _found_in_attachments = True
                        break
                else:
                    break

        self.assertTrue(_found_in_attachments)
