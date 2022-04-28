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
from datetime import datetime
from api.persistence import models
from eg.mock_mailer import MockMailer
from bin.common import idm, config
from bin.sandman.walk import BaseWalker, File
from bin.sandman.sweep import Sweeper
from api.vault.key import VaultFileKey as VFK
from api.vault.file import VaultFile
from api.vault import Branch, Vault
from api.config import Config
from core.persistence import base as PersistenceBase, Filter as PersistenceFilter, GroupSummary
import core.file
from core.vault import exception as VaultExc
from core import typing as T, idm as IdM, time, file
from unittest.mock import MagicMock
from unittest import mock
import unittest
from tempfile import TemporaryDirectory

import os
os.environ["VAULTRC"] = "eg/.vaultrc"


class _DummyWalker(BaseWalker):
    def __init__(self, walk):
        self._walk = walk

    def files(self):
        yield from self._walk


class _DummyFile(models.File):
    @classmethod
    def FromFS(cls, path: T.Path, idm: IdM.base.IdentityManager, ctime: datetime, atime: datetime, mtime: datetime) -> File:
        file = models.File.FromFS(path, idm)
        file.ctime = ctime
        file.atime = atime
        file.mtime = mtime
        return File(file)


def after_deletion_threshold() -> datetime:
    return time.now() - config.deletion.threshold - time.delta(seconds=1)


def make_file_seem_old(path: T.Path) -> File:
    long_ago = after_deletion_threshold()
    return _DummyFile.FromFS(path, idm, ctime=long_ago, mtime=long_ago, atime=long_ago)


def make_file_seem_old_but_read_recently(path: T.Path) -> File:
    long_ago = after_deletion_threshold()
    return _DummyFile.FromFS(path, idm, ctime=long_ago, mtime=long_ago, atime=time.now())


def make_file_seem_modified_long_ago(path: T.Path) -> File:
    long_ago = after_deletion_threshold()
    return _DummyFile.FromFS(path, idm, ctime=time.now(), mtime=long_ago, atime=time.now())


class _DummyUser(IdM.base.User):
    def __init__(self, uid: int, name: T.Optional[str] = None, email: T.Optional[str] = None):
        self._id = uid
        self._name = name
        self._email = email

    @property
    def name(self):
        if self._name:
            return self._name
        raise NameError

    @property
    def email(self):
        if self._email:
            return self._email
        raise NameError


class _DummyGroup(IdM.base.Group):
    _owner: IdM.base.User
    _member: IdM.base.User

    def __init__(self, gid: int, owner: IdM.base.User, member: T.Optional[IdM.base.User] = None):
        self._id = gid
        self._owner = owner
        self._member = member or owner

    @property
    def name(self):
        return f"group-{self._owner.name}"

    @property
    def owners(self):
        return iter([self._owner])

    @property
    def members(self):
        yield self._member


_FileState = T.Tuple[PersistenceBase.File, PersistenceBase.State]


class _DummyPersistence(PersistenceBase.Persistence):

    def __init__(self, *_) -> None:
        self._files: T.List[_FileState] = []
        self._user: IdM.base.User = _DummyUser(
            os.getuid(), name="Test User", email="testEmail@test.com")

    def persist(self, file: PersistenceBase.File, state: PersistenceBase.State) -> None:
        self._files.append((file, state))

    @property
    def stakeholders(self) -> T.Iterator[IdM.base.User]:
        return iter((self._user,))

    def files(self, criteria: PersistenceFilter) -> PersistenceBase.FileCollection:
        user = self._user

        class _DummyFileCollection(PersistenceBase.FileCollection):

            def __init__(self, files: T.List[_FileState]):
                self._files = files

            def __enter__(self):
                return self

            def __exit__(self, *_) -> bool:
                return False

            @property
            def accumulator(self) -> T.Dict[IdM.base.Group, GroupSummary]:
                acc: T.Dict[IdM.base.Group, GroupSummary] = {}
                key = _DummyGroup(os.getgid(), user)
                for file, _ in self._files:
                    acc[key] = acc.get(key, GroupSummary(path=file.path, count=0, size=0)) \
                        + GroupSummary(path=file.path, count=1, size=file.size)
                return acc

            def _accumulate(self, *_) -> None:
                ...

            def __len__(self):
                return len(self._files)

            def __iter__(self):
                return iter(x[0] for x in self._files)

        return _DummyFileCollection([x for x in self._files if x[1] == criteria.state])

    def clean(self, *_) -> None:
        ...


