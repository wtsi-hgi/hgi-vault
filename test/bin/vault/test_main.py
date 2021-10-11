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
from bin.vault import main, ViewContext
from api.vault import Branch
from core import typing as T
import argparse


class TestMain(unittest.TestCase):

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.view')
    def test_keep_view_relative_default(self, mock_view, mock_remove):
        main(["__init__","keep" ,"--view"])
        mock_view.assert_called_with(Branch.Keep, ViewContext.All, False)
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.view')
    def test_keep_view_absolute_default(self, mock_view, mock_remove):
        main(["__init__","keep" ,"--view", "--absolute"])
        mock_view.assert_called_with(Branch.Keep, ViewContext.All, True)
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.view')
    def test_keep_view_relative_all(self, mock_view, mock_remove):
        main(["__init__","keep" ,"--view", "all"])
        mock_view.assert_called_with(Branch.Keep, ViewContext.All, False)
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.view')
    def test_keep_view_absolute_all(self, mock_view, mock_remove):
        main(["__init__","keep" ,"--view", "all", "--absolute"])
        mock_view.assert_called_with(Branch.Keep, ViewContext.All, True)
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.view')
    def test_keep_view_relative_here(self, mock_view, mock_remove):
        main(["__init__","keep" ,"--view", "here"])
        mock_view.assert_called_with(Branch.Keep, ViewContext.Here, False)
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.view')
    def test_keep_view_absolute_here(self, mock_view, mock_remove):
        main(["__init__","keep" ,"--view", "here", "--absolute"])
        mock_view.assert_called_with(Branch.Keep, ViewContext.Here, True)
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.view')
    def test_keep_view_relative_mine(self, mock_view, mock_remove):
        main(["__init__","keep" ,"--view", "mine"])
        mock_view.assert_called_with(Branch.Keep, ViewContext.Mine, False)
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.view')
    def test_keep_view_absolute_mine(self, mock_view, mock_remove):
        main(["__init__","keep" ,"--view", "mine", "--absolute"])
        mock_view.assert_called_with(Branch.Keep, ViewContext.Mine, True)
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
        mock_view.assert_called_with(Branch.Archive, ViewContext.All, False)
        mock_view.assert_called_with(Branch.Stash, ViewContext.All, False)
        mock_remove.assert_not_called()


    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.view')
    def test_archive_view_absolute_default(self, mock_view, mock_remove):
        main(["__init__","archive" ,"--view", "--absolute"])
        mock_view.assert_called_with(Branch.Archive, ViewContext.All, True)
        mock_view.assert_called_with(Branch.Stash, ViewContext.All, True)
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.view')
    def test_archive_view_relative_all(self, mock_view, mock_remove):
        main(["__init__","archive" ,"--view", "all"])
        mock_view.assert_called_with(Branch.Archive, ViewContext.All, False)
        mock_view.assert_called_with(Branch.Stash, ViewContext.All, False)
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.view')
    def test_archive_view_absolute_all(self, mock_view, mock_remove):
        main(["__init__","archive" ,"--view", "all", "--absolute"])
        mock_view.assert_called_with(Branch.Archive, ViewContext.All, True)
        mock_view.assert_called_with(Branch.Stash, ViewContext.All, True)
        mock_remove.assert_not_called()


    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.view')
    def test_archive_view_relative_here(self, mock_view, mock_remove):
        main(["__init__","archive" ,"--view", "here"])
        mock_view.assert_called_with(Branch.Archive, ViewContext.Here, False)
        mock_view.assert_called_with(Branch.Stash, ViewContext.Here, False)
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.view')
    def test_archive_view_absolute_here(self, mock_view, mock_remove):
        main(["__init__","archive" ,"--view", "here", "--absolute"])
        mock_view.assert_called_with(Branch.Archive, ViewContext.Here, True)
        mock_view.assert_called_with(Branch.Stash, ViewContext.Here, True)
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.view')
    def test_archive_view_relative_mine(self, mock_view, mock_remove):
        main(["__init__","archive" ,"--view", "mine"])
        mock_view.assert_called_with(Branch.Archive, ViewContext.Mine, False)
        mock_view.assert_called_with(Branch.Stash, ViewContext.Mine, False)
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.view')
    def test_archive_view_absolute_mine(self, mock_view, mock_remove):
        main(["__init__","archive" ,"--view", "mine", "--absolute"])
        mock_view.assert_called_with(Branch.Archive, ViewContext.Mine, True)
        mock_view.assert_called_with(Branch.Stash, ViewContext.Mine, True)
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.view')
    def test_archive_view_staged_relative_default(self, mock_view, mock_remove):
        main(["__init__","archive" ,"--view-staged"])
        mock_view.assert_called_with(Branch.Staged, ViewContext.All, False)
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.view')
    def test_archive_view_staged_absolute_default(self, mock_view, mock_remove):
        main(["__init__","archive" ,"--view-staged", "--absolute"])
        mock_view.assert_called_with(Branch.Staged, ViewContext.All, True)
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.view')
    def test_archive_view_staged_relative_all(self, mock_view, mock_remove):
        main(["__init__","archive" ,"--view-staged", "all"])
        mock_view.assert_called_with(Branch.Staged, ViewContext.All, False)
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.view')
    def test_archive_view_staged_absolute_all(self, mock_view, mock_remove):
        main(["__init__","archive" ,"--view-staged", "all", "--absolute"])
        mock_view.assert_called_with(Branch.Staged, ViewContext.All, True)
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.view')
    def test_archive_view_staged_relative_here(self, mock_view, mock_remove):
        main(["__init__","archive" ,"--view-staged", "here"])
        mock_view.assert_called_with(Branch.Staged, ViewContext.Here, False)
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.view')
    def test_archive_view_staged_absolute_here(self, mock_view, mock_remove):
        main(["__init__","archive" ,"--view-staged", "here", "--absolute"])
        mock_view.assert_called_with(Branch.Staged, ViewContext.Here, True)
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.view')
    def test_archive_view_staged_relative_mine(self, mock_view, mock_remove):
        main(["__init__","archive" ,"--view-staged", "mine"])
        mock_view.assert_called_with(Branch.Staged, ViewContext.Mine, False)
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.view')
    def test_archive_view_staged_absolute_mine(self, mock_view, mock_remove):
        main(["__init__","archive" ,"--view-staged", "mine", "--absolute"])
        mock_view.assert_called_with(Branch.Staged, ViewContext.Mine, True)
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.add')
    def test_archive_files(self, mock_add, mock_remove):
        main(["__init__","archive" ,"/file1", "/file2"])
        mock_add.assert_called_with(Branch.Archive, [T.Path("/file1"), T.Path("/file2")])
        mock_remove.assert_not_called()


    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.add')
    def test_stash_files(self, mock_add, mock_remove):
        main(["__init__","archive" ,"--stash", "/file1", "/file2"])
        mock_add.assert_called_with(Branch.Stash, [T.Path("/file1"), T.Path("/file2")])
        mock_remove.assert_not_called()



    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.recover')
    def test_recover_files(self, mock_recover, mock_remove):
        main(["__init__","recover" ,"/file1", "/file2"])
        mock_recover.assert_called_with([T.Path("/file1"), T.Path("/file2")])
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.recover')
    def test_recover_all(self, mock_recover, mock_untrack):
        main(["__init__","recover" ,"--all"])
        mock_recover.assert_called_with(None)
        mock_untrack.assert_not_called()

    @mock.patch('bin.vault.untrack')
    def test_untrack(self, mock_untrack):
        main(["__init__","untrack" ,"/file1", "/file2"])
        mock_untrack.assert_called_with([T.Path("/file1"), T.Path("/file2")])
