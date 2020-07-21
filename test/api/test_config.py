"""
Copyright (c) 2020 Genome Research Limited

Author: Aiden Neale <an12@sanger.ac.uk>

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

import os
import unittest
from tempfile import TemporaryDirectory
from core import typing as T, time
from core.config import exception
from api.config import Config, _validate, _schema


class TestLoader(unittest.TestCase):
    _tmp:TemporaryDirectory
    _path:T.Path

    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self._path = path = T.Path(self._tmp.name)

        tmp_file = path / "config"
        tmp_file.touch()


    def tearDown(self) -> None:
        self._tmp.cleanup()
        del self._path



    def test_branch_contents(self) -> None:
        config = Config(T.Path("eg/.vaultrc"))
        self.assertEqual(config.identity.groups.attributes.owners, "owner")
        self.assertEqual(config.identity.users.dn, "ou=users,dc=example,dc=com")

        self.assertEqual(config.persistence.postgres.port, 5432)
        self.assertEqual(config.persistence.password, "abc123")

        self.assertEqual(config.email.smtp.host, "mail.example.com")
        self.assertEqual(config.deletion.warnings, [time.delta(days=10), time.delta(days=3), time.delta(days=1)])

        self.assertEqual(config.archive.handler, T.Path("/path/to/executable"))



    def test_build(self) -> None:
        _path = self._path / "config"

        self.assertTrue(Config(T.Path("eg/.vaultrc")))

        _not_a_config = """
This is an example
"""
        _bad_YAML = """
identity:
            ldap:
        host: baz
    port: quux
"""

        with open(_path, 'w') as file:
            file.write(_not_a_config)

        self.assertRaises(exception.InvalidConfiguration, Config._build, _path)

        with open(_path, 'w') as file:
            file.write(_bad_YAML)

        self.assertRaises(exception.InvalidConfiguration, Config._build, _path)



    def test_validation(self) -> None:
        _path = self._path / "config"
        #This test is expected to pass but fails
        config_test = Config(T.Path("eg/.vaultrc"))
        self.assertTrue(config_test._is_valid)

        _basic_schema = """
identity:
    ldap:
        host: ldap.example.com
    users:
        dn: ou=users,dc=example,dc=com
        attributes:
            uid: uidNumber
    groups:
        dn: ou=groups,dc=example,dc=com
        attributes:
            gid: gidNumber
persistence:
    postgres:
        host: postgres.example.com
    database: sandman
    user: a_db_user
    password: abc123
email:
    smtp:
        host: mail.example.com
    sender: vault@example.com
deletion:
    threshold: 90
archive:
    threshold: 1000
    handler: /path/to/executable
"""

        _added_info_schema = """
identity:
    ldap:
        host: ldap.example.com
    users:
        dn: ou=users,dc=example,dc=com
        attributes:
            uid: uidNumber
    groups:
        dn: ou=groups,dc=example,dc=com
        attributes:
            gid: gidNumber
persistence:
    postgres:
        host: postgres.example.com
    database: sandman
    data: information
    user: a_db_user
    password: abc123
email:
    smtp:
        host: mail.example.com
    sender: vault@example.com
deletion:
    threshold: 90
    warnings:
        - 240
        - 72
        - 24
archive:
    threshold: 1000
    data: more information
    handler: /path/to/executable
"""

        with open(_path, 'w') as file:
            file.write(_basic_schema)

        config_test = Config(T.Path(_path))
        self.assertTrue(config_test._is_valid)

        with open(_path, 'w') as file:
            file.write(_added_info_schema)

        self.assertTrue(Config(T.Path(_path))._is_valid)

if __name__ == "__main__":
    unittest.main()
