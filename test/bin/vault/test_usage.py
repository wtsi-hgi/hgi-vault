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
from bin.vault.usage import parse_args
import unittest
import os


class TestUsage(unittest.TestCase):

    def test_keep(self):
        args = parse_args(["keep", "/file1", "/file2"])
        expected = [T.Path("/file1"), T.Path("/file2")]
        self.assertEqual(args.files, expected)

    def test_keep_view(self):
        args = parse_args(["keep", "--view"])
        self.assertTrue(args.view)

    def test_keep_file_view(self):
        args = parse_args(["keep", "/file1", "--view"])
        self.assertTrue(args.view)

        success = False
        try:
            args.files
        except AttributeError:
            success = True
        self.assertTrue(success)

    def test_keep_extra_files(self):
        args = ["keep", "/file1", "/file2", "/file3", "/file4",
                "/file5", "/file6", "/file7", "/file8", "/file9", "/file10", "/file11"]
        self.assertRaises(KeyError, parse_args, args)

    def test_archive(self):
        args = parse_args(["archive", "/file1", "/file2"])
        expected = [T.Path("/file1"), T.Path("/file2")]
        self.assertEqual(args.files, expected)

    def test_archive_view(self):
        args = parse_args(["archive", "--view"])
        self.assertTrue(args.view)

    def test_archive_file_view(self):
        args = parse_args(["archive", "/file1", "--view"])
        self.assertTrue(args.view)

        success = False
        try:
            args.files
        except AttributeError:
            success = True
        self.assertTrue(success)

    def test_archive_extra_files(self):
        args = ["archive", "/file1", "/file2", "/file3", "/file4",
                "/file5", "/file6", "/file7", "/file8", "/file9", "/file10", "/file11"]
        self.assertRaises(KeyError, parse_args, args)

    def test_recover(self):
        args = parse_args(["recover", "/file1", "/file2"])
        expected = [T.Path("/file1"), T.Path("/file2")]
        self.assertEqual(args.files, expected)

    def test_recover_view(self):
        args = parse_args(["recover", "--view"])
        self.assertTrue(args.view)

    def test_recover_all(self):
        args = parse_args(["recover", "--all"])
        self.assertTrue(args.all)

    def test_recover_view_all(self):
        args = ["recover", "--all", "--view"]
        self.assertRaises(KeyError, parse_args, args)

    def test_recover_view_all(self):
        args = ["recover", "--view", "--all"]
        self.assertRaises(KeyError, parse_args, args)

    def test_recover_file_view(self):
        args = parse_args(["recover", "/file1", "--view"])
        self.assertTrue(args.view)

        success = False
        try:
            args.files
        except AttributeError:
            success = True
        self.assertTrue(success)

    def test_recover_file_all(self):
        args = parse_args(["recover", "/file1", "--all"])
        self.assertTrue(args.all)

        success = False
        try:
            args.files
        except AttributeError:
            success = True
        self.assertTrue(success)

    def test_recover_all_file(self):
        args = parse_args(["recover", "--all", "/file1"])
        self.assertTrue(args.all)

        success = False
        try:
            args.files
        except AttributeError:
            success = True
        self.assertTrue(success)

    def test_recover_file_view(self):
        args = parse_args(["recover", "/file1", "--view"])
        self.assertTrue(args.view)

        success = False
        try:
            args.files
        except AttributeError:
            success = True
        self.assertTrue(success)

    def test_recover_view_file(self):
        success = False
        try:
            parse_args(["recover", "--view", "/file1"])
        except (argparse.ArgumentError, SystemExit):
            success = True
        self.assertTrue(success)

    def test_recover_extra_files(self):
        args = parse_args(["recover", "/file1", "/file2", "/file3", "/file4",
                           "/file5", "/file6", "/file7", "/file8", "/file9", "/file10", "/file11"])
        expected = [T.Path("/file1"), T.Path("/file2"), T.Path("/file3"),
                    T.Path(
                        "/file4"), T.Path("/file5"), T.Path("/file6"), T.Path("/file7"),
                    T.Path("/file8"), T.Path("/file9"), T.Path("/file10"), T.Path("/file11")]

        self.assertEqual(args.files, expected)

    def test_untrack(self):
        args = parse_args(["untrack", "/file1", "/file2"])
        expected = [T.Path("/file1"), T.Path("/file2")]
        self.assertEqual(args.files, expected)

    def test_untrack_view(self):
        args = ["untrack", "--view"]
        self.assertRaises(SystemExit, parse_args, args)

    def test_stash(self):
        args = parse_args(["archive", "--stash", "/file1", "/file2"])
        expected = [T.Path("/file1"), T.Path("/file2")]
        self.assertEqual(args.files, expected)

    def test_stash_exception_keep(self):

        args = ["keep", "--stash", "/file1", "/file2"]
        self.assertRaises(SystemExit, parse_args, args)

    def test_stash_exception_view(self):

        args = ["archive", "--stash", "--view"]
        self.assertRaises(SystemExit, parse_args, args)

        args = ["archive", "--view", "--stash"]
        self.assertRaises(SystemExit, parse_args, args)

        args = ["archive", "--stash"]
        self.assertRaises(KeyError, parse_args, args)

    def test_file_exception_fofn(self):

        args = ["archive", "--stash", "/file1", "/file2", "--fofn" "/file3"]
        self.assertRaises(SystemExit, parse_args, args)

        args = ["archive", "--fofn" "/file3", "/file1", "/file2"]
        self.assertRaises(SystemExit, parse_args, args)

        args = ["keep", "--fofn" "/file3", "/file1", "/file2"]
        self.assertRaises(SystemExit, parse_args, args)

        args = ["recover", "--fofn" "/file3", "/file1", "/file2"]
        self.assertRaises(SystemExit, parse_args, args)

        args = ["untrack", "--fofn" "/file3", "/file1", "/file2"]
        self.assertRaises(SystemExit, parse_args, args)
