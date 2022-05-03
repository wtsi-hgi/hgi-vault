"""
Copyright (c) 2021 Genome Research Limited

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

from bin.common import idm
from bin.vault import ViewContext, recover, view
from bin.vault.recover import relativise, derelativise, move_with_path_safety_checks, exception
from api.vault.key import VaultFileKey as VFK
from api.vault import Branch, Vault
from tempfile import TemporaryDirectory
from core import typing as T
from unittest import mock
import unittest
import os


class TestVaultRelativeToWorkDirRelative(unittest.TestCase):
    """
    The following tests will emulate the following directory structure
    relative to the vault root
    +- some/
        +- path/
        |  +- file1
        |  +- file2
        +- file3
    """

    def test_child_to_work_dir(self):

        work_dir = T.Path("some/path")
        vault_relative_path = T.Path("some/path/file1")
        expected = T.Path("file1")
        work_dir_rel = relativise(vault_relative_path, work_dir)
        self.assertEqual(expected, work_dir_rel)

    def test_sibling_to_work_dir(self):

        work_dir = T.Path("this/is/my/path")
        vault_relative_path = T.Path("this/is/my/file3")
        expected = T.Path("../file3")
        work_dir_rel = relativise(vault_relative_path, work_dir)
        self.assertEqual(expected, work_dir_rel)


class TestWorkDirRelativeToVaultRelative(unittest.TestCase):

    def test_child_to_work_dir(self):

        work_dir = T.Path("some/path")
        work_dir_rel = T.Path("file1")
        vault_path = T.Path("/this/is/vault/root")
        vault_relative_path = derelativise(work_dir_rel, work_dir, vault_path)
        expected = T.Path("some/path/file1")
        self.assertEqual(expected, vault_relative_path)

    def test_sibling_to_work_dir(self):

        work_dir = T.Path("this/is/my/path")
        work_dir_rel = T.Path("../file3")
        vault_path = T.Path("/this/is/vault/root")
        vault_relative_path = derelativise(work_dir_rel, work_dir, vault_path)
        expected = T.Path("this/is/my/file3")
        self.assertEqual(expected, vault_relative_path)


class TestMovWithPathSafetyChecks(unittest.TestCase):
    _tmp: TemporaryDirectory
    _path: T.Path

    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self._path = path = T.Path(self._tmp.name)

        tmp_file = path / "foo"
        tmp_file.touch()

    def tearDown(self) -> None:
        self._tmp.cleanup()
        del self._path

    def test_basic_case(self):

        full_source_path = self._path / "foo"
        full_dest_path = self._path / "quux"
        move_with_path_safety_checks(full_source_path, full_dest_path)
        self.assertFalse(os.path.isfile(full_source_path))
        self.assertTrue(os.path.isfile(full_dest_path))

    def test_source_does_not_exist(self):
        full_source_path = self._path / "new"
        full_dest_path = self._path / "quux"
        self.assertRaises(exception.NoSourceFound,
                          move_with_path_safety_checks, full_source_path, full_dest_path)

    def test_destination_does_not_exist(self):
        full_source_path = self._path / "foo"
        full_dest_path = self._path / "new" / "quux"
        self.assertRaises(exception.NoParentForDestination,
                          move_with_path_safety_checks, full_source_path, full_dest_path)


class TestRecover(unittest.TestCase):

    _tmp: TemporaryDirectory
    _path: T.Path

    def setUp(self) -> None:
        """
        The following tests will emulate the following directory structure
            +- parent/
                +-.vault/
                +- file1
                +- some/
                |  +- file2
                |  +- file3

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
        self.file_one.chmod(0o660)
        self.file_two.chmod(0o660)
        self.file_three.chmod(0o660)
        self.parent.chmod(0o330)
        self.some.chmod(0o330)
        Vault._find_root = mock.MagicMock(return_value=self.parent)
        # Make the desired vault.
        self.vault = Vault(relative_to=self.file_one, idm=idm)

    def tearDown(self) -> None:
        self._tmp.cleanup()
        del self.parent

    # These mock objects patch calls to cwd and _create_vault in recover.
    # These calls return our desired directory.
    @mock.patch('bin.vault.file.cwd')
    @mock.patch('bin.vault._create_vault')
    def test_basic_case(self, vault_mock, cwd_mock):
        vault_file_one = self.vault.add(Branch.Limbo, self.file_one)
        vault_file_two = self.vault.add(Branch.Limbo, self.file_two)
        vault_file_three = self.vault.add(Branch.Limbo, self.file_three)

        vault_file_path_one = vault_file_one.path
        vault_file_path_two = vault_file_two.path
        vault_file_path_three = vault_file_three.path

        self.file_one.unlink()
        self.file_two.unlink()
        self.file_three.unlink()

        cwd_mock.return_value = self.some
        vault_mock.return_value = self.vault
        files = [T.Path("../file1"), T.Path("file2")]
        recover(files)

        self.assertTrue(os.path.isfile(self.file_one))
        self.assertFalse(os.path.isfile(vault_file_path_one))
        self.assertTrue(os.path.isfile(self.file_two))
        self.assertFalse(os.path.isfile(vault_file_path_two))
        self.assertTrue(os.path.isfile(vault_file_path_three))
        self.assertFalse(os.path.isfile(self.file_three))

    @mock.patch('bin.vault.file.cwd')
    @mock.patch('bin.vault._create_vault')
    def test_all_case(self, vault_mock, cwd_mock):
        vault_file_one = self.vault.add(Branch.Limbo, self.file_one)
        vault_file_two = self.vault.add(Branch.Limbo, self.file_two)
        vault_file_three = self.vault.add(Branch.Limbo, self.file_three)

        vault_file_path_one = vault_file_one.path
        vault_file_path_two = vault_file_two.path
        vault_file_path_three = vault_file_three.path

        self.file_one.unlink()
        self.file_two.unlink()
        self.file_three.unlink()

        cwd_mock.return_value = self.some
        vault_mock.return_value = self.vault

        recover()

        self.assertTrue(os.path.isfile(self.file_one))
        self.assertFalse(os.path.isfile(vault_file_path_one))
        self.assertTrue(os.path.isfile(self.file_two))
        self.assertFalse(os.path.isfile(vault_file_path_two))
        self.assertTrue(os.path.isfile(self.file_three))
        self.assertFalse(os.path.isfile(vault_file_path_three))


