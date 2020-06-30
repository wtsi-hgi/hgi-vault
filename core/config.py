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

from . import typing as T


class exception(T.SimpleNamespace):
    """ Namespace of exceptions to make importing easier """
    class NoSuchSetting(Exception):
        """ Raised when a setting access is attempted that does not exist """

    class InvalidConfiguration(Exception):
        """ Raised when configuration validation fails """


ValueT = T.Any
NodeT = T.Dict[str, ValueT]

class _BaseConfig(metaclass=ABCMeta):
    """ Abstract base class for tree-like configuration container """
    _contents:NodeT

    def __init__(self, source:T.Any = None, *, contents:T.Optional[NodeT] = None) -> None:
        """ Build the configuration node from source or explicit contents """
        assert (source is None) ^ (contents is None)

        if source is not None:
            self._contents = self.build(source)
            if not self.is_valid:
                raise exception.InvalidConfiguration(f"Configuration is invalid")

        if contents is not None:
            self._contents = contents

    def __getattr__(self, item:str) -> T.Union[_BaseConfig, ValueT]:
        try:
            contents = self._contents[item]
        except KeyError:
            raise exception.NoSuchSetting(f"No such setting \"{item}\"")

        if isinstance(contents, dict):
            # Return value container
            container = self.__class__(contents=contents)
            return container

        # Return value
        return contents

    def __dir__(self) -> T.List[str]:
        return list(self._contents.keys())

    @staticmethod
    @abstractmethod
    def build(source:T.Any) -> NodeT:
        """
        Build contents from some external source

        @param   source  Some external source
        @return  Dictionary of configuration tree
        """

    @property
    @abstractmethod
    def is_valid(self) -> bool:
        """ Are the contents valid? """


class base(T.SimpleNamespace):
    """ Namespace of base classes to make importing easier """
    Config = _BaseConfig
