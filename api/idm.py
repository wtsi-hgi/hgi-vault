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

import os

import ldap3

from core import config, idm, typing as T


class LDAPUser(idm.base.User):
    _name:str
    _email:str

    def __init__(self, entry:ldap3.Entry, mapping:config.base.Config) -> None:
        self._id    = entry[mapping.uid].value
        self._name  = entry[mapping.name].value
        self._email = entry[mapping.email].value

    @property
    def name(self) -> str:
        return self._name

    @property
    def email(self) -> str:
        return self._email


class LDAPGroup(idm.base.Group):
    # Group where the current user is the only member and owner
    def __init__(self, gid:int) -> None:
        self._id = gid

    @property
    def members(self) -> T.Iterator[LDAPUser]:
        yield LDAPUser(os.getuid())

    owners = members


class LDAPIdentityManager(idm.base.IdentityManager):
    _config:config.base.Config

    _server:ldap3.Server
    _connection:ldap3.Connection

    # Cache of users and groups
    _users:T.Dict[int, LDAPUser]
    _groups:T.Dict[int, LDAPGroup]

    def __init__(self, config:config.base.Config) -> None:
        self._config = config

        # TODO Interface for LDAP, rather than hardcoding to ldap3
        self._server = ldap3.Server(host=config.ldap.host, port=config.ldap.port)
        self._connection = ldap3.Connection(self._server, authentication=ldap3.ANONYMOUS,
                                                          read_only=True,
                                                          lazy=True)
        self._users = self._groups = {}

    def _fetch(self, dn:str, query:str) -> T.Optional[ldap3.Entry]:
        with self._connection as ldap:
            if not ldap.search(search_base=dn, search_filter=query, search_scope=ldap3.SUBTREE, attributes=ldap3.ALL_ATTRIBUTES):
                return None

            return ldap.entries[0]

    def user(self, *, uid:int) -> LDAPUser:
        if uid in self._users:
            return self._users[uid]

        config = self._config.users
        if (user := self._fetch(config.dn, f"({config.attributes.uid}={uid})")) is None:
            raise idm.exception.NoSuchIdentity(f"User with POSIX ID {uid} was not found")

        self._users[uid] = LDAPUser(user, config.attributes)
        return self.user(uid=uid)

    def group(self, *, gid:int) -> LDAPGroup:
        raise NotImplementedError("Watch this space...")
