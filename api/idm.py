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

from core import config, idm, typing as T


class DummyUser(idm.base.User):
    def __init__(self, uid:int) -> None:
        self._id = uid

    @property
    def name(self) -> str:
        return "Dummy User"

    @property
    def email(self) -> T.Optional[str]:
        return "dummy@example.com"


class DummyGroup(idm.base.Group):
    # Group where the current user is the only member and owner
    def __init__(self, gid:int) -> None:
        self._id = gid

    @property
    def members(self) -> T.Iterator[DummyUser]:
        yield DummyUser(os.getuid())

    owners = members


class DummyIdentityManager(idm.base.IdentityManager):
    def __init__(self, cfg:config.base.Config) -> None:
        pass

    def user(self, *, uid:int) -> T.Optional[DummyUser]:
        return DummyUser(uid)

    def group(self, *, gid:int) -> T.Optional[DummyGroup]:
        return DummyGroup(gid)
