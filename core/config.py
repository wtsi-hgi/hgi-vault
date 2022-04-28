"""
Copyright (c) 2020 Genome Research Limited

Authors:
* Christopher Harrison <ch12@sanger.ac.uk>
* Aiden Neale <an12@sanger.ac.uk>

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

import os
from abc import ABCMeta, abstractmethod
from functools import singledispatchmethod

from . import typing as T


class exception(T.SimpleNamespace):
    """ Namespace of exceptions to make importing easier """
    class NoSuchSetting(Exception):
        """ Raised when a setting access is attempted that does not exist """

    class InvalidConfiguration(Exception):
        """ Raised when configuration validation fails """

    class InvalidSemantics(InvalidConfiguration):
        """ Raised when validation fails due to semantic error """

    class ConfigurationNotFound(Exception):
        """ Raised when the configuration file cannot be found """


def _path(env: str, *paths: T.Path) -> T.Path:
    """
    Return the file path of the configuration file from a number of
    options in the given precedence

    @param   env     The environment variable to read
    @param   *paths  Any number of paths
    @return  The existing configuration file path
    """
    # Prepend the value from the environment variable, if it exists
    if (from_environment := os.getenv(env)) is not None:
        paths = (from_environment,) + paths

    for from_file in paths:
        if (cfg := T.Path(from_file).expanduser()).is_file():
            return cfg.resolve()

    raise exception.ConfigurationNotFound("No configuration found")


ValueT = T.Any
NodeT = T.Mapping[str, ValueT]


class _BaseConfig(metaclass=ABCMeta):
    """ Abstract base class for tree-like configuration container """
    _contents: NodeT

    @singledispatchmethod
    def __init__(self, source: T.Any) -> None:
        """ Build the configuration node from source """
        self._contents = self._build(source)
        if not self._is_valid:
            raise exception.InvalidSemantics("Configuration did not validate")

    @__init__.register(dict)
    def _(self, source: NodeT) -> None:
        """ Build the configuration node from explicit contents """
        self._contents = source

    @__init__.register
    def _(self, source: None) -> None:
        """ Forbid null-configuration """
        raise exception.InvalidConfiguration(
            "Cannot build configuration from nothing")

    def __getattr__(self, item: str) -> T.Union[_BaseConfig, ValueT]:
        try:
            contents = self._contents[item]
        except KeyError:
            raise exception.NoSuchSetting(f"No such setting \"{item}\"")

        # We create a (shallow) copy for sub-branches, to avoid
        # downstream changes to the contents
        return type(self)(contents.copy()) if isinstance(contents, dict) else contents

    def __dir__(self) -> T.List[str]:
        # Convenience method for REPL use
        return list(self._contents.keys())

    @staticmethod
    @abstractmethod
    def _build(source: T.Any) -> NodeT:
        """
        Build contents from some external source

        @param   source  Some external source
        @return  Dictionary of configuration tree
        """

    @property
    @abstractmethod
    def _is_valid(self) -> bool:
        """ Are the contents valid? """


class base(T.SimpleNamespace):
    """ Namespace of base classes to make importing easier """
    Config = _BaseConfig


class utils(T.SimpleNamespace):
    """ Namespace of utilities to make importing easier """
    path = _path
