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


class exception(T.SimpleNamespace):
    class BackendException(Exception):
        """ Raised on persistence backend failure """

    class LogicException(BackendException):
        """ Raised on persistence backend logic error """


class Anything:
    """ Sentinel class for wildcard searching """


@dataclass
class Filter:
    """ Filter criteria """
    # NOTE The parameters of the "state" object define the state search
    # criteria; the "Anything" sentinel can be used as a wildcard, both
    # in the state parameters and as the stakeholder (default)
    state:_BaseState
    stakeholder:T.Union[idm.base.User, T.Type[Anything]] = Anything


@dataclass
class _BaseState:
    """ Base class for file states """
    notified:T.Union[bool, T.Type[Anything]]


@dataclass
class _BaseFile:
    """ Base class for file metadata """


class _BaseFileCollection(T.Collection[_BaseFile], T.ContextManager, metaclass=ABCMeta):
    """ Abstract base class for collections of files """
    _persistence:_BasePersistence
    _filter:Filter

    _contents:T.List[_BaseFile]

    def __init__(self, persistence:_BasePersistence, criteria:Filter) -> None:
        self._persistence = persistence
        self._filter = criteria
        self._contents = []

    def __len__(self) -> int:
        return len(self._contents)

    def __contains__(self, file:_BaseFile) -> bool:
        return file in self._contents

    def __iter__(self) -> T.Iterator[_BaseFile]:
        return iter(self._contents)

    def __exit__(self, *exc) -> bool:
        # If the context manager exits cleanly, then clean up the files
        if not all(exc):
            self._persistence.clean(self)

        return False

    def __iadd__(self, file:_BaseFile) -> _BaseFileCollection:
        """ Overload += to append new files """
        self._contents.append(file)
        self._accumulate(file)
        return self

    @property
    def criteria(self) -> Filter:
        """ Criteria used to generate the collection """
        return self._filter

    @abstractmethod
    def _accumulate(self, file:_BaseFile) -> None:
        """
        Add a file into any accumulators

        @param  file  File to accumulate
        """

    @property
    @abstractmethod
    def accumulator(self) -> T.Any:
        """ Return the accumulator object """


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
    def files(self, criteria:Filter) -> _BaseFileCollection:
        """
        Get the persisted files by state and their optional stakeholder

        @param   criteria  Filter object
        @return  Collection of files
        """

    @abstractmethod
    def clean(self, files:_BaseFileCollection) -> None:
        """
        Clean up persisted files

        @param   files  File collection to clean up
        """


class base(T.SimpleNamespace):
    """ Namespace of base classes to make importing easier """
    File           = _BaseFile
    FileCollection = _BaseFileCollection
    State          = _BaseState
    Persistence    = _BasePersistence
