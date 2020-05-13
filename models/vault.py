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

from dataclasses import dataclass
from os import PathLike

from core import typing as T, file, ldap
from core.logging import Logger
from core.utils import base64
from core.vault import Branch, base, exception


_KEY_DELIMITER = "-"

@dataclass(init=False)
class _VaultFileKey(PathLike):
    """ HGI vault file key properties """
    # FIXME? I'm not sure it's necessary to separate this out into a
    # separate class; it could easily be a part of VaultFile. It does
    # make testing a bit easier, though...
    prefix:T.Path  # inode prefix path
    suffix:T.Path  # Basename suffix path

    def __init__(self, path:T.Path) -> None:
        # The hexidecimal representation of the inode ID, padded to a
        # multiple of 8-bytes
        inode = f"{file.inode_id(path):x}"
        if len(inode) % 2:
            inode = f"0{inode}"

        # Chunk the inode ID into 8-byte segments
        self.prefix = T.Path(*[inode[i:i+2] for i in range(0, len(inode), 2)])

        # The base64 encoding of the path
        self.suffix = T.Path(base64.encode(str(path)))

    def __fspath__(self) -> str:
        return str(self.path)

    @property
    def path(self) -> T.Path:
        return T.Path(f"{self.prefix}{_KEY_DELIMITER}{self.suffix}")


class VaultFile(base.VaultFile):
    """ HGI vault file implementation """
    _path:T.Path        # Path to external (non-vaulted) file (relative to vault root)
    _key:_VaultFileKey  # Vault key (path) of external file

    def __init__(self, vault:Vault, branch:Branch, path:T.Path) -> None:
        self.vault  = vault
        self.branch = branch

        if not path.exists():
            raise exception.DoesNotExist(f"{path} does not exist")

        if not file.is_regular(path):
            raise exception.NotRegularFile(f"{path} is not a regular file")

        self._path = self._relative_path(path)
        self._key = _VaultFileKey(self._path)

        # TODO Check the key to see if it already exists under a
        # different name; indicating that the given path has been
        # vaulted, but renamed/moved.
        # TODO Check number of hardlinks on key, if it exists; if it is
        # one, then the original file has been removed. Do what??

    def _relative_path(self, path:T.Path) -> T.Path:
        """
        Return the specified path relative to the vault's root
        directory. If the path is outside the root, then raise an
        IncorrectVault exception; if that path is physically within the
        vault, then raise a PhysicalVaultFile exception.

        @param   path  Path
        @return  Path relative to vault root
        """
        path  = path.resolve()
        root  = self.vault.root
        vault = self.vault.location

        try:
            _ = path.relative_to(vault)
            raise exception.PhysicalVaultFile(f"{path} is physically contained in the vault in {root}")
        except ValueError:
            pass

        try:
            return path.relative_to(root)
        except ValueError:
            raise exception.IncorrectVault(f"{path} does not belong to the vault in {root}")

    @property
    def path(self) -> T.Path:
        return self.vault.location / self.branch.value / self._key

    @property
    def can_add(self) -> bool:
        # TODO
        pass

    @property
    def can_remove(self) -> bool:
        # TODO
        pass


class Vault(base.Vault):
    """ HGI vault implementation """
    _vault = T.Path(".vault")
    _file_type = VaultFile

    log:Logger

    def __init__(self) -> None:
        # TODO
        pass

    def add(self, branch:Branch, path:T.Path) -> None:
        # TODO
        pass

    def remove(self, branch:Branch, path:T.Path) -> None:
        # TODO
        pass
