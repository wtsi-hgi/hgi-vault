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

import grp
import pwd
from abc import ABCMeta, abstractmethod
from contextlib import suppress
from dataclasses import dataclass
from string import Template

from core import config, idm, typing as T
from .ldap import LDAP, NoResultsFound


@dataclass(init=False)
class _LDAPIdentity:
    _idm:LDAPIdentityManager
    _exc:T.ClassVar[Template]

class _LazyLDAPIdentity(_LDAPIdentity, metaclass=ABCMeta):
    """ Abstract base class for lazy LDAP identity loading """
    def __init__(self, idm:LDAPIdentityManager, identity:int) -> None:
        self._idm = idm

        try:
            self._id = self._check_id(identity)
        except KeyError:
            raise idm.exception.NoSuchIdentity(self._exc.substitute(identity=identity))

    @classmethod
    @abstractmethod
    def from_dn(cls, idm:LDAPIdentityManager, dn:str) -> _LazyLDAPIdentity:
        """ Construct the identity object from a DN """

    @staticmethod
    @abstractmethod
    def _check_id(identity:int) -> int:
        """
        Check that the given identity exists: Acting as the identity
        function, if an identity exists, or raising KeyError otherwise
        """

    @abstractmethod
    def _fetch_details(self) -> None:
        """ Fetch details from LDAP when required """
        # TODO There's scope for further abstraction here


class LDAPUser(_LazyLDAPIdentity, idm.base.User):
    _exc = Template("User with POSIX ID $identity was not found")

    _name:T.Optional[str]  = None
    _email:T.Optional[str] = None

    @classmethod
    def from_dn(cls, idm:LDAPIdentityManager, dn:str) -> LDAPUser:
        # NOTE Here we make the assumption that user DNs have the form:
        #
        #   KEY=USERNAME,BASE_DN
        #
        # Where KEY is arbitrary, USERNAME is the POSIX username and
        # BASE_DN is per the configuration definition. We extract the
        # USERNAME and run it through the passwd database to convert it
        # to its respective POSIX user ID.
        base_suffix = f",{idm._config.users.dn}"
        if not dn.endswith(base_suffix):
            # This is not a known user DN
            raise idm.exception.NoSuchIdentity(f"The DN {dn} is not a subordinate of {idm._config.users.dn}")

        try:
            # Strip the base DN suffix, then split the key-value pair
            _, username = dn[:-len(base_suffix)].split("=")
            uid = pwd.getpwnam(username).pw_uid
        except KeyError:
            # This is an unknown username
            raise idm.exception.NoSuchIdentity(f"User with POSIX username {username} was not found")

        return idm.user(uid=uid)

    @staticmethod
    def _check_id(identity:int) -> int:
        return pwd.getpwuid(identity).pw_uid

    def _fetch_details(self) -> None:
        config  = self._idm._config.users
        mapping = config.attributes

        try:
            user = next(self._idm._ldap.search(config.dn, f"({mapping.uid}={self.uid})"))
            self._name, *_  = user[mapping.name]
            self._email, *_ = user[mapping.email]

        except NoResultsFound:
            raise idm.exception.NoSuchIdentity(self._exc.substitute(identity=self.uid))

    @property
    def name(self) -> str:
        if self._name is None:
            self._fetch_details()

        return self._name

    @property
    def email(self) -> str:
        if self._email is None:
            self._fetch_details()

        return self._email


class LDAPGroup(_LazyLDAPIdentity, idm.base.Group):
    _exc = Template("Group with POSIX ID $identity was not found")

    _owners:T.Optional[T.List[LDAPUser]]  = None
    _members:T.Optional[T.List[LDAPUser]] = None

    @classmethod
    def from_dn(cls, idm:LDAPIdentityManager, dn:str) -> LDAPGroup:
        # This is not (currently) needed
        raise NotImplementedError

    @staticmethod
    def _check_id(identity:int) -> int:
        return grp.getgrgid(identity).gr_gid

    def _fetch_details(self) -> None:
        config  = self._idm._config.groups
        mapping = config.attributes

        def user_from_dn(dn:str) -> T.Optional[LDAPUser]:
            with suppress(idm.exception.NoSuchIdentity):
                return LDAPUser.from_dn(self._idm, dn)

        try:
            # Dereference owners and members, skipping over any that
            # can't be found in the passwd database
            group = next(self._idm._ldap.search(config.dn, f"({mapping.gid}={self.gid})"))
            self._owners  = [user for dn in group[mapping.owners]  if (user := user_from_dn(dn)) is not None]
            self._members = [user for dn in group[mapping.members] if (user := user_from_dn(dn)) is not None]

        except NoResultsFound:
            raise idm.exception.NoSuchIdentity(self._exc.substitute(identity=self.gid))

    @property
    def owners(self) -> T.Iterator[LDAPUser]:
        if self._owners is None:
            self._fetch_details()

        yield from self._owners

    @property
    def members(self) -> T.Iterator[LDAPUser]:
        if self._members is None:
            self._fetch_details()

        yield from self._members


class LDAPIdentityManager(idm.base.IdentityManager):
    _config:config.base.Config
    _ldap:LDAP

    # Cache of users and groups
    _cache:T.Dict[T.Tuple[T.Type[_LazyLDAPIdentity], int], _LazyLDAPIdentity]

    def __init__(self, config:config.base.Config) -> None:
        self._config = config
        self._ldap   = LDAP(config.ldap)
        self._cache  = {}

    @T.overload
    def _fetch(self, cls:T.Type[LDAPUser], entity_id:int) -> LDAPUser: ...

    @T.overload
    def _fetch(self, cls:T.Type[LDAPGroup], entity_id:int) -> LDAPGroup: ...

    def _fetch(self, cls, entity_id):
        key = cls, entity_id
        cache = self._cache

        if key not in cache:
            # Add to cache, when it doesn't exist
            cache[key] = cls(self, entity_id)

        return cache[key]

    def user(self, *, uid:int) -> LDAPUser:
        return self._fetch(LDAPUser, uid)

    def group(self, *, gid:int) -> LDAPGroup:
        return self._fetch(LDAPGroup, gid)