class TestView(unittest.TestCase):

    _tmp: TemporaryDirectory
    parent: T.Path

    def setUp(self) -> None:
        """
        The following tests will emulate the following directory structure
            +- parent/
                +-.vault/
                +- file1
                +- some/
                |  +- file2
                |  +- file3

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

        # Ensure permissions are right for the vault "add" api to work.
        # The default permissions do not fly.
        # For files, ensure they are readable, writable and u=g (66x).
        # Parent directories should be executable and should have u=g(33x)
        self.file_one.chmod(0o660)
        self.file_two.chmod(0o660)
        self.file_three.chmod(0o660)
        self.parent.chmod(0o330)
        self.some.chmod(0o330)

        Vault._find_root = mock.MagicMock(return_value=self.parent)
        self.vault = Vault(relative_to=self.file_one, idm=idm)

    def tearDown(self) -> None:
        self._tmp.cleanup()
        del self.parent

    @mock.patch('bin.vault.file.cwd')
    def test_basic_case(self, cwd_mock):
        """This does not test anything, except possibly for syntax errors
        , but is useful for the purpose of understanding"""
        self.vault.add(Branch.Limbo, self.file_one)
        self.vault.add(Branch.Limbo, self.file_two)
        self.vault.add(Branch.Limbo, self.file_three)

        cwd_mock.return_value = self.parent / "some"
        view(Branch.Limbo, ViewContext.All, False)
