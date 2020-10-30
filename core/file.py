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


class BaseFile(metaclass=ABCMeta):
    """ Base class for files """
    @property
    @abstractmethod
    def path(self) -> T.Path:
        """ Return the path of the file """

    @property
    @abstractmethod
    def age(self) -> T.TimeDelta:
        """ Return the age of the file """


def cwd() -> T.Path:
    """ Return the current working directory """
    return T.Path.cwd()


def inode_id(path:T.Path) -> int:
    """
    Return the inode ID for the given file, without following symlinks

    @param   path  Path to a regular file
    @return  inode ID
    """
    return path.stat().st_ino


def is_regular(path:T.Path) -> bool:
    """
    Check whether the given path is a regular file

    @param   path  Path
    @return  Predicate result
    """
    return path.is_file() and not path.is_symlink()


def hardlinks(path:T.Path) -> int:
    """
    Return the number of hardlinks for the given file

    @param   path  Path
    @return  Number of hardlinks
    """
    return path.stat().st_nlink
