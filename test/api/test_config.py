"""
Copyright (c) 2020 Genome Research Limited

Authors:
* Aiden Neale <an12@sanger.ac.uk>
* Christopher Harrison <ch12@sanger.ac.uk>
* Piyush Ahuja <pa11@sanger.ac.uk>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or (at
your option) any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see https://www.gnu.org/licenses/
"""

import unittest
from tempfile import NamedTemporaryFile

from core import config, time, typing as T
from api.config import Config


_EXAMPLE_CONFIG = T.Path("eg/.vaultrc")
_EXAMPLE_CONFIG_TEXT = _EXAMPLE_CONFIG.read_text()

_NOT_A_CONFIG = "This is an example"

_BAD_YAML = """
identity:
    ldap:
            host: baz
        port: quux
"""

# Extra stuff should be ignored
_ADDED_INFO_CONFIG = f"""{_EXAMPLE_CONFIG_TEXT}
here:
  is: some extra stuff
"""

# A list where a scalar is expected
_SCALAR_LIST_CONFIG = _EXAMPLE_CONFIG_TEXT.replace(
    "port: 5432",
    "port: [1, 2, 3]")

# Incorrect data type
_INCORRECT_TYPE_CONFIG = _EXAMPLE_CONFIG_TEXT.replace(
    "port: 389",
    "port: Three hundred and eighty nine")

# A required key not present
_MISSING_KEY_CONFIG = _EXAMPLE_CONFIG_TEXT.replace(
    "host: ldap.example.com",
    "")

# An optional key not present
_MISSING_OPTIONAL_CONFIG = _EXAMPLE_CONFIG_TEXT.replace(
    "port: 25",
    "")

_MISSING_DELETION_LIMBO = _EXAMPLE_CONFIG_TEXT.replace(
    "limbo: 14",
    "")

class TestConfig(unittest.TestCase):
    _tmp:NamedTemporaryFile
    temp_config:T.Path

    def setUp(self) -> None:
        self._tmp = NamedTemporaryFile()
        self.temp_config = T.Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.close()
        del self.temp_config

    def test_example_config(self) -> None:
        # NOTE This is coupled to eg/.vaultrc
        # Any changes there must be reflected in these tests
        config = Config(_EXAMPLE_CONFIG)

        self.assertEqual(config.identity.ldap.host, "ldap.example.com")
        self.assertEqual(config.identity.ldap.port, 389)

        self.assertEqual(config.identity.users.dn, "ou=users,dc=example,dc=com")
        self.assertEqual(config.identity.users.attributes.uid, "uidNumber")
        self.assertEqual(config.identity.users.attributes.name, "cn")
        self.assertEqual(config.identity.users.attributes.email, "mail")

        self.assertEqual(config.identity.groups.dn, "ou=groups,dc=example,dc=com")
        self.assertEqual(config.identity.groups.attributes.gid, "gidNumber")
        self.assertEqual(config.identity.groups.attributes.owners, "owner")
        self.assertEqual(config.identity.groups.attributes.members, "member")

        self.assertEqual(config.persistence.postgres.host, "postgres.example.com")
        self.assertEqual(config.persistence.postgres.port, 5432)

        self.assertEqual(config.persistence.database, "sandman")
        self.assertEqual(config.persistence.user, "a_db_user")
        self.assertEqual(config.persistence.password, "abc123")

        self.assertEqual(config.email.smtp.host, "mail.example.com")
        self.assertEqual(config.email.smtp.port, 25)
        self.assertEqual(config.email.sender, "vault@example.com")

        self.assertEqual(config.deletion.threshold, time.delta(days=90))
        self.assertEqual(config.deletion.warnings, [time.delta(days=10), time.delta(days=3), time.delta(days=1)])
        self.assertEqual(config.deletion.limbo, time.delta(days=14))

        self.assertEqual(config.archive.threshold, 1000)
        self.assertEqual(config.archive.handler, T.Path("/path/to/executable"))

    def test_builder(self) -> None:
        self.assertIsInstance(Config(_EXAMPLE_CONFIG), Config)

        self.temp_config.write_text(_NOT_A_CONFIG)
        self.assertRaises(config.exception.InvalidConfiguration, Config._build, self.temp_config)

        self.temp_config.write_text(_BAD_YAML)
        self.assertRaises(config.exception.InvalidConfiguration, Config._build, self.temp_config)

    def test_validator(self) -> None:
        self.assertTrue(Config(_EXAMPLE_CONFIG)._is_valid)

        self.temp_config.write_text(_ADDED_INFO_CONFIG)
        self.assertTrue(Config(self.temp_config)._is_valid)

        self.temp_config.write_text(_SCALAR_LIST_CONFIG)
        self.assertRaises(config.exception.InvalidSemantics, Config, self.temp_config)

        self.temp_config.write_text(_INCORRECT_TYPE_CONFIG)
        self.assertRaises(config.exception.InvalidSemantics, Config, self.temp_config)

        self.temp_config.write_text(_MISSING_KEY_CONFIG)
        self.assertRaises(config.exception.InvalidSemantics, Config, self.temp_config)

        self.temp_config.write_text(_MISSING_OPTIONAL_CONFIG)
        self.assertTrue((c := Config(self.temp_config))._is_valid)
        self.assertEqual(c.email.smtp.port, 25)

        self.temp_config.write_text(_MISSING_DELETION_LIMBO)


    

  

if __name__ == "__main__":
    unittest.main()
