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
from base64 import b64encode
from enum import Enum

from .. import typing as T, file


class Branch(Enum):
    """ Vault branch/subvault enumeration """
    Keep    = "keep"
    Archive = "archive"


def _path_to_vault_key(path:T.Path) -> T.Path:
    """
    Return the vault key where the given file ought to be stored

    @param   path  Path to a regular file
    @return  Vault key path
    """
    # TODO Make sure the path is relative to the vault location

    # The hexidecimal representation of the inode ID, padded to 8-bytes
    inode = f"{file.inode_id(path):x}"
    if len(inode) % 2:
        inode = f"0{inode}"

    # The base64 encoding of the path
    basename = b64encode(str(path).encode()).decode()

    # Chunk the inode ID into 8-byte segments and concatenate the base64
    # encoded basename
    chunks = [inode[i:i+2] for i in range(0, len(inode), 2)]
    chunks[-1] += f"-{basename}"

    return T.Path(*chunks)


class BaseVault(metaclass=ABCMeta):
    _location:T.Path

    @abstractmethod
    def in_vault(self, path:T.Path) -> T.Optional[Branch]:
        """
        Return the branch in which the given file is found, or None if
        the file is not contained in the vault

        @param   path  Path to regular file
        @return  Appropriate branch or None
        """

    @abstractmethod
    def add_to_vault(self, branch:Branch, path:T.Path) -> None:
        """
        TODO
        """

    @abstractmethod
    def remove_from_vault(self, branch:Branch, path:T.Path) -> None:
        """
        TODO
        """

    @property
    def location(self) -> T.Path:
        """ Return the vault location """
        return self._location
