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

import core.idm
from core import typing as T
from api.config import Config, Executable
from api.idm.idm import LDAPIdentityManager, LDAPUser, LDAPGroup
from api.idm.ldap import NoResultsFound


# NOTE This ties our tests to the example configuration
_EXAMPLE_CONFIG = Config(T.Path("eg/.vaultrc"),
                         executables=(Executable.VAULT,)).identity


def _DUMMY_PWUID(uid):
    # Dummy passwd interface, that acts as an identity function
    return T.SimpleNamespace(pw_uid=uid)


def _DUMMY_GRGID(gid):
    # Dummy group interface, that acts as an identity function
    return T.SimpleNamespace(gr_name="foo", gr_gid=gid)


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
            self.mocked_ldap_idm = LDAPIdentityManager(_EXAMPLE_CONFIG)

    def test_ldap_user(self):
        idm = self.mocked_ldap_idm

        idm._ldap.search.return_value = iter([{
            "cn": ["Testy McTestface"],
            "mail": ["test@example.com"]
        }])

        with patch("pwd.getpwuid", new=_DUMMY_PWUID):
            user = idm.user(uid=123)

        self.assertIsInstance(user, LDAPUser)
        self.assertEqual(user.uid, 123)

        # Check laziness; i.e., these attributes are placeholders...
        self.assertIsNone(user._name)
        self.assertIsNone(user._email)

        # ...until they're requested
        self.assertEqual(user.name, "Testy McTestface")
        self.assertEqual(user.email, "test@example.com")
        self.assertEqual(user.name, user._name)
        self.assertEqual(user.email, user._email)

    def test_ldap_group(self):
        idm = self.mocked_ldap_idm

        def user_dn(user): return f"uid={user},{idm._config.users.dn}"
        idm._ldap.search.return_value = iter([mock_results := {
            "owner": map(user_dn, ["foo", "bar"]),
            "member": map(user_dn, ["bar", "quux", "xyzzy"])
        }])

        with patch("grp.getgrgid", new=_DUMMY_GRGID):
            group = idm.group(gid=123)

        self.assertIsInstance(group, LDAPGroup)
        self.assertEqual(group.gid, 123)

        with patch.multiple("pwd", getpwnam=_DUMMY_PWNAM, getpwuid=_DUMMY_PWUID), \
                patch("grp.getgrgid", new=_DUMMY_GRGID):

            self.assertEqual(group.name, "foo")

            for dn in mock_results["owner"]:
                self.assertIn(LDAPUser.from_dn(idm, dn), group.owners)

            for dn in mock_results["member"]:
                self.assertIn(LDAPUser.from_dn(idm, dn), group.members)

    def test_bad_identity(self):
        idm = self.mocked_ldap_idm
        NoSuchIdentity = core.idm.exception.NoSuchIdentity

        with patch("pwd.getpwuid", side_effect=KeyError):
            self.assertRaises(NoSuchIdentity, idm.user, uid=123)
            self.assertRaises(NoSuchIdentity, LDAPUser.from_dn,
                              idm, f"uid=foo,{idm._config.users.dn}")

        self.assertRaises(NoSuchIdentity, LDAPUser.from_dn,
                          idm, "This is not the DN you are looking for")

        # Test LDAP search failure
        idm._ldap.search.side_effect = NoResultsFound

        with self.assertRaises(NoSuchIdentity):
            with patch("pwd.getpwuid", new=_DUMMY_PWUID):
                user = idm.user(uid=123)
                _ = user.email

        with self.assertRaises(NoSuchIdentity):
            with patch("grp.getgrgid", new=_DUMMY_GRGID):
                group = idm.group(gid=123)
                _ = next(group.members)


if __name__ == "__main__":
    unittest.main()
