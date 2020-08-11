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

from abc import ABCMeta, abstractmethod
from dataclasses import dataclass

from . import config, idm, typing as T


class Anything:
    """ Sentinel class for wildcard searching """


@dataclass
class _BaseFile:
    """ Base class for file metadata """


class _BaseFileCollection(T.Collection[_BaseFile], metaclass=ABCMeta):
    """ Abstract base class for collections of files """
    _contents:T.List[_BaseFile]

    def __init__(self) -> None:
        self._contents = []

    def __len__(self) -> int:
        return len(self._contents)

    def __contains__(self, file:_BaseFile) -> bool:
        return file in self._contents

    def __iter__(self) -> T.Iterator[_BaseFile]:
        return iter(self._contents)

    def __iadd__(self, file:_BaseFile) -> _BaseFileCollection:
        """ Overload += to append new files """
        self._contents.append(file)
        self._accumulate(file)
        return self

    @abstractmethod
    def _accumulate(self, file:_BaseFile) -> None:
        """
        Add a file into any accumulators

        @param  file  File to accumulate
        """

    # TODO How to update notification state?


@dataclass
class _BaseState:
    """ Base class for file states """
    notified:T.Union[bool, Anything]


class _BasePersistence(metaclass=ABCMeta):
    @abstractmethod
    def __init__(self, config:config.base.Config, idm:idm.base.IdentityManager) -> None:
        """ Construct from configuration and injected IdM """

    @abstractmethod
    def persist(self, file:_BaseFile, state:_BaseState) -> None:
        """
        Persist a file with its respective state

        @param  file   File object
        @param  state  File state
        """

    @property
    @abstractmethod
    def stakeholders(self) -> T.Iterator[idm.base.User]:
        """ Return an iterator of persisted file stakeholders """

    @abstractmethod
    def filter(self, state:_BaseState, stakeholder:T.Optional[idm.base.User] = None) -> _BaseFileCollection:
        """
        Get the persisted files by state and their optional stakeholder

        n.b., The parameters of the "state" object define the search
        criteria. The "Anything" sentinel can be used as a wildcard.

        @param   state        File state filter
        @param   stakeholder  Stakeholder user filter (optional)
        @return  Collection of files
        """


class base(T.SimpleNamespace):
    """ Namespace of base classes to make importing easier """
    File           = _BaseFile
    FileCollection = _BaseFileCollection
    State          = _BaseState
    Persistence    = _BasePersistence
