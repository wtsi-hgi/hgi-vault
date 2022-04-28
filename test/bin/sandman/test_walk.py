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

from bin.sandman.walk import FilesystemWalker
from core.vault import exception as VaultExc
from core import typing as T, idm as IdM
from api.vault import Branch, Vault
from unittest.mock import MagicMock
from unittest import mock
import unittest
from tempfile import TemporaryDirectory
import os
os.environ["VAULTRC"] = "eg/.vaultrc"


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
    _owner: _DummyUser
    _member: _DummyUser

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
    _user: _DummyUser

    def __init__(self, dummy_uid):
        self._user = _DummyUser(dummy_uid)

    def user(self, uid):
        pass

    def group(self, gid):
        return _DummyGroup(gid, self._user)


dummy_idm = _DummyIdM(1)


class TestFileSystemWalker(unittest.TestCase):

    def setUp(self):
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
        self.file_one.touch()
        self.file_two.touch()
        self.file_three.touch()
        # Ensure permissions are right for the vault add api to work.
        # The default permissions do not fly.
        # For files, ensure they are readable, writable and u=g (66x) is sufficient.
        # Parent directories should be executable and should have u=g(33x)
        # Parent directories should also be readable, for list_dir() to work in the walk
        self.file_one.chmod(0o660)
        self.file_two.chmod(0o660)
        self.file_three.chmod(0o660)
        self.parent.chmod(0o770)
        self.some.chmod(0o770)
        # Monkey patch Vault._find_root so that it returns the directory we want
        Vault._find_root = MagicMock(return_value=self.parent)
        self.vault = Vault(relative_to=self.file_one, idm=dummy_idm)

    def tearDown(self):
        self._tmp.cleanup()
        del self.parent

    # Behavior: A walk yields the correct status for the annotatd files, along with the files
    @mock.patch('bin.sandman.walk.idm', new=dummy_idm)
    def test_basic_case(self):
        # vault_mock =  MagicMock(return_value = self.parent)
        vault_file_one = self.vault.add(Branch.Keep, self.file_one)
        vault_file_two = self.vault.add(Branch.Archive, self.file_two)
        vault_file_three = self.vault.add(Branch.Limbo, self.file_three)
        self.file_three.unlink()

        walker = FilesystemWalker(self.parent)

        files = {}
        for vault, file, status in walker.files():
            key = file.path
            value = status
            files[key] = value

        self.assertTrue(isinstance(
            files[vault_file_one.path], VaultExc.PhysicalVaultFile))
        self.assertTrue(isinstance(
            files[vault_file_two.path], VaultExc.PhysicalVaultFile))
        self.assertTrue(isinstance(
            files[vault_file_three.path], VaultExc.PhysicalVaultFile))

        self.assertEqual(files[self.file_one], Branch.Keep)
        self.assertEqual(files[self.file_two], Branch.Archive)
        self.assertFalse(self.file_three in files)

    # Behavior: A walk yields the correct exceptions for corruped files
    @mock.patch('bin.sandman.walk.idm', new=dummy_idm)
    def test_corruption_case(self):
        # vault_mock =  MagicMock(return_value = self.parent)
        vault_file_one = self.vault.add(Branch.Keep, self.file_one)
        vault_file_two = self.vault.add(Branch.Archive, self.file_two)
        vault_file_three = self.vault.add(Branch.Limbo, self.file_three)
        self.file_one.unlink()
        self.file_two.unlink()

        walker = FilesystemWalker(self.parent)

        files = {}
        for vault, file, status in walker.files():
            key = file.path
            value = status
            files[key] = value

        self.assertTrue(isinstance(
            files[vault_file_one.path], VaultExc.PhysicalVaultFile))
        self.assertTrue(isinstance(
            files[vault_file_two.path], VaultExc.PhysicalVaultFile))
        self.assertTrue(isinstance(
            files[vault_file_three.path], VaultExc.PhysicalVaultFile))

        self.assertFalse(self.file_one in files)
        self.assertFalse(self.file_two in files)
        self.assertTrue(isinstance(
            files[self.file_three], VaultExc.VaultCorruption))

    # Behavior: A walk yields the correct exceptions for Staged files
    @mock.patch('bin.sandman.walk.idm', new=dummy_idm)
    def test_staged_case(self):
        # vault_mock =  MagicMock(return_value = self.parent)
        vault_file_one = self.vault.add(Branch.Staged, self.file_one)
        vault_file_two = self.vault.add(Branch.Staged, self.file_two)
        self.file_one.unlink()

        walker = FilesystemWalker(self.parent)

        files = {}
        for vault, file, status in walker.files():
            key = file.path
            value = status
            files[key] = value

        self.assertTrue(isinstance(
            files[vault_file_one.path], VaultExc.PhysicalVaultFile))
        self.assertTrue(isinstance(
            files[vault_file_two.path], VaultExc.PhysicalVaultFile))
        self.assertFalse(self.file_one in files)
        self.assertFalse(isinstance(
            files[self.file_two], VaultExc.VaultCorruption))
