"""
Copyright (c) 2022 Genome Research Limited

Author: Michael Grace <mg38@sanger.ac.uk>

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

from core import typing as T
from core.config import base as ConfigBase
from core.idm import base as IDMBase
from core.persistence import base as PersistenceBase


class DummyUser(IDMBase.User):
    def __init__(
            self,
            uid: int,
            name: T.Optional[str] = None,
            email: T.Optional[str] = None) -> None:
        self._id: int = uid
        self._name = name or f"Dummy User Name - uid: {self._id}"
        self._email = email or f"Dummy User Email - uid: {self._id}"

    @property
    def name(self) -> str:
        return self._name

    @property
    def email(self) -> T.Optional[str]:
        return self._email


class DummyGroup(IDMBase.Group):
    def __init__(self,
                 gid: int,
                 num_grp_owners: int = 3,
                 owner: IDMBase.User = DummyUser(1),
                 member: T.Optional[IDMBase.User] = None) -> None:
        self._id: int = gid
        self._owner = owner
        self._member: IDMBase.User = member or owner
        self._num_owners: int = num_grp_owners

    @property
    def name(self) -> str:
        return f"Dummy Group Name - gid: {self._id}"

    @property
    def members(self) -> T.Iterator[IDMBase.User]:
        yield self._member

    @property
    def owners(self) -> T.Iterator[IDMBase.User]:
        for _ in range(self._num_owners):
            yield self._owner


class DummyIDM(IDMBase.IdentityManager):
    def __init__(self,
                 _: ConfigBase.Config,
                 num_grp_owners: int = 3,
                 grp_owner: IDMBase.User = DummyUser(1),
                 grp_member: T.Optional[IDMBase.User] = None) -> None:
        self._num_grp_owners: int = num_grp_owners
        self._grp_owner = grp_owner
        self._grp_member = grp_member

    def user(self, *, uid: int) -> DummyUser:
        return DummyUser(uid)

    def group(self, *, gid: int) -> DummyGroup:
        return DummyGroup(
            gid,
            num_grp_owners=self._num_grp_owners,
            owner=self._grp_owner,
            member=self._grp_member)



class DummyState(PersistenceBase.State):
    pass


class DummyFile(PersistenceBase.File):
    pass
