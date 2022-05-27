"""
Copyright (c) 2020 Genome Research Limited

Author: Christopher Harrison <ch12@sanger.ac.uk>

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
from tempfile import TemporaryDirectory

from core import typing as T
from core.vault import base, exception

_DUMMY_VAULT = T.Path("dummy")


class DummyBranch(base.Branch):
    Foo = T.Path("foo")
    Bar = T.Path("bar")


class DummyVaultFile(base.VaultFile):
    def __init__(self, vault, branch, path):
        self.vault = vault
        self.branch = branch
        self._path = path

    @property
    def path(self):
        return self.vault.location / self.branch.value / self._path

    @property
    def source(self):
        return False

    @property
    def can_add(self):
        pass

    @property
    def can_remove(self):
        pass


class DummyVault(base.Vault):
    _file_type = DummyVaultFile
    _branch_enum = DummyBranch
    _vault = _DUMMY_VAULT

    def add(self, branch, path):
        pass

    def remove(self, branch, path):
        pass

    def list(self, branch):
        pass


class TestBaseVault(unittest.TestCase):
    def test_valid_root(self):
        vault = DummyVault()

        with self.assertRaises(exception.InvalidRoot):
            vault.root = T.Path("foo")

        with self.assertRaises(exception.InvalidRoot):
            vault.root = T.Path("/foo")

        vault.root = T.Path("/")
        self.assertEqual(vault.root, T.Path("/"))

        with self.assertRaises(exception.RootIsImmutable):
            vault.root = T.Path("/tmp")

    def test_containment(self):
        vault = DummyVault()

        with TemporaryDirectory() as root:
            # Set up vault like so: /path/to/tmp/${_DUMMY_VAULT}/
            #                       + foo/
            #                       | + foo
            #                       + bar/
            #                         + bar
            root = T.Path(root)
            for branch in DummyBranch:
                bpath = branch.value

                path = root / _DUMMY_VAULT / bpath
                path.mkdir(parents=True)

                filename = path / bpath
                filename.touch()

            vault.root = root
            for branch in DummyBranch:
                bpath = branch.value
                self.assertEqual(vault.branch(bpath), branch)
                self.assertTrue(bpath in vault)

            not_in_vault = T.Path("path/to/nowhere")
            self.assertIsNone(vault.branch(not_in_vault))
            self.assertFalse(not_in_vault in vault)


if __name__ == "__main__":
    unittest.main()
