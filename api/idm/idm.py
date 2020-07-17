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

from __future__ import annotations

from core import config, idm, typing as T
from .ldap import LDAP, Scope, NoResultsFound


class LDAPUser(idm.base.User):
    _name:str
    _email:str

    def __init__(self, _:LDAPIdentityManager, entry:T.Dict, mapping:config.base.Config) -> None:
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
    _owners:T.List[LDAPUser]
    _members:T.List[LDAPUser]

    def __init__(self, idm:LDAPIdentityManager, entry:T.Dict, mapping:config.base.Config) -> None:
        self._id, *_  = entry[mapping.gid]

        # Dereference owners and members
        self._owners  = [user for u in entry[mapping.owners]  if (user := self._user(idm, u)) is not None]
        self._members = [user for u in entry[mapping.members] if (user := self._user(idm, u)) is not None]

    def _user(self, idm:LDAPIdentityManager, dn:str) -> T.Optional[LDAPUser]:
        """ Fetch the LDAP user by its DN """
        try:
            user = LDAPUser(
                idm,
                next(idm._ldap.search(dn, "(objectClass=*)", Scope.Base)),
                idm._config.users.attributes)

            idm._users[user.uid] = user  # Add to cache (FWIW)
            return user

        except NoResultsFound:
            return None

    @property
    def owners(self) -> T.Iterator[LDAPUser]:
        yield from self._owners

    @property
    def members(self) -> T.Iterator[LDAPUser]:
        yield from self._members


class LDAPIdentityManager(idm.base.IdentityManager):
    _config:config.base.Config
    _ldap:LDAP

    # Cache of users and groups
    _users:T.Dict[int, LDAPUser]
    _groups:T.Dict[int, LDAPGroup]

    def __init__(self, config:config.base.Config) -> None:
        self._config = config
        self._ldap   = LDAP(config.ldap)
        self._users  = {}
        self._groups = {}

    @T.overload
    def _fetch(self, cls:T.Type[LDAPUser], entity_id:int) -> LDAPUser: ...

    @T.overload
    def _fetch(self, cls:T.Type[LDAPGroup], entity_id:int) -> LDAPGroup: ...

    def _fetch(self, cls, entity_id):
        # Set up appropriate references for the given class
        cache, config, search_key, exception = {
            LDAPUser: (
                self._users,
                self._config.users,
                self._config.users.attributes.uid,
                f"User with POSIX ID {entity_id} was not found"),

            LDAPGroup: (
                self._groups,
                self._config.groups,
                self._config.groups.attributes.gid,
                f"Group with POSIX ID {entity_id} was not found")}[cls]

        if entity_id in cache:
            # Fetch from cache, if it exists
            return cache[entity_id]

        try:
            # Add entry to cache, if it exists
            cache[entity_id] = cls(
                self,
                next(self._ldap.search(config.dn, f"({search_key}={entity_id})")),
                config.attributes)

        except NoResultsFound:
            raise idm.exception.NoSuchIdentity(exception)

        return self._fetch(cls, entity_id)

    def user(self, *, uid:int) -> LDAPUser:
        return self._fetch(LDAPUser, uid)

    def group(self, *, gid:int) -> LDAPGroup:
        return self._fetch(LDAPGroup, gid)
