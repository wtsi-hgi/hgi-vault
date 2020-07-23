"""
Copyright (c) 2020 Genome Research Limited

Authors:
* Christopher Harrison <ch12@sanger.ac.uk>
* Aiden Neale <an12@sanger.ac.uk>
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
from unittest.mock import patch

from core import typing as T
from api.config import Config
from api.idm import IdentityManager


# NOTE This ties our tests to the example configuration
_EXAMPLE_CONFIG = Config(T.Path("eg/.vaultrc")).identity


def _DUMMY_PASSWD(uid):
    # Dummy passwd interface, that acts as an identity function
    return T.SimpleNamespace(pw_uid=uid)

def _DUMMY_PASSWD1(gid):
    # Dummy passwd interface, that acts as an identity function
    return T.SimpleNamespace(gr_gid=gid)

class TestIDM(unittest.TestCase):
    def setUp(self):
        with patch("api.idm.idm.LDAP", autospec=True):
            # Instantiate an identity manager with a mocked LDAP class
            self.mocked_ldap_idm = IdentityManager(_EXAMPLE_CONFIG)

    def test_ldap_user(self):
        idm = self.mocked_ldap_idm

        # We can manipulate the LDAP search function's return value to
        # return what we want, for the purposes of testing
        idm._ldap.search.return_value = iter([{
            "cn":        ["Testy McTestface"],
            "mail":      ["test@example.com"]
        }])

        with patch("pwd.getpwuid", spec=_DUMMY_PASSWD):
            # We have to mock the passwd interface too
            user = idm.user(uid=123)

        self.assertEqual(user.name,  "Testy McTestface")
        self.assertEqual(user.email, "test@example.com")


    def test_ldap_group(self):
        idm = self.mocked_ldap_idm

        # We can manipulate the LDAP search function's return value to
        # return what we want, for the purposes of testing
        idm._ldap.search.return_value = iter([{
            "owners":        ["uid=ch12,ou=people,dc=sanger,dc=ac,dc=uk", "uid=an12,ou=people,dc=sanger,dc=ac,dc=uk"],
            "members":      ["an12"]
        }])

        with patch("grp.getgrgid", spec=_DUMMY_PASSWD1):
            # We have to mock the passwd interface too
            group = idm.group(gid=123)

        self.assertEqual(group.owners,  ["uid=ch12,ou=people,dc=sanger,dc=ac,dc=uk", "uid=an12,ou=people,dc=sanger,dc=ac,dc=uk"])
        self.assertEqual(group.members, "an12")


if __name__ == "__main__":
    unittest.main()
