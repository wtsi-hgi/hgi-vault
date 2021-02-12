"""
Copyright (c) 2020 Genome Research Limited

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


import unittest
import logging

import os
os.environ["VAULTRC"] = "eg/.vaultrc"

from core import typing as T
from tempfile import TemporaryDirectory
from api.vault import Branch, Vault
from api.vault.key import VaultFileKey as VFK
from bin.vault.limbo import convert_vault_rel_to_work_dir_rel, convert_work_dir_rel_to_vault_rel, hardlink_and_remove
from bin.vault import recover, view, recover_all
from bin.common import idm
from unittest import mock
# At the vault root
# +- some/
#    +- path/
#    |  +- file1
#    |  +- file2

#    +- file3

class TestVaultRelativeToWorkDirRelative(unittest.TestCase):

    def test_child_to_work_dir(self):
        #  some/path/file1, some/path ->  file1
        work_dir = T.Path("some/path")
        vault_relative_path = T.Path("some/path/file1")
        expected = T.Path("file1")
        work_dir_rel = convert_vault_rel_to_work_dir_rel(vault_relative_path, work_dir)
        self.assertEqual(expected, work_dir_rel)


    def test_sibling_to_work_dir(self):
        # this/is/my/file3, this/is/my/path  ->  ../file3,
        work_dir = T.Path("this/is/my/path")
        vault_relative_path = T.Path("this/is/my/file3")
        expected = T.Path("../file3")
        work_dir_rel = convert_vault_rel_to_work_dir_rel(vault_relative_path, work_dir)
        self.assertEqual(expected, work_dir_rel)


class TestWorkDirRelativeToVaultRelative(unittest.TestCase):

    def test_child_to_work_dir(self):
        #file1, some/path -> some/path/file1
        work_dir = T.Path("some/path")
        work_dir_rel = T.Path("file1")
        vault_path = T.Path(".")
        vault_relative_path = convert_work_dir_rel_to_vault_rel(work_dir_rel, work_dir, vault_path)
        expected = T.Path("some/path/file1")
        self.assertEqual(expected, vault_relative_path)


    def test_sibling_to_work_dir(self):
        #../file3, this/is/my/path -> this/is/my/file3
        work_dir = T.Path("this/is/my/path")
        work_dir_rel = T.Path("../file3")
        vault_path = T.Path(".")
        vault_relative_path = convert_work_dir_rel_to_vault_rel(work_dir_rel, work_dir, vault_path)
        expected = T.Path("this/is/my/file3")
        self.assertEqual(expected, vault_relative_path)




class TestHardLinkAndRemove(unittest.TestCase):
    _tmp:TemporaryDirectory
    _path:T.Path

    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self._path = path = T.Path(self._tmp.name)

        tmp_file = path / "foo"
        tmp_file.touch()

    
    def tearDown(self) -> None:
        self._tmp.cleanup()
        del self._path


    def test_basic_case(self):
        #file1, some/path -> some/path/file1
        full_source_path = self._path / "foo"
        full_dest_path = self._path / "quux"
        hardlink_and_remove(full_source_path, full_dest_path)
        self.assertFalse(os.path.isfile(full_source_path))
        self.assertTrue(os.path.isfile(full_dest_path))

    def test_source_does_not_exist(self):
        #file1, some/path -> some/path/file1
        full_source_path = self._path / "new"
        full_dest_path = self._path / "quux"
        hardlink_and_remove(full_source_path, full_dest_path)
        # self.assertRaises(hardlink_and_remove(full_source_path, full_dest_path))
    def test_destination_does_not_exist(self):
        #file1, some/path -> some/path/file1
        full_source_path = self._path / "foo"
        full_dest_path = self._path / "new" / "quux"
        hardlink_and_remove(full_source_path, full_dest_path)
        # self.assertRaises(hardlink_and_remove(full_source_path, full_dest_path))




class TestRecover(unittest.TestCase):

# At the vault root
# +- project/  
#   +- some/
#       +- path/
#       |  +- file2
#       |  +- file3

#   +- file1
    _tmp:TemporaryDirectory
    _path:T.Path

    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.parent = path = T.Path(self._tmp.name).resolve() / "parent"
        self.some = path / "some"
        self.some.mkdir(parents=True, exist_ok=True)
        self.file_one = path /  "file1"
        self.file_two = path / self.some / "file2"
        self.file_three = path / self.some / "file3"
        self.file_one.touch()
        self.file_two.touch()
        self.file_three.touch()

        self.file_one.chmod(0o660)
        self.file_two.chmod(0o664)
        self.file_three.chmod(0o660)
        self.parent.chmod(0o330)
        self.some.chmod(0o330)
        Vault._find_root = mock.MagicMock(return_value = self.parent)
        self.vault = Vault(relative_to = self.file_one, idm = idm)



    def tearDown(self) -> None:
        self._tmp.cleanup()
        del self.parent

    
    @mock.patch('bin.vault.file.cwd')
    @mock.patch('bin.vault._create_vault')
    def test_basic_case(self, vault_mock, cwd_mock):
        

        self.vault.add(Branch.Limbo, self.file_one)
        self.vault.add(Branch.Limbo, self.file_two)
        self.vault.add(Branch.Limbo, self.file_three)

        limbo_root = self.parent/ ".vault"/ ".limbo"

        inode_no = self.file_one.stat().st_ino
        vault_relative_path = self.file_one.relative_to(self.parent)
        vault_file_path_one = limbo_root / VFK(vault_relative_path, inode_no).path

        inode_no = self.file_two.stat().st_ino
        vault_relative_path = self.file_two.relative_to(self.parent)
        vault_file_path_two = limbo_root / VFK(vault_relative_path, inode_no).path

        inode_no = self.file_three.stat().st_ino
        vault_relative_path = self.file_three.relative_to(self.parent)
        vault_file_path_three = limbo_root / VFK(vault_relative_path, inode_no).path


        self.file_one.unlink()
        self.file_two.unlink()
        self.file_three.unlink()

        cwd_mock.return_value = self.some
        vault_mock.return_value = self.vault
        files = ["../file1", "file2"]
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
        

        self.vault.add(Branch.Limbo, self.file_one)
        self.vault.add(Branch.Limbo, self.file_two)
        self.vault.add(Branch.Limbo, self.file_three)

        limbo_root = self.parent/ ".vault"/ ".limbo"

        inode_no = self.file_one.stat().st_ino
        vault_relative_path = self.file_one.relative_to(self.parent)
        vault_file_path_one = limbo_root / VFK(vault_relative_path, inode_no).path

        inode_no = self.file_two.stat().st_ino
        vault_relative_path = self.file_two.relative_to(self.parent)
        vault_file_path_two = limbo_root / VFK(vault_relative_path, inode_no).path

        inode_no = self.file_three.stat().st_ino
        vault_relative_path = self.file_three.relative_to(self.parent)
        vault_file_path_three = limbo_root / VFK(vault_relative_path, inode_no).path


        self.file_one.unlink()
        self.file_two.unlink()
        self.file_three.unlink()

        cwd_mock.return_value = self.some
        vault_mock.return_value = self.vault
        
        recover_all()

        self.assertTrue(os.path.isfile(self.file_one))
        self.assertFalse(os.path.isfile(vault_file_path_one))


        self.assertTrue(os.path.isfile(self.file_two))
        self.assertFalse(os.path.isfile(vault_file_path_two))
        self.assertTrue(os.path.isfile(self.file_three))
        self.assertFalse(os.path.isfile(vault_file_path_three))
        
class TestView(unittest.TestCase):

# At the vault root
# +- some/
#    +- path/
#    |  +- file2
#    |  +- file3

#    +- file1
    _tmp:TemporaryDirectory
    parent:T.Path

    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.parent = path = T.Path(self._tmp.name).resolve() / "parent"
        self.some = path / "some"
        self.some.mkdir(parents=True, exist_ok=True)
        self.file_one = path /  "file1"
        self.file_two = path / self.some / "file2"
        self.file_three = path / self.some / "file3"
        self.file_one.touch()
        self.file_two.touch()
        self.file_three.touch()

        self.file_one.chmod(0o660)
        self.file_two.chmod(0o664)
        self.file_three.chmod(0o660)
        self.parent.chmod(0o330)
        self.some.chmod(0o330)
        Vault._find_root = mock.MagicMock(return_value = self.parent)
        self.vault = Vault(relative_to = self.file_one, idm = idm)


    def tearDown(self) -> None:
        self._tmp.cleanup()
        del self.parent

#     def test_basic_case(self, vault_mock, cwd_mock):
    @mock.patch('bin.vault.file.cwd')
    def test_basic_case(self, cwd_mock):

        self.vault.add(Branch.Limbo, self.file_one)
        self.vault.add(Branch.Limbo, self.file_two)
        self.vault.add(Branch.Limbo, self.file_three)

        cwd_mock.return_value = self.parent / "some"
        # custom_mock = vault_mock()
        # custom_mock._find_root.return_value = self._path
        # vault_mock.return_value = custom_mock
        view(Branch.Limbo)




