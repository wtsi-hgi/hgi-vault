"""
Copyright (c) 2022 Genome Research Limited

Author: Sendu Bala <sb10@sanger.ac.uk>

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
import os
from api.idm.idm import LDAPIdentityManager
from api.config import ExecutableNamespace
from bin.common import generate_config
from unittest import mock

Executable = ExecutableNamespace.Executable


class TestGenerateConfig(unittest.TestCase):

    def test_vault_config(self) -> None:
        config, idm = generate_config(Executable.VAULT)
        self.assertEqual(config.identity.ldap.host, "ldap.example.com")
        self.assertIsInstance(idm, LDAPIdentityManager)

    def test_sandman_config(self) -> None:
        config, idm = generate_config(Executable.SANDMAN)
        self.assertEqual(config.identity.ldap.host, "ldap.example.com")
        self.assertEqual(config.persistence.database, "sandman")

    def test_invalidexe_config(self) -> None:
        self.assertRaises(ExecutableNamespace.InvalidExecutable,
                          generate_config, "foo")

    @mock.patch.dict(os.environ, {"BADVAULTRC": "eg/.nonexistant"})
    def test_invalidpath_config(self) -> None:
        self.assertRaises(SystemExit, generate_config, Executable.VAULT, False)

    @mock.patch.dict(os.environ, {"BADVAULTRC": "eg/.nonexistant"})
    def test_cached_config(self) -> None:
        # the cached config from earlier tests means we don't see effect of the
        # BADVAULTRC
        config, idm = generate_config(Executable.VAULT, True)
        self.assertEqual(config.identity.ldap.host, "ldap.example.com")


if __name__ == "__main__":
    unittest.main()
