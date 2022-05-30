"""
Copyright (c) 2022 Genome Research Limited

Authors:
    - Sendu Bala <sb10@sanger.ac.uk>
    - Michael Grace <mg38@sanger.ac.uk>

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

import getpass
import os
import unittest
from unittest import mock

from api.config import ExecutableNamespace
from api.idm.idm import LDAPIdentityManager
from bin.common import clear_config_cache, generate_config

Executable = ExecutableNamespace.Executable


class TestGenerateConfig(unittest.TestCase):

    def setUp(self) -> None:
        clear_config_cache()

    def test_vault_config(self) -> None:
        config, idm = generate_config(Executable.VAULT)
        self.assertEqual(config.identity.ldap.host, "ldap.example.com")
        self.assertIsInstance(idm, LDAPIdentityManager)

    def test_sandman_config(self) -> None:
        config, _ = generate_config(Executable.SANDMAN)
        self.assertEqual(config.identity.ldap.host, "ldap.example.com")

        if os.getenv("SANDMAN_FARM_TEST") == "1":
            self.assertEqual(config.persistence.database, f"sandman_dev_{getpass.getuser()}")
        else:
            self.assertEqual(config.persistence.database, "sandman")

    def test_invalidexe_config(self) -> None:
        self.assertRaises(ExecutableNamespace.InvalidExecutable,
                          generate_config, "foo")

    @mock.patch.dict(os.environ, {"VAULTRC": "eg/.nonexistant"})
    def test_invalidpath_config(self) -> None:
        self.assertRaises(SystemExit, generate_config, Executable.VAULT)

    def test_cached_config(self) -> None:
        # First generate the config using the eg version
        generate_config(Executable.VAULT)

        # Then "regenerate" it with a non existant one
        with mock.patch.dict(os.environ, {"VAULTRC": "nonexistant"}):
            config, _ = generate_config(Executable.VAULT)

        # The cache should have held the original, so there'll still be values
        self.assertEqual(config.identity.ldap.host, "ldap.example.com")


if __name__ == "__main__":
    unittest.main()
