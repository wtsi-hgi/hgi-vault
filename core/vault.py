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

from abc import ABCMeta, abstractmethod
from enum import Enum
from dataclasses import dataclass
from os import PathLike

from . import typing as T


class exception(T.SimpleNamespace):
    """ Namespace of exceptions to make importing easier """
    class InvalidRoot(Exception):
        """ Raised when a vault root is not an absolute path """

    class RootIsImmutable(Exception):
        """ Raised when an attempt to change the vault root is made """

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

    class VaultCorruption(Exception):
        """ Raised when duplicate/orphaned vault keys are detected """

    class VaultConflict(Exception):
        """ Raised whenever the vault conflicts with userland """

    class NoSuchVault(Exception):
        """ Raised whenever a vault doesn't exist where it's expected """

    class MinimumNumberOfOwnersNotMet(Exception):
        """Raised when an attempt to create a vault is made on a project
        that doesn't meet the required minimum number of owners"""


class _BaseBranch(Enum):
    """ Base vault branch/namespace enumeration """
    # It would be nice if this could also be a subclass of os.PathLike,
    # but because both that and Enum do metaclass trickery, we can't :(

    def __bool__(self) -> bool:
        # Always return truthy (see _BaseVault.__contains__)
        return True

    def __str__(self) -> str:
        return self.name

    def __fspath__(self) -> str:
        # We can't enforce enumerations to be os.PathLike at the type
        # level, but we can implement it anyway for syntactic sugar
        return str(self.value)


@dataclass(init=False)
class _VaultFile:
    """ Base properties """
    vault: _BaseVault
    branch: _BaseBranch


class _BaseVaultFile(PathLike, _VaultFile, metaclass=ABCMeta):
    """ Abstract base class for files stored in the vault """
    @abstractmethod
    def __init__(self, vault: _BaseVault, branch: _BaseBranch,
                 path: T.Path) -> None:
        """ Initialise the dataclass values """

    @property
    @abstractmethod
    def path(self) -> T.Path:
        """ Return the current path of the vault file """

    @property
    @abstractmethod
    def source(self) -> T.Path:
        """ Return the path of the external source file """

    @property
    @abstractmethod
    def can_add(self) -> bool:
        """ Predicate on whether the file can be added to the vault """

    @property
    @abstractmethod
    def can_remove(self) -> bool:
        """ Predicate on whether the file can be removed from the vault """

    def __fspath__(self) -> str:
        return str(self.path)

    @property
    def exists(self) -> bool:
        """ Check if the vault file exists """
        return self.path.exists()


_VFT = T.TypeVar("_VFT", bound=_BaseVaultFile)  # "Vault File Type"
_BranchT = T.TypeVar("_BranchT", bound=_BaseBranch)


class _BaseVault(T.Container[_VFT], metaclass=ABCMeta):
    """ Abstract base class for vault implementations """
    _branch_enum: T.ClassVar[T.Type[_BranchT]]
    _file_type: T.ClassVar[T.Type[_VFT]]
    _vault: T.ClassVar[T.Path]

    _root: T.Path

    # Abstract methods

    @abstractmethod
    def add(self, branch: _BranchT, path: T.Path) -> _VFT:
        """
        Add the given file to the specified vault branch

        @param   branch  Branch
        @param   path    Path
        @return  Added vault file
        """

    @abstractmethod
    def remove(self, branch: _BranchT, path: T.Path) -> None:
        """
        Remove the given file from the specified vault branch

        @param   branch  Branch
        @param   path    Path
        """

    @abstractmethod
    def list(self, branch: _BranchT) -> T.Iterator[T.Path]:
        """
        Return an iterator of files that exist in the given vault branch
        by their extra-vault paths (hence T.Path, rather than _VFT)

        @note    There is no guarantee on the order of the output

        @param   branch  Branch
        @return  Iterator of paths
        """

    # Properties

    @property
    def root(self) -> T.Path:
        return self._root

    @root.setter
    def root(self, path: T.Path) -> None:
        """ Set the root vault """
        try:
            root = self._root
            raise exception.RootIsImmutable(
                f"The vault root is already set to {root}")
        except AttributeError:
            pass

        if not path.is_absolute() or not path.resolve().exists():
            raise exception.InvalidRoot(f"A vault cannot exist in {path}")

        self._root = path

    @property
    def location(self) -> T.Path:
        """ Return the vault location """
        return self._root / self._vault

    # Standard Methods

    def __eq__(self, other: _BaseVault) -> bool:
        """ Equality predicate """
        return isinstance(other, type(self)) and self.root == other.root

    def __contains__(self, path: T.Path) -> bool:
        """ Check whether the given path is contained in the vault """
        # NOTE This is why _BaseBranch is always truthy
        # NOTE Technically, path should be of type _VFT, but using Path
        #      is much more convenient
        return bool(self.branch(path))

    def __hash__(self) -> int:
        return hash(self.root)

    def file(self, branch: _BranchT, path: T.Path) -> _VFT:
        """
        Return the vault file given by the specified branch and path;
        this will be required for .add and .remove, but probably won't
        be useful outside that context

        @param   branch  Vault branch
        @param   path    Path
        @return  Respective vault file, using the appropriate constructor
        """
        return self._file_type(self, branch, path)

    def branch(self, path: T.Path) -> T.Optional[_BranchT]:
        """
        Return the branch in which the given file is found, or None if
        the file is not contained in the vault

        @param   path  Path
        @return  Appropriate branch or None
        """
        # FIXME This works, but our VaultFile implementation
        # automatically corrects the branch, if the file is found in
        # another branch; that makes this code redundant. However, this
        # code is meant to be generic; maybe VaultFile.exists needs to
        # be corrected...
        for branch in self._branch_enum:
            vault_file = self.file(branch, path)
            if vault_file.exists and vault_file.branch == branch:
                return branch

        return None


class base(T.SimpleNamespace):
    """ Namespace of base classes to make importing easier """
    Branch = _BaseBranch
    VaultFile = _BaseVaultFile
    Vault = _BaseVault
