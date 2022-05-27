"""
Copyright (c) 2020, 2021, 2022 Genome Research Limited

Authors:
* Christopher Harrison <ch12@sanger.ac.uk>
* Piyush Ahuja <pa11@sanger.ac.uk>
* Michael Grace <mg38@sanger.ac.uk>

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

from abc import ABCMeta
from dataclasses import dataclass
import enum
from functools import cached_property

import yaml

from core import config, time, typing as T


class _YAMLConfig(config.base.Config, metaclass=ABCMeta):
    """ Abstract base class for building configuration from YAML """
    @staticmethod
    def _build(*sources: T.Path) -> T.Dict[T.Any, T.Any]:
        _config: T.Dict[T.Any, T.Any] = {}

        for source in sources:
            with source.open() as stream:
                try:
                    if not isinstance(parsed := yaml.safe_load(stream), dict):
                        parsed: T.Dict[T.Any, T.Any]
                        raise config.exception.InvalidConfiguration(
                            f"Configuration in {source.name} is not a mapping")

                    _config.update(parsed)

                except yaml.YAMLError:
                    raise config.exception.InvalidConfiguration(
                        f"Could not parse {source.name}")

        return _config


# Convenience type constructors for days and hours (less than a month)
def _Days(days: int) -> T.TimeDelta:
    return time.delta(days=days)


def _HoursLessThanThreeMonths(hours: int) -> T.TimeDelta:
    if (delta := time.delta(hours=hours)) > time.delta(days=90):
        raise TypeError("I'm not waiting that long")

    return delta


@dataclass
class _ListOf:
    """ Homogeneous Collection Type Constructor """
    cast: T.Type

    def __call__(self, data: T.Any):
        if not isinstance(data, list):
            data = [] if data is None else [data]

        return [self.cast(value) for value in data]


_TypeConstructor = T.Callable[[T.Any], T.Any]


class _Required:
    """ Sentinel object to mark required settings """


@dataclass
class _Setting:
    cast: _TypeConstructor = str
    default: T.Any = _Required()

    @property
    def is_scalar(self):
        return not isinstance(self.cast, _ListOf)


class ExecutableNamespace(T.SimpleNamespace):
    class InvalidExecutable(Exception):
        """raised when a config is attempted to be generated
        without a valid executable"""

    class Executable(enum.Enum):

        VAULT = enum.auto()
        SANDMAN = enum.auto()


Executable = ExecutableNamespace.Executable

_schema: T.Dict[Executable, T.Any] = {
    Executable.VAULT: {
        "identity": {
            "ldap": {
                "host": _Setting(),
                "port": _Setting(cast=int, default=389)},
            "users": {
                "dn": _Setting(),
                "attributes": {
                    "uid": _Setting(),
                    "name": _Setting(default="cn"),
                    "email": _Setting(default="mail")}},
            "groups": {
                "dn": _Setting(),
                "attributes": {
                    "gid": _Setting(),
                    "owners": _Setting(default="owner"),
                    "members": _Setting(default="member")}}},

        "deletion": {
            "threshold": _Setting(cast=_Days),
            "limbo": _Setting(cast=_Days),
            "warnings": _Setting(cast=_ListOf(_HoursLessThanThreeMonths), default=[])},


        "min_group_owners": _Setting(cast=int, default=3)
    },
    Executable.SANDMAN: {
        "persistence": {
            "postgres": {
                "host": _Setting(),
                "port": _Setting(cast=int, default=5432)},
            "database": _Setting(),
            "user": _Setting(),
            "password": _Setting()},

        "email": {
            "smtp": {
                "host": _Setting(),
                "port": _Setting(cast=int, default=25),
                "tls": _Setting(cast=bool, default=False)},
            "sender": _Setting()},

        "archive": {
            "threshold": _Setting(cast=int),
            "handler": _Setting(cast=T.Path)
        },
        "sandman_run_interval": _Setting(cast=_HoursLessThanThreeMonths, default=24)
    }
}


def _validate(data: T.Dict, schema: T.Dict) -> bool:
    """
    Recursively validate and type cast the input data in-place against
    the given schema, returning the validity of the input
    """
    for key, setting in schema.items():
        if isinstance(setting, dict):
            # Descend the tree when we encounter a sub-schema
            if key not in data:
                data[key] = {}

            if not _validate(data[key], schema[key]):
                return False

        else:
            if key not in data:
                # Check for optional settings
                if isinstance(setting.default, _Required):
                    return False

                data[key] = setting.default

            if setting.is_scalar and isinstance(data[key], list):
                # Scalar settings must not be lists
                return False

            try:
                # Cast input to expected type
                # NOTE Type constructors cannot be guaranteed to be
                # idempotent, so _validate can only be run against the
                # input data at most once
                data[key] = setting.cast(data[key])

            except (ValueError, TypeError):
                return False

    return True


class Config(_YAMLConfig):

    def __init__(self, *sources: T.Any, executables: T.Set[Executable]):
        self._executables = executables
        super().__init__(*sources)

    @cached_property
    def _is_valid(self):
        return all(_validate(self._contents, _schema[executable]) for executable in self._executables)

    @property
    def _extra_attr(self):
        return {
            "executables": self._executables
        }
