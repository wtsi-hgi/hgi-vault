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
import unittest
from unittest import mock
import os
os.environ["VAULTRC"] = "eg/.vaultrc"
from bin.vault import main
from api.vault import Branch
from core import typing as T
import argparse


class TestMain(unittest.TestCase):

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.view')
    def test_keep_view_relative_default(self, mock_view, mock_remove):
        main(["__init__","keep" ,"--view"])
        mock_view.assert_called_with(Branch.Keep, "all", False)
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.view')
    def test_keep_view_absolute_default(self, mock_view, mock_remove):
        main(["__init__","keep" ,"--view", "--absolute"])
        mock_view.assert_called_with(Branch.Keep, "all", True)
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.view')
    def test_keep_view_relative_all(self, mock_view, mock_remove):
        main(["__init__","keep" ,"--view", "all"])
        mock_view.assert_called_with(Branch.Keep, "all", False)
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.view')
    def test_keep_view_absolute_all(self, mock_view, mock_remove):
        main(["__init__","keep" ,"--view", "all", "--absolute"])
        mock_view.assert_called_with(Branch.Keep, "all", True)
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.view')
    def test_keep_view_relative_here(self, mock_view, mock_remove):
        main(["__init__","keep" ,"--view", "here"])
        mock_view.assert_called_with(Branch.Keep, "here", False)
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.view')
    def test_keep_view_absolute_here(self, mock_view, mock_remove):
        main(["__init__","keep" ,"--view", "here", "--absolute"])
        mock_view.assert_called_with(Branch.Keep, "here", True)
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.view')
    def test_keep_view_relative_mine(self, mock_view, mock_remove):
        main(["__init__","keep" ,"--view", "mine"])
        mock_view.assert_called_with(Branch.Keep, "mine", False)
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.view')
    def test_keep_view_absolute_mine(self, mock_view, mock_remove):
        main(["__init__","keep" ,"--view", "mine", "--absolute"])
        mock_view.assert_called_with(Branch.Keep, "mine", True)
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.add')
    def test_keep_files(self, mock_add, mock_remove):
        main(["__init__","keep" ,"/file1", "/file2"])
        mock_add.assert_called_with(Branch.Keep, [T.Path("/file1"), T.Path("/file2")])
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.view')
    def test_archive_view_relative_default(self, mock_view, mock_remove):
        main(["__init__","archive" ,"--view"])
        mock_view.assert_called_with(Branch.Archive, "all", False)
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.view')
    def test_archive_view_absolute_default(self, mock_view, mock_remove):
        main(["__init__","archive" ,"--view", "--absolute"])
        mock_view.assert_called_with(Branch.Archive, "all", True)
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.view')
    def test_archive_view_relative_all(self, mock_view, mock_remove):
        main(["__init__","archive" ,"--view", "all"])
        mock_view.assert_called_with(Branch.Archive, "all", False)
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.view')
    def test_archive_view_absolute_all(self, mock_view, mock_remove):
        main(["__init__","archive" ,"--view", "all", "--absolute"])
        mock_view.assert_called_with(Branch.Archive, "all", True)
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.view')
    def test_archive_view_relative_here(self, mock_view, mock_remove):
        main(["__init__","archive" ,"--view", "here"])
        mock_view.assert_called_with(Branch.Archive, "here", False)
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.view')
    def test_archive_view_absolute_here(self, mock_view, mock_remove):
        main(["__init__","archive" ,"--view", "here", "--absolute"])
        mock_view.assert_called_with(Branch.Archive, "here", True)
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.view')
    def test_archive_view_relative_mine(self, mock_view, mock_remove):
        main(["__init__","archive" ,"--view", "mine"])
        mock_view.assert_called_with(Branch.Archive, "mine", False)
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.view')
    def test_archive_view_absolute_mine(self, mock_view, mock_remove):
        main(["__init__","archive" ,"--view", "mine", "--absolute"])
        mock_view.assert_called_with(Branch.Archive, "mine", True)
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.add')
    def test_archive_files(self, mock_add, mock_remove):
        main(["__init__","archive" ,"/file1", "/file2"])
        mock_add.assert_called_with(Branch.Archive, [T.Path("/file1"), T.Path("/file2")])
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.recover')
    def test_recover_files(self, mock_recover, mock_remove):
        main(["__init__","recover" ,"/file1", "/file2"])
        mock_recover.assert_called_with([T.Path("/file1"), T.Path("/file2")])
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.recover')
    def test_recover_all(self, mock_recover, mock_remove):
        main(["__init__","recover" ,"--all"])
        mock_recover.assert_called_with(None)
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.untrack')
    def test_remove(self, mock_remove):
        main(["__init__","untrack" ,"/file1", "/file2"])
        mock_remove.assert_called_with([T.Path("/file1"), T.Path("/file2")])
