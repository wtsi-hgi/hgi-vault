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
from functools import singledispatchmethod

from . import typing as T


class exception(T.SimpleNamespace):
    """ Namespace of exceptions to make importing easier """
    class NoSuchSetting(Exception):
        """ Raised when a setting access is attempted that does not exist """

    class InvalidConfiguration(Exception):
        """ Raised when configuration validation fails """


ValueT = T.Any
NodeT = T.Mapping[str, ValueT]

class _BaseConfig(metaclass=ABCMeta):
    """ Abstract base class for tree-like configuration container """
    _contents:NodeT

    @singledispatchmethod
    def __init__(self, source:T.Any) -> None:
        """ Build the configuration node from source """
        self._contents = self.build(source)
        if not self.is_valid:
            raise exception.InvalidConfiguration("Configuration did not validate")

    @__init__.register(dict)
    def _(self, source:NodeT) -> None:
        """ Build the configuration node from explicit contents """
        self._contents = source

    @__init__.register
    def _(self, source:None) -> None:
        """ Forbid null-configuration """
        raise exception.InvalidConfiguration("Cannot build configuration from nothing")

    def __getattr__(self, item:str) -> T.Union[_BaseConfig, ValueT]:
        try:
            contents = self._contents[item]
        except KeyError:
            raise exception.NoSuchSetting(f"No such setting \"{item}\"")

        return type(self)(contents) if isinstance(contents, dict) else contents

    def __dir__(self) -> T.List[str]:
        # Convenience method for REPL use
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
