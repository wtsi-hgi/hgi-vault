"""
Copyright (c) 2020 Genome Research Limited

Author: 
* Christopher Harrison <ch12@sanger.ac.uk>
* Piyush Ahuja <pa11@sanger.ac.uk>

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

from . import typing as T, time


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


def delete(path:T.Path) -> None:
    """
    Delete the given file

    @param  path  Path to file
    """
    # NOTE While trivial, this is for the sake of centralisation
    # (i.e., all deletes must go through here)
    path.unlink()


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
    # NOTE Order is important as Path.is_file looks to follow symlinks
    return (not path.is_symlink()) and path.is_file()


def hardlinks(path:T.Path) -> int:
    """
    Return the number of hardlinks for the given file

    @param   path  Path
    @return  Number of hardlinks
    """
    return path.stat().st_nlink

def update_mtime(path: T.Path, dt: T.DateTime) -> None:
    """
    Update the modification time of the file to the given time.

    @param path Path to file
    @path dt DateTime

    """
    # Naive dt instances are assumed to represent local time and timestamp()  method relies on the platform C mktime() function to perform the conversion. For "aware" dt instances, the mtime is to be computed as: (dt - datetime(1970, 1, 1, tzinfo=timezone.utc)).total_seconds(). To simply and not have to make this calculation, we convert every dt to UTC.

    dt = time.to_utc(dt)
    mtime = int(dt.timestamp())
    atime = path.stat().st_atime

    os.utime(path, (atime, mtime ))
