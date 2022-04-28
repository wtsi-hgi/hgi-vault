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
import argparse
from core import typing as T
from api.vault import Branch
from bin.vault import main, ViewContext
import unittest
from unittest import mock
from unittest.mock import call, mock_open

from tempfile import TemporaryDirectory
import os
os.environ["VAULTRC"] = "eg/.vaultrc"


class TestMain(unittest.TestCase):

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.view')
    def test_keep_view_relative_default(self, mock_view, mock_remove):
        main(["__init__", "keep", "--view"])
        mock_view.assert_called_with(Branch.Keep, ViewContext.All, False)
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.view')
    def test_keep_view_absolute_default(self, mock_view, mock_remove):
        main(["__init__", "keep", "--view", "--absolute"])
        mock_view.assert_called_with(Branch.Keep, ViewContext.All, True)
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.view')
    def test_keep_view_relative_all(self, mock_view, mock_remove):
        main(["__init__", "keep", "--view", "all"])
        mock_view.assert_called_with(Branch.Keep, ViewContext.All, False)
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.view')
    def test_keep_view_absolute_all(self, mock_view, mock_remove):
        main(["__init__", "keep", "--view", "all", "--absolute"])
        mock_view.assert_called_with(Branch.Keep, ViewContext.All, True)
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.view')
    def test_keep_view_relative_here(self, mock_view, mock_remove):
        main(["__init__", "keep", "--view", "here"])
        mock_view.assert_called_with(Branch.Keep, ViewContext.Here, False)
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.view')
    def test_keep_view_absolute_here(self, mock_view, mock_remove):
        main(["__init__", "keep", "--view", "here", "--absolute"])
        mock_view.assert_called_with(Branch.Keep, ViewContext.Here, True)
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.view')
    def test_keep_view_relative_mine(self, mock_view, mock_remove):
        main(["__init__", "keep", "--view", "mine"])
        mock_view.assert_called_with(Branch.Keep, ViewContext.Mine, False)
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.view')
    def test_keep_view_absolute_mine(self, mock_view, mock_remove):
        main(["__init__", "keep", "--view", "mine", "--absolute"])
        mock_view.assert_called_with(Branch.Keep, ViewContext.Mine, True)
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.add')
    def test_keep_files(self, mock_add, mock_remove):
        main(["__init__", "keep", "/file1", "/file2"])
        mock_add.assert_called_with(
            Branch.Keep, [T.Path("/file1"), T.Path("/file2")])
        mock_remove.assert_not_called()

    # Test for log warning message about symlink
    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.add')
    def test_keep_files_symlink(self, mock_add, mock_remove):

        self._tmp = TemporaryDirectory()
        path = T.Path(self._tmp.name).resolve()
        # Form a directory hierarchy
        filepath = path / "a"
        symlink = path / "b"
        filepath.touch()
        os.symlink(filepath, symlink)

        main(["__init__", "keep", str(symlink)])
        mock_add.assert_called_with(Branch.Keep, [filepath])
        mock_remove.assert_not_called()
        self._tmp.cleanup()

    # Test for log warning message about symlink in fofn case
    @mock.patch('bin.vault.untrack')
    def test_symlink_fofn(self, mock_untrack):
        self._tmp = TemporaryDirectory()
        path = T.Path(self._tmp.name).resolve()
        # Form temporary files
        filepath = path / "a"
        symlink = path / "b"
        filepath.touch()
        os.symlink(filepath, symlink)
        with mock.patch("builtins.open", new_callable=mock_open, read_data=f"{symlink}\n"):
            main(["__init__", "untrack", "--fofn", "mock_file"])
            args = mock_untrack.call_args.args
            files = list(args[0])
            self.assertEqual(files, [filepath])
        self._tmp.cleanup()

    @mock.patch("builtins.open", new_callable=mock_open, read_data='/file1\n/file2')
    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.add')
    def test_keep_fofn(self, mock_add, mock_remove, mock_file):
        main(["__init__", "keep", "--fofn", "mock_file"])
        args = mock_add.call_args.args
        files = list(args[1])
        branch = args[0]
        self.assertEqual(files, [T.Path("/file1"), T.Path("/file2")])
        self.assertEqual(branch, Branch.Keep)
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.view')
    def test_archive_view_relative_default(self, mock_view, mock_remove):
        main(["__init__", "archive", "--view"])
        calls = [call(Branch.Archive, ViewContext.All, False),
                 call(Branch.Stash, ViewContext.All, False)]
        mock_view.assert_has_calls(calls)
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.view')
    def test_archive_view_absolute_default(self, mock_view, mock_remove):
        main(["__init__", "archive", "--view", "--absolute"])
        calls = [call(Branch.Archive, ViewContext.All, True),
                 call(Branch.Stash, ViewContext.All, True)]
        mock_view.assert_has_calls(calls)
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.view')
    def test_archive_view_relative_all(self, mock_view, mock_remove):
        main(["__init__", "archive", "--view", "all"])
        calls = [call(Branch.Archive, ViewContext.All, False),
                 call(Branch.Stash, ViewContext.All, False)]
        mock_view.assert_has_calls(calls)
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.view')
    def test_archive_view_absolute_all(self, mock_view, mock_remove):
        main(["__init__", "archive", "--view", "all", "--absolute"])
        calls = [call(Branch.Archive, ViewContext.All, True),
                 call(Branch.Stash, ViewContext.All, True)]
        mock_view.assert_has_calls(calls)
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.view')
    def test_archive_view_relative_here(self, mock_view, mock_remove):
        main(["__init__", "archive", "--view", "here"])
        calls = [call(Branch.Archive, ViewContext.Here, False),
                 call(Branch.Stash, ViewContext.Here, False)]
        mock_view.assert_has_calls(calls)
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.view')
    def test_archive_view_absolute_here(self, mock_view, mock_remove):
        main(["__init__", "archive", "--view", "here", "--absolute"])
        calls = [call(Branch.Archive, ViewContext.Here, True),
                 call(Branch.Stash, ViewContext.Here, True)]
        mock_view.assert_has_calls(calls)
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.view')
    def test_archive_view_relative_mine(self, mock_view, mock_remove):
        main(["__init__", "archive", "--view", "mine"])
        calls = [call(Branch.Archive, ViewContext.Mine, False),
                 call(Branch.Stash, ViewContext.Mine, False)]
        mock_view.assert_has_calls(calls)
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.view')
    def test_archive_view_absolute_mine(self, mock_view, mock_remove):
        main(["__init__", "archive", "--view", "mine", "--absolute"])
        calls = [call(Branch.Archive, ViewContext.Mine, True),
                 call(Branch.Stash, ViewContext.Mine, True)]
        mock_view.assert_has_calls(calls)
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.view')
    def test_archive_view_staged_relative_default(self, mock_view, mock_remove):
        main(["__init__", "archive", "--view-staged"])
        mock_view.assert_called_with(Branch.Staged, ViewContext.All, False)
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.view')
    def test_archive_view_staged_absolute_default(self, mock_view, mock_remove):
        main(["__init__", "archive", "--view-staged", "--absolute"])
        mock_view.assert_called_with(Branch.Staged, ViewContext.All, True)
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.view')
    def test_archive_view_staged_relative_all(self, mock_view, mock_remove):
        main(["__init__", "archive", "--view-staged", "all"])
        mock_view.assert_called_with(Branch.Staged, ViewContext.All, False)
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.view')
    def test_archive_view_staged_absolute_all(self, mock_view, mock_remove):
        main(["__init__", "archive", "--view-staged", "all", "--absolute"])
        mock_view.assert_called_with(Branch.Staged, ViewContext.All, True)
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.view')
    def test_archive_view_staged_relative_here(self, mock_view, mock_remove):
        main(["__init__", "archive", "--view-staged", "here"])
        mock_view.assert_called_with(Branch.Staged, ViewContext.Here, False)
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.view')
    def test_archive_view_staged_absolute_here(self, mock_view, mock_remove):
        main(["__init__", "archive", "--view-staged", "here", "--absolute"])
        mock_view.assert_called_with(Branch.Staged, ViewContext.Here, True)
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.view')
    def test_archive_view_staged_relative_mine(self, mock_view, mock_remove):
        main(["__init__", "archive", "--view-staged", "mine"])
        mock_view.assert_called_with(Branch.Staged, ViewContext.Mine, False)
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.view')
    def test_archive_view_staged_absolute_mine(self, mock_view, mock_remove):
        main(["__init__", "archive", "--view-staged", "mine", "--absolute"])
        mock_view.assert_called_with(Branch.Staged, ViewContext.Mine, True)
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.add')
    def test_archive_files(self, mock_add, mock_remove):
        main(["__init__", "archive", "/file1", "/file2"])
        mock_add.assert_called_with(
            Branch.Archive, [T.Path("/file1"), T.Path("/file2")])
        mock_remove.assert_not_called()

    @mock.patch("builtins.open", new_callable=mock_open, read_data='/file1\n/file2')
    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.add')
    def test_archive_fofn(self, mock_add, mock_remove, mock_file):
        main(["__init__", "archive", "--fofn", "mock_file"])
        args = mock_add.call_args.args
        files = list(args[1])
        branch = args[0]
        self.assertEqual(files, [T.Path("/file1"), T.Path("/file2")])
        self.assertEqual(branch, Branch.Archive)
        mock_remove.assert_not_called()

    @mock.patch("builtins.open", new_callable=mock_open, read_data='/file1\n/file2')
    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.add')
    def test_archive_stash_fofn(self, mock_add, mock_remove, mock_file):
        main(["__init__", "archive", "--stash", "--fofn", "mock_file"])
        args = mock_add.call_args.args
        files = list(args[1])
        branch = args[0]
        self.assertEqual(files, [T.Path("/file1"), T.Path("/file2")])
        self.assertEqual(branch, Branch.Stash)
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.add')
    def test_stash_files(self, mock_add, mock_remove):
        main(["__init__", "archive", "--stash", "/file1", "/file2"])
        mock_add.assert_called_with(
            Branch.Stash, [T.Path("/file1"), T.Path("/file2")])
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.recover')
    def test_recover_files(self, mock_recover, mock_remove):
        main(["__init__", "recover", "/file1", "/file2"])
        mock_recover.assert_called_with([T.Path("/file1"), T.Path("/file2")])
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.recover')
    def test_recover_all(self, mock_recover, mock_untrack):
        main(["__init__", "recover", "--all"])
        mock_recover.assert_called_with(None)
        mock_untrack.assert_not_called()

    @mock.patch("builtins.open", new_callable=mock_open, read_data='/file1\n/file2\n')
    @mock.patch('bin.vault.untrack')
    @mock.patch('bin.vault.recover')
    def test_recover_fofn(self, mock_recover, mock_remove, mock_file):
        main(["__init__", "recover", "--fofn", "mock_file"])
        args = mock_recover.call_args.args
        files = list(args[0])
        self.assertEqual(files, [T.Path("/file1"), T.Path("/file2")])
        mock_remove.assert_not_called()

    @mock.patch('bin.vault.untrack')
    def test_untrack(self, mock_untrack):
        main(["__init__", "untrack", "/file1", "/file2"])
        mock_untrack.assert_called_with([T.Path("/file1"), T.Path("/file2")])

    @mock.patch("builtins.open", new_callable=mock_open, read_data='/file1\n/file2\n')
    @mock.patch('bin.vault.untrack')
    def test_untrack_fofn(self, mock_untrack, mock_file):
        main(["__init__", "untrack", "--fofn", "mock_file"])
        args = mock_untrack.call_args.args
        files = list(args[0])
        self.assertEqual(files, [T.Path("/file1"), T.Path("/file2")])
