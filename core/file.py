"""
Copyright (c) 2020, 2021 Genome Research Limited

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

from abc import ABCMeta, abstractmethod
import os

from . import time, typing as T


class exception(T.SimpleNamespace):
    """Namespace of exceptions"""

    class UnactionableFile(Exception):
        """Raised when a file isn't actionable"""


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


def delete(path: T.Path) -> None:
    """
    Delete the given file

    @param  path  Path to file
    """
    # NOTE While trivial, this is for the sake of centralisation
    # (i.e., all deletes must go through here)
    path.unlink()


def inode_id(path: T.Path) -> int:
    """
    Return the inode ID for the given file, without following symlinks

    @param   path  Path to a regular file
    @return  inode ID
    """
    return path.stat().st_ino


def is_regular(path: T.Path) -> bool:
    """
    Check whether the given path is a regular file

    @param   path  Path
    @return  Predicate result
    """
    # NOTE Order is important as Path.is_file looks to follow symlinks
    return (not path.is_symlink()) and path.is_file()


def hardlinks(path: T.Path) -> int:
    """
    Return the number of hardlinks for the given file

    @param   path  Path
    @return  Number of hardlinks
    """
    return path.stat().st_nlink


def touch(path: T.Path, atime: T.Optional[T.DateTime]
          = None, mtime: T.Optional[T.DateTime] = None) -> None:
    """
    Update the access and/or modification time of a given file

    NOTE Only the file owner can change atime and mtime arbitrarily; the
    default behaviour (set both to the current time) is permitted by
    anyone who can write to the file

    NOTE This isn't quite the same as pathlib.Path.touch

    @param  path   Path
    @param  atime  New access time (None for don't change)
    @param  mtime  New modification time (None for don't change)
    """
    if mtime is None and atime is None:
        new_utime = None
    else:
        file_stat = path.stat()
        new_atime = file_stat.st_atime if atime is None else time.timestamp(
            atime)
        new_mtime = file_stat.st_mtime if mtime is None else time.timestamp(
            mtime)
        new_utime = (new_atime, new_mtime)

    os.utime(path, times=new_utime)
