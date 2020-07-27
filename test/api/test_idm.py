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
from api.idm.idm import LDAPGroup, LDAPUser


# NOTE This ties our tests to the example configuration
_EXAMPLE_CONFIG = Config(T.Path("eg/.vaultrc")).identity


def _DUMMY_PWUID(uid):
    # Dummy passwd interface, that acts as an identity function
    return T.SimpleNamespace(pw_uid=uid)

def _DUMMY_GRGID(gid):
    # Dummy group interface, that acts as an identity function
    return T.SimpleNamespace(gr_gid=gid)

def _DUMMY_PWNAM(username):
    # Dummy passwd-by-username interface: Take the bottom 10-bits from
    # the hash of the username string as the user ID
    # NOTE This is obviously not guaranteed to avoid clashes
    dummy_uid = hash(username) & 1023
    return T.SimpleNamespace(pw_uid=dummy_uid)


class TestIDM(unittest.TestCase):
    def setUp(self):
        with patch("api.idm.idm.LDAP", autospec=True):
            # Instantiate an identity manager with a mocked LDAP class
            self.mocked_ldap_idm = IdentityManager(_EXAMPLE_CONFIG)

    def test_ldap_user(self):
        idm = self.mocked_ldap_idm

        idm._ldap.search.return_value = iter([{
            "cn":   ["Testy McTestface"],
            "mail": ["test@example.com"]
        }])

        with patch("pwd.getpwuid", new=_DUMMY_PWUID):
            user = idm.user(uid=123)

        self.assertEqual(user.name,  "Testy McTestface")
        self.assertEqual(user.email, "test@example.com")

    def test_ldap_group(self):
        idm = self.mocked_ldap_idm

        mock_search = {
            "owner":  [f"uid={user},{idm._config.users.dn}" for user in ["foo", "bar"]],
            "member": [f"uid={user},{idm._config.users.dn}" for user in ["bar", "quux", "xyzzy"]]
        }
        idm._ldap.search.return_value = iter([mock_search])

        with patch("grp.getgrgid", new=_DUMMY_GRGID):
            group = idm.group(gid=123)

        with patch.multiple("pwd", getpwnam=_DUMMY_PWNAM, getpwuid=_DUMMY_PWUID):
            for dn in mock_search["owner"]:
                self.assertIn(LDAPUser.from_dn(idm, dn), group.owners)

            for dn in mock_search["member"]:
                self.assertIn(LDAPUser.from_dn(idm, dn), group.members)


if __name__ == "__main__":
    unittest.main()
