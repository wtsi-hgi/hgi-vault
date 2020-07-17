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

from core import config, idm, typing as T
from .ldap import LDAP, NoResultsFound


class LDAPUser(idm.base.User):
    _name:str
    _email:str

    def __init__(self, entry:T.Dict, mapping:config.base.Config) -> None:
        self._id, *_    = entry[mapping.uid]
        self._name, *_  = entry[mapping.name]
        self._email, *_ = entry[mapping.email]

    @property
    def name(self) -> str:
        return self._name

    @property
    def email(self) -> str:
        return self._email


class LDAPGroup(idm.base.Group):
    pass


class LDAPIdentityManager(idm.base.IdentityManager):
    _config:config.base.Config
    _ldap:LDAP

    # Cache of users and groups
    _users:T.Dict[int, LDAPUser]
    _groups:T.Dict[int, LDAPGroup]

    def __init__(self, config:config.base.Config) -> None:
        self._config = config
        self._ldap = LDAP(config.ldap)
        self._users = self._groups = {}

    def user(self, *, uid:int) -> LDAPUser:
        if uid in self._users:
            return self._users[uid]

        try:
            config = self._config.users
            self._users[uid] = LDAPUser(
                next(self._ldap.search(config.dn, f"({config.attributes.uid}={uid})")),
                config.attributes)

        except NoResultsFound:
            raise idm.exception.NoSuchIdentity(f"User with POSIX ID {uid} was not found")

        return self.user(uid=uid)

    def group(self, *, gid:int) -> LDAPGroup:
        raise NotImplementedError("Watch this space...")
