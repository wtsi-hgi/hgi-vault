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

from abc import ABCMeta, abstractmethod
from dataclasses import dataclass

<<<<<<< HEAD
from core import typing as T
=======
from . import config, typing as T
>>>>>>> develop


class exception(T.SimpleNamespace):
    """ Namespace of exceptions to make importing easier """
    class NoSuchIdentity(Exception):
        """ Raised when a non-existent identity is queried """


@dataclass(init=False)
class _Identity:
    """ Base class for identities """
    _id:int

class _User(_Identity, metaclass=ABCMeta):
    """ Abstract base class for user identities """
    @property
    def uid(self) -> int:
        return self._id

<<<<<<< HEAD
=======
    @property
    @abstractmethod
    def name(self) -> str:
        """ Return the user's real name """

    @property
    @abstractmethod
    def email(self) -> T.Optional[str]:
        """ Return the user's e-mail address """

>>>>>>> develop
class _Group(_Identity, metaclass=ABCMeta):
    """ Abstract base class for group identities """
    @property
    def gid(self) -> int:
        return self._id

    @property
    @abstractmethod
    def owners(self) -> T.Iterator[_User]:
        """ Return an iterator of users who are owners of the group """

    @property
    @abstractmethod
    def members(self) -> T.Iterator[_User]:
        """ Return an iterator of users who are members of the group """


class _IdentityManager(metaclass=ABCMeta):
    """ Abstract base class for identity management interface """
    @abstractmethod
<<<<<<< HEAD
=======
    def __init__(self, cfg:config.base.Config) -> None:
        """ Construct from configuration """

    @abstractmethod
>>>>>>> develop
    def user(self, *, uid:int) -> T.Optional[_User]:
        """
        Return the user identity given by the specified ID

        @param   uid  User ID
        @return  User identity (None, if not found)
        """

    @abstractmethod
    def group(self, *, gid:int) -> T.Optional[_Group]:
        """
        Return the group identity given by the specified ID

        @param   gid  Group ID
        @return  Group identity (None, if not found)
        """


class base(T.SimpleNamespace):
    """ Namespace of base classes to make importing easier """
    IdentityManager = _IdentityManager
    User            = _User
    Group           = _Group
