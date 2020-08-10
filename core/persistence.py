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

from . import typing as T


class exception(T.SimpleNamespace):
    """ Namespace of exceptions to make importing easier """


class _BaseState(metaclass=ABCMeta):
    """ Abstract base class for file states """


class base(T.SimpleNamespace):
    """ Namespace of base classes to make importing easier """
    State = _BaseState