class _DummyIdM(IdM.base.IdentityManager):
    _user: _DummyUser

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
        # Monkey patch Vault._find_root so that it returns the directory we want
        Vault._find_root = MagicMock(return_value=self.parent)
        self.vault = Vault(relative_to=self.file_one, idm=idm)

    def tearDown(self) -> None:
        self._tmp.cleanup()
        del self.parent

    def determine_vault_path(self, path, branch) -> T.Path:
        inode_no = path.stat().st_ino
        vault_relative_path = self.file_one.relative_to(self.parent)
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
        Sweeper(dummy_walker, dummy_persistence, False)

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
        Sweeper(dummy_walker, dummy_persistence, True)

        self.assertFalse(os.path.isfile(self.file_one))
        self.assertTrue(os.path.isfile(vault_file_one.path))

    # Behavior: When the source file of a vault file in Keep is deleted, Sweeper does not delete the vault file in Keep if its a dry run
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
        Sweeper(dummy_walker, dummy_persistence, False)

        self.assertFalse(os.path.isfile(self.file_one))
        self.assertTrue(os.path.isfile(vault_file_one.path))
        self.assertTrue(os.path.isfile(self.file_two))
        self.assertTrue(os.path.isfile(vault_file_two.path))
        self.assertTrue(os.path.isfile(self.file_three))
        self.assertTrue(os.path.isfile(vault_file_three.path))

    # Behavior: When the source file of a vaultfile in Keep is deleted, Sweeper deletes the vault file in Keep.
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
        Sweeper(dummy_walker, dummy_persistence, True)

        self.assertFalse(os.path.isfile(self.file_one))
        self.assertFalse(os.path.isfile(vault_file_one.path))
        self.assertTrue(os.path.isfile(self.file_two))
        self.assertTrue(os.path.isfile(vault_file_two.path))
        self.assertTrue(os.path.isfile(self.file_three))
        self.assertTrue(os.path.isfile(vault_file_three.path))

    # Behavior: When the source file of a vault file in Archive is deleted, Sweeper does not delete the vault file if its a dry run
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
        Sweeper(dummy_walker, dummy_persistence, False)

        self.assertTrue(os.path.isfile(self.file_one))
        self.assertTrue(os.path.isfile(vault_file_one.path))
        self.assertFalse(os.path.isfile(self.file_two))
        self.assertTrue(os.path.isfile(vault_file_two.path))

        self.assertTrue(os.path.isfile(self.file_three))
        self.assertTrue(os.path.isfile(vault_file_three.path))

    # Behavior: When the source file of a vault file in Archive is deleted, Sweeper deletes the vault file
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

        Sweeper(dummy_walker, dummy_persistence, True)

        self.assertFalse(os.path.isfile(self.file_one))
        self.assertFalse(os.path.isfile(vault_file_one.path))
        self.assertFalse(os.path.isfile(self.file_two))
        self.assertFalse(os.path.isfile(vault_file_two.path))

        self.assertTrue(os.path.isfile(self.file_three))
        self.assertTrue(os.path.isfile(vault_file_three.path))

    # Behavior:
    # The vault file is in Stash, but has less than one hardlink: corruption is logged.
    # The vault file is in Staged, but has more than one hardlink: there is no corruption.
    # The vault file is in Limbo, but has more than one hardlink: corruption is logged.
    @mock.patch('bin.sandman.walk.idm', new=dummy_idm)
    @mock.patch('bin.vault._create_vault')
    def test_archive_corruption_case_actual(self, vault_mock):
        vault_file_one = self.vault.add(Branch.Staged, self.file_one)
        vault_file_two = self.vault.add(Branch.Limbo, self.file_two)
        walk = [(self.vault, File.FromFS(vault_file_one.path), VaultExc.PhysicalVaultFile("File is in Staged and can have to hardlinks if the file was archived with the stash option")),
                (self.vault, File.FromFS(vault_file_two.path), VaultExc.PhysicalVaultFile("File is in Limbo and has two hardlinks"))]
        dummy_walker = _DummyWalker(walk)
        dummy_persistence = MagicMock()
        Sweeper(dummy_walker, dummy_persistence, True)

        self.assertTrue(os.path.isfile(self.file_one))
        self.assertTrue(os.path.isfile(vault_file_one.path))
        self.assertTrue(os.path.isfile(self.file_two))
        self.assertTrue(os.path.isfile(vault_file_two.path))

   # Behavior: Regular, tracked, non-vault file.
   # If the file is marked for Keep: nothing is done.
   # If the file has a corresponding hardlink in Staged, its NOT a case of VaultCorruption
   # If the file has a corresponding hardlink in Limbo, its a case of VaultCorruption and yet nothing is done.
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
        Sweeper(dummy_walker, dummy_persistence, True)

        self.assertTrue(os.path.isfile(self.file_one))
        self.assertTrue(os.path.isfile(vault_file_one.path))
        self.assertTrue(os.path.isfile(self.file_two))
        self.assertTrue(os.path.isfile(vault_file_two.path))
        self.assertTrue(os.path.isfile(self.file_three))
        self.assertTrue(os.path.isfile(vault_file_three.path))

    # Behavior: Regular, tracked, non-vault file.
    # If the file has a corresponding hardlink in Archive, then the source file is deleted and the archive file is moved to staged.
    @mock.patch('bin.sandman.walk.idm', new=dummy_idm)
    @mock.patch('bin.vault._create_vault')
    def test_tracked_file_archived(self, vault_mock):
        vault_file_one_archive = self.vault.add(Branch.Archive, self.file_one)

        walk = [(self.vault, File.FromFS(self.file_one), Branch.Archive)]

        vault_file_one_staged = self.determine_vault_path(
            self.file_one, Branch.Staged)

        dummy_walker = _DummyWalker(walk)
        dummy_persistence = MagicMock()
        Sweeper(dummy_walker, dummy_persistence, True)

        self.assertFalse(os.path.isfile(self.file_one))
        self.assertFalse(os.path.isfile(vault_file_one_archive.path))
        self.assertTrue(os.path.isfile(vault_file_one_staged))

    # Behavior: Regular, tracked, non-vault file.
    # If the file has a corresponding hardlink in Stash, then the source file is NOT deleted and the stashed file is moved to staged.
    @mock.patch('bin.sandman.walk.idm', new=dummy_idm)
    @mock.patch('bin.vault._create_vault')
    def test_tracked_file_stashed(self, vault_mock):
        vault_file_one_stash = self.vault.add(Branch.Stash, self.file_one)

        walk = [(self.vault, File.FromFS(self.file_one), Branch.Stash)]

        vault_file_one_staged = self.determine_vault_path(
            self.file_one, Branch.Staged)

        dummy_walker = _DummyWalker(walk)
        dummy_persistence = MagicMock()
        Sweeper(dummy_walker, dummy_persistence, True)

        self.assertTrue(os.path.isfile(self.file_one))
        self.assertFalse(os.path.isfile(vault_file_one_stash.path))
        self.assertTrue(os.path.isfile(vault_file_one_staged))

    # Behavior: When a regular, untracked, non-vault file has been there for more than the deletion threshold, the source is deleted and a hardlink created in Limbo
    @mock.patch('bin.sandman.walk.idm', new=dummy_idm)
    @mock.patch('bin.vault._create_vault')
    def test_deletion_threshold_passed(self, vault_mock):
        walk = [(self.vault, make_file_seem_old(self.file_one), None)]
        dummy_walker = _DummyWalker(walk)
        dummy_persistence = MagicMock()

        vault_file_path = self.determine_vault_path(
            self.file_one, Branch.Limbo)

        Sweeper(dummy_walker, dummy_persistence, True)

        # Check if the untracked file has been deleted
        self.assertFalse(os.path.isfile(self.file_one))
        # Check if the file has been added to Limbo
        self.assertTrue(os.path.isfile(vault_file_path))

    # Behavior: When a regular, untracked, non-vault file has been modified more than the deletion threshold ago, but read recently, the source is not deleted and a hardlink is not created in Limbo
    @mock.patch('bin.sandman.walk.idm', new=dummy_idm)
    @mock.patch('bin.vault._create_vault')
    def test_deletion_threshold_not_passed_for_access(self, vault_mock):
        walk = [
            (self.vault, make_file_seem_old_but_read_recently(self.file_one), None)]
        dummy_walker = _DummyWalker(walk)
        dummy_persistence = MagicMock()

        vault_file_path = self.determine_vault_path(
            self.file_one, Branch.Limbo)

        Sweeper(dummy_walker, dummy_persistence, True)

        # Check if the untracked file has been deleted
        self.assertTrue(os.path.isfile(self.file_one))
        # Check if the file has been added to Limbo
        self.assertFalse(os.path.isfile(vault_file_path))

    # Behavior: When a regular, untracked, non-vault file has been modified more than the deletion threshold ago, but created recently, the source is not deleted and a hardlink is not created in Limbo
    @mock.patch('bin.sandman.walk.idm', new=dummy_idm)
    @mock.patch('bin.vault._create_vault')
    def test_deletion_threshold_not_passed_for_creation(self, vault_mock):
        walk = [(self.vault, make_file_seem_modified_long_ago(self.file_one), None)]
        dummy_walker = _DummyWalker(walk)
        dummy_persistence = MagicMock()

        vault_file_path = self.determine_vault_path(
            self.file_one, Branch.Limbo)

        Sweeper(dummy_walker, dummy_persistence, True)

        # Check if the untracked file has been deleted
        self.assertTrue(os.path.isfile(self.file_one))
        # Check if the file has been added to Limbo
        self.assertFalse(os.path.isfile(vault_file_path))

    # Behavior: When a Limbo file has been there for more than the limbo threshold, it is deleted
    @mock.patch('bin.sandman.walk.idm', new=dummy_idm)
    @mock.patch('bin.vault._create_vault')
    def test_limbo_deletion_threshold_passed(self, vault_mock):
        vault_file_one = self.vault.add(Branch.Limbo, self.file_one)
        self.file_one.unlink()

        walk = [(self.vault, make_file_seem_old(vault_file_one.path),
                 VaultExc.PhysicalVaultFile("File is in Limbo"))]
        dummy_walker = _DummyWalker(walk)
        dummy_persistence = MagicMock()
        Sweeper(dummy_walker, dummy_persistence, True)

        self.assertFalse(os.path.isfile(self.file_one))
        self.assertFalse(os.path.isfile(vault_file_one.path))

    # Behavior: When a Limbo file was modifed more than the limbo threshold ago, but read recently, it is not deleted
    @mock.patch('bin.sandman.walk.idm', new=dummy_idm)
    @mock.patch('bin.vault._create_vault')
    def test_limbo_deletion_threshold_not_passed_for_access(self, vault_mock):
        vault_file_one = self.vault.add(Branch.Limbo, self.file_one)
        self.file_one.unlink()

        walk = [(self.vault, make_file_seem_old_but_read_recently(
            vault_file_one.path), VaultExc.PhysicalVaultFile("File is in Limbo"))]
        dummy_walker = _DummyWalker(walk)
        dummy_persistence = MagicMock()
        Sweeper(dummy_walker, dummy_persistence, True)

        self.assertFalse(os.path.isfile(self.file_one))
        self.assertTrue(os.path.isfile(vault_file_one.path))

    # Behavior: When a Limbo file has been there for less than the limbo threshold, it is not deleted
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
        Sweeper(dummy_walker, dummy_persistence, True)

        self.assertFalse(os.path.isfile(self.file_one))
        self.assertTrue(os.path.isfile(vault_file_one.path))

    def test_unactionable_file_wont_be_actioned(self):
        """Gets the Sweeper to try and action a file
        with the wrong permissions. The file won't be actionable,
        and it should throw the exception.

        Anything in the file `can_add` criteria will throw this
        exception.

        """
        dummy_walker = _DummyWalker(
            [(self.vault, File.FromFS(self.wrong_perms), None)])
        dummy_persistence = MagicMock()
        self.assertRaises(core.file.exception.UnactionableFile,
                          lambda: Sweeper(dummy_walker, dummy_persistence, True))

    def test_emails_stakeholders(self):
        """We're going to get a file close to the threshold,
        and then check if the email that is generated mentions
        the right information
        """
        new_time: T.DateTime = time.now() - config.deletion.threshold + \
            max(config.deletion.warnings) - time.delta(seconds=1)
        dummy_walker = _DummyWalker([(self.vault, _DummyFile.FromFS(
            self.file_one, idm, ctime=new_time, mtime=new_time, atime=new_time), None)])
        dummy_persistence = _DummyPersistence(config.persistence, idm)
        MockMailer.file_path = T.Path(self._tmp.name).resolve() / "mail"
        Sweeper(dummy_walker, dummy_persistence, True,
                MockMailer)  # this will make the email

        # Now we'll see what it says
        # Nothing in all the thresholds except the largest
        # Nothing staged for archival
        def _search_file(file: T.Path, phrase: str) -> T.List[int]:
            """returns first line number that the phrase was
            found in the file"""
            locations: T.List[int] = []
            with open(file) as f:
                for line_num, line in enumerate(f):
                    if phrase in line:
                        locations.append(line_num)
            return locations

        # The filepath should only be listed once in the whole email
        filepath_line_nums = _search_file(
            MockMailer.file_path, str(self.file_one))
        self.assertEquals(len(filepath_line_nums), 1)

        # That should be at the bottom of all the warnings
        for _line_num in _search_file(MockMailer.file_path, "Your files will be DELETED"):
            self.assertLess(_line_num, filepath_line_nums[0])
