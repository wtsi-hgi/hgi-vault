import unittest
import logging

import os
os.environ["VAULTRC"] = "eg/.vaultrc"

from tempfile import TemporaryDirectory

from core import typing as T
from api.vault.file import convert_vault_rel_to_work_dir_rel, convert_work_dir_rel_to_vault_rel, hardlink_and_remove

from bin.vault import recover 

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
# +- some/
#    +- path/
#    |  +- file2
#    |  +- file3

#    +- file1
    _tmp:TemporaryDirectory
    _path:T.Path

    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self._path = path = T.Path(self._tmp.name)

        self._limbo_root = limbo_root = path / ".vault"/".limbo"
        tmp_dir = limbo_root/ "some"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        tmp_file_one = limbo_root/  "file1"
        tmp_file_two = limbo_root/ tmp_dir / "file2"
        tmp_file_three = limbo_root/ tmp_dir / "file3"
        tmp_file_one.touch()
        tmp_file_two.touch()
        tmp_file_three.touch()

     

    def tearDown(self) -> None:
        self._tmp.cleanup()
        del self._path

    @mock.patch('bin.vault.os.getcwd')
    @mock.patch('bin.vault._create_vault')
    def test_basic_case(self, vault_mock, cwd_mock):


        cwd_mock.return_value = self._path / "some"
        custom_mock = vault_mock()
        custom_mock._find_root.return_value = self._path
        vault_mock.return_value = custom_mock
        

        files = ["../file1", "file2"]
        recover(files)

        vault_root  = self._path
        limbo_root = self._limbo_root

        source_one = limbo_root/ "file1"
        destination_one = vault_root/ "file1"
        self.assertTrue(os.path.isfile(destination_one))
        self.assertFalse(os.path.isfile(source_one))

        source_two = limbo_root/ "some"/ "file2"
        destination_two = vault_root/ "some"/ "file2"
        self.assertFalse(os.path.isfile(destination_two))
        self.assertTrue(os.path.isfile(source_two))

        source_three = limbo_root/ "some"/ "file3"
        destination_three = vault_root/ "some"/ "file3"
        self.assertTrue(os.path.isfile(source_three))
        self.assertFalse(os.path.isfile(destination_three))





