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
import unittest
from unittest import mock
import os
os.environ["VAULTRC"] = "eg/.vaultrc"
from bin.vault import main
from api.vault import Branch
from core import typing as T
import argparse


class TestMain(unittest.TestCase):

    @mock.patch('bin.vault.remove')
    @mock.patch('bin.vault.view')
    def test_keep_view(self, mock_view, mock_remove):
        main(["__init__","keep" ,"--view"])
        mock_view.assert_called_with(Branch.Keep)
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.remove')
    @mock.patch('bin.vault.add')
    def test_keep_files(self, mock_add, mock_remove):
        main(["__init__","keep" ,"/file1", "/file2"])
        mock_add.assert_called_with(Branch.Keep, [T.Path("/file1"), T.Path("/file2")])
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.remove')
    @mock.patch('bin.vault.view')
    def test_archive_view(self, mock_view, mock_remove):
        main(["__init__","archive" ,"--view"])
        mock_view.assert_called_with(Branch.Archive)
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.remove')
    @mock.patch('bin.vault.add')
    def test_archive_files(self, mock_add, mock_remove):
        main(["__init__","archive" ,"/file1", "/file2"])
        mock_add.assert_called_with(Branch.Archive, [T.Path("/file1"), T.Path("/file2")])
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.remove')
    @mock.patch('bin.vault.recover')
    def test_recover_files(self, mock_recover, mock_remove):
        main(["__init__","recover" ,"/file1", "/file2"])
        mock_recover.assert_called_with([T.Path("/file1"), T.Path("/file2")])
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.remove')
    @mock.patch('bin.vault.recover')
    def test_recover_all(self, mock_recover, mock_remove):
        main(["__init__","recover" ,"--all"])
        mock_recover.assert_called_with(None)
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.remove')
    def test_remove(self, mock_remove):
        main(["__init__","remove" ,"/file1", "/file2"])
        mock_remove.assert_called_with([T.Path("/file1"), T.Path("/file2")])
    
