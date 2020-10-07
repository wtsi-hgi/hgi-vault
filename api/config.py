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

from abc import ABCMeta
from dataclasses import dataclass
from functools import cached_property

import yaml

from core import config, time, typing as T


class _YAMLConfig(config.base.Config, metaclass=ABCMeta):
    """ Abstract base class for building configuration from YAML """
    @staticmethod
    def _build(source:T.Path) -> T.Dict:
        with source.open() as stream:
            try:
                if not isinstance(parsed := yaml.safe_load(stream), dict):
                    raise config.exception.InvalidConfiguration(f"Configuration in {source.name} is not a mapping")
                return parsed

            except yaml.YAMLError:
                raise config.exception.InvalidConfiguration(f"Could not parse {source.name}")


# Convenience type constructors for days and hours (less than a month)
def _Days(days:int) -> T.TimeDelta:
    return time.delta(days=days)

def _HoursLessThanAMonth(hours:int) -> T.TimeDelta:
    if (delta := time.delta(hours=hours)) > time.delta(hours=720):
        raise TypeError("I'm not waiting that long")

    return delta

@dataclass
class _ListOf:
    """ Homogeneous Collection Type Constructor """
    cast:T.Type

    def __call__(self, data:T.Any):
        if not isinstance(data, list):
            data = [] if data is None else [data]

        return [self.cast(value) for value in data]


_TypeConstructor = T.Callable[[T.Any], T.Any]

class _Required:
    """ Sentinel object to mark required settings """

@dataclass
class _Setting:
    cast:_TypeConstructor = str
    default:T.Any = _Required()

    @property
    def is_scalar(self):
        return not isinstance(self.cast, _ListOf)


_schema = {
    "identity": {
        "ldap": {
            "host":          _Setting(),
            "port":          _Setting(cast=int, default=389)},
        "users": {
            "dn":            _Setting(),
            "attributes": {
                "uid":       _Setting(),
                "name":      _Setting(default="cn"),
                "email":     _Setting(default="mail")}},
        "groups": {
            "dn":            _Setting(),
            "attributes": {
                "gid":       _Setting(),
                "owners":    _Setting(default="owner"),
                "members":   _Setting(default="member")}}},

    "persistence": {
        "postgres": {
            "host":          _Setting(),
            "port":          _Setting(cast=int, default=5432)},
        "database":          _Setting(),
        "user":              _Setting(),
        "password":          _Setting()},

    "email": {
        "smtp": {
            "host":          _Setting(),
            "port":          _Setting(cast=int, default=25),
            "tls":           _Setting(cast=bool, default=False)},
        "sender":            _Setting()},

    "deletion": {
        "threshold":         _Setting(cast=_Days),
        "warnings":          _Setting(cast=_ListOf(_HoursLessThanAMonth), default=[])},

    "archive": {
        "threshold":         _Setting(cast=int),
        "handler":           _Setting(cast=T.Path)}}

def _validate(data:T.Dict, schema:T.Dict) -> bool:
    """
    Recursively validate and type cast the input data in-place against
    the given schema, returning the validity of the input
    """
    for key, setting in schema.items():
        if isinstance(setting, dict):
            # Descend the tree when we encounter a sub-schema
            if not key in data:
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
    @cached_property
    def _is_valid(self):
        return _validate(self._contents, _schema)
