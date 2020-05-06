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

from core import typing as T, file


class InvalidRoot(Exception):
    """ Raised when a vault root is not an absolute path """

class IncorrectVault(Exception):
    """ Raised when access is attempted from the wrong vault """

class PhysicalVaultFile(Exception):
    """ Raised when a file physically inside the vault is referenced """

class NotRegularFile(Exception):
    """ Raised when a file is not a regular file """

class PermissionDenied(Exception):
    """ Raised when a file cannot be added or removed from the vault """

class DoesNotExist(Exception):
    """ Raised when a file does not exist """


class Branch(Enum):
    """ Vault branch/subvault enumeration """
    # It would be nice if this could also be a subclass of os.PathLike,
    # but because both that and Enum do metaclass trickery, we can't :(
    Keep    = T.Path("keep")
    Archive = T.Path("archive")


def _path_to_vault_key(path:T.Path) -> T.Path:
    """
    Return the vault key where the given file ought to be stored

    @param   path  Path to a regular file
    @return  Vault key path
    """
    # TODO This should become HGIVault._vault_key

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
    """ Abstract base class for vault implementations """
    _root:T.Path
    _vault:T.ClassVar[T.Path]

    ## Abstract methods

    @abstractmethod
    def _vault_key(self, branch:Branch, path:T.Path) -> T.Path:
        """
        Return the vault key; i.e., the path where the given file ought
        to be stored

        @param   branch  Vault branch
        @param   path    Path to regular file
        @return  Vault key path
        """
        # FIXME The return value is going to be too specific; we need
        # some concept of "specific" and "minimal" paths

    @abstractmethod
    def check_add_permissions(self, path:T.Path) -> None:
        """
        Check the permissions of the given file for adding to the vault;
        if they are not satisfied, raise a PermissionDenied exception

        @param   path  Path to file
        """

    @abstractmethod
    def _add_to_vault(self, branch:Branch, path:T.Path) -> None:
        """
        Add the given file to the specified vault branch

        @param   branch  Vault to branch
        @param   path    Path to file
        """

    @abstractmethod
    def check_remove_permissions(self, path:T.Path) -> None:
        """
        Check the permissions of the given file for removing from the
        vault; if they are not satisfied, raise a PermissionDenied
        exception

        @param   path  Path to file
        """

    @abstractmethod
    def _remove_from_vault(self, branch:Branch, path:T.Path) -> None:
        """
        Remove the given file from the specified vault branch

        @param   branch  Vault to branch
        @param   path    Path to file
        """

    ## Properties

    def _set_root(self, path:T.Path) -> None:
        """ Set the root vault """
        if not path.is_absolute() or not path.resolve().exists():
            raise InvalidRoot(f"A vault cannot exist in {path}")

        self._root = path

    root = property(fset=_set_root)

    @property
    def location(self) -> T.Path:
        """ Return the vault location """
        return self._root / self._vault

    ## Standard Methods

    def _relative_path(self, path:T.Path) -> T.Path:
        """
        Return the specified path relative to the vault's root
        directory. If the path is outside the root, then raise an
        IncorrectVault exception; if that path is physically within the
        vault, then raise a PhysicalVaultFile exception.

        @param   path  Path to regular file
        @return  Path relative to vault root
        """
        path = path.resolve()
        root = self._root
        vault = self.location

        try:
            _ = path.relative_to(vault)
            raise PhysicalVaultFile(f"{path} is physically contained in the vault in {root}")
        except ValueError:
            pass

        try:
            return path.relative_to(root)
        except ValueError:
            raise IncorrectVault(f"{path} does not belong to the vault in {root}")

    def _canonicalise(self, perm_checker:T.Callable[[T.Path], None], path:T.Path) -> T.Path:
        """
        Check the given file is a regular file, exists, has the correct
        permissions and return its path relative to the vault root; if
        any of these steps fail, an appropriate exception will be raised

        @param   perm_checker  Permissions checking method
        @param   path          Path to file
        @return  Path relative to the vault root
        """
        if not file.is_regular(path):
            raise NotRegularFile(f"{path} is not a regular file")

        if not path.exists():
            raise DoesNotExist(f"{path} does not exist")

        perm_checker(path)

        return self._relative_path(path)

    def in_vault(self, path:T.Path) -> T.Optional[Branch]:
        """
        Return the branch in which the given file is found, or None if
        the file is not contained in the vault

        @param   path  Path to regular file
        @return  Appropriate branch or None
        """
        path = self._relative_path(path)

        for branch in Branch:
            # FIXME This will break if the path has been added to the
            # vault and renamed in the meantime; the return of
            # _vault_key needs to have higher fidelity
            if self._vault_key(branch, path).exists():
                return branch

        return None

    def add_to_vault(self, branch:Branch, path:T.Path) -> None:
        """
        Add the given file to the specified vault branch

        @param   branch  Vault to branch
        @param   path    Path to file
        """
        path = self._canonicalise(self.check_add_permissions, path)
        self._add_to_vault(branch, path)

    def remove_from_vault(self, branch:Branch, path:T.Path) -> None:
        """
        Remove the given file from the specified vault branch

        @param   branch  Vault to branch
        @param   path    Path to file
        """
        path = self._canonicalise(self.check_remove_permissions, path)
        self._remove_from_vault(branch, path)


class HGIVault(BaseVault):
    _vault = T.Path(".vault")

    # TODO Implementations
