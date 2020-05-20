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

import os.path
from os import PathLike

from core import typing as T, file, ldap
from core.logging import Logger
from core.utils import base64
from core.vault import base, exception


class Branch(base.Branch):
    """ HGI vault branches """
    Keep    = T.Path("keep")
    Archive = T.Path("archive")


_PrefixSuffixT = T.Tuple[T.Optional[T.Path], T.Path]

class _VaultFileKey(PathLike):
    """ HGI vault file key properties """
    # NOTE This is implemented in a separate class to keep that part of
    # the logic outside VaultFile and to decouple it from the filesystem
    _delimiter:T.ClassVar[str] = "-"

    _prefix:T.Optional[T.Path]  # inode prefix path, without the LSB
    _suffix:T.Path              # LSB and encoded basename suffix path

    def __init__(self, *, inode:T.Optional[int]       = None,
                          path:T.Optional[T.Path]     = None,
                          key_path:T.Optional[T.Path] = None) -> None:
        """
        Construct the key either from an inode-path tuple, or recovered
        from a key's path

        @param   inode     inode ID to construct from
        @param   path      Path to construct from
        @param   key_path  Key path to recover from
        """
        try:
            # NOTE inode-path and key_path are mutually exclusive and
            # one MUST be provided. It would be messy to do this with
            # single dispatch, so we roll our own multiple dispatch...
            # which is equally messy :P
            dispatch, *args = {
                (False, False, True):  (self._construct, inode, path),
                (True,  True,  False): (self._recover, key_path)
            }[inode is None, path is None, key_path is None]
        except KeyError:
            raise TypeError(f"{self.__class__.__name__} must be constructed with inode and path arguments OR from a key path")

        self._prefix, self._suffix = dispatch(*args)

    def _construct(self, inode:int, path:T.Path) -> _PrefixSuffixT:
        """ Construct the vault file key from an inode ID and path """
        # The byte-padded hexidecimal representation of the inode ID
        inode_hex = f"{inode:x}"
        if len(inode_hex) % 2:
            inode_hex = f"0{inode_hex}"

        # Chunk the inode ID into 8-bit segments
        chunks = [inode_hex[i:i+2] for i in range(0, len(inode_hex), 2)]

        # inode ID, without the least significant byte, if it exists
        dirname = None
        if len(chunks) > 1:
            dirname = T.Path(*chunks[:-1])

        # inode ID LSB, delimiter, and the base64 encoding of the path
        prefix = chunks[-1] + self._delimiter
        basename = T.Path(prefix + base64.encode(str(path)))

        return dirname, basename

    def _recover(self, path:T.Path) -> _PrefixSuffixT:
        """ Recover the vault file key from a vault file key path """
        dirname, basename = os.path.split(path)
        prefix = T.Path(dirname) if dirname else None
        return prefix, T.Path(basename)

    def __eq__(self, rhs:_VaultFileKey) -> bool:
        return self._prefix == rhs._prefix \
           and self._suffix == rhs._suffix

    def __bool__(self) -> bool:
        return True

    def __fspath__(self) -> str:
        return str(self.path)

    @property
    def path(self) -> T.Path:
        return self._suffix if self._prefix is None \
          else T.Path(self._prefix, self._suffix)

    @property
    def source(self) -> T.Path:
        """ Return the source file path """
        _, encoded = self._suffix.name.split(self._delimiter)
        return T.Path(base64.decode(encoded).decode())

    #def alternate(self, search_base:T.Path) -> T.Optional[_VaultFileKey]:
    #    """
    #    Return an alternate key if one exists in the given search base

    #    @param   search_base  Search base path
    #    @return  Alternate key (None, if not found)
    #    """
    #    # NOTE This method couples this class to the filesystem, however
    #    # it relies on its internal implementation details, so it makes
    #    # sense for it to belong here. However, this coupling gives
    #    # justification for merging this class into VaultFile...
    #    if self._prefix is not None:
    #        search_base = search_base / self._prefix

    #    lsb, _ = self._suffix.name.split(self._delimiter)

    #    try:
    #        # NOTE This assumes there's only ever one match
    #        alt, *_ = search_base.glob(f"{lsb}{self._delimiter}*")
    #        alt = T.Path(alt.name)
    #    except ValueError:
    #        # Alternate not found
    #        return None

    #    if alt == self._suffix:
    #        # Alternate not found
    #        # FIXME This is wrong; it's dependant upon the branch!
    #        return None

    #    if self._prefix is not None:
    #        alt = self._prefix / alt

    #    return _VaultFileKey(key_path=alt)


class VaultFile(base.VaultFile):
    """ HGI vault file implementation """
    _key:_VaultFileKey  # Vault key (path) of external file

    def __init__(self, vault:Vault, branch:Branch, path:T.Path) -> None:
        self.vault = vault
        self.branch = branch
        path = path.resolve()

        if not path.exists():
            raise exception.DoesNotExist(f"{path} does not exist")

        if not file.is_regular(path):
            raise exception.NotRegularFile(f"{path} is not a regular file")

        inode = file.inode_id(path)
        path = self._relative_path(path)
        self._key = _VaultFileKey(inode=inode, path=path)

        # Check for corresponding keys in the vault, automatically
        # update if the branch or path differ in that alternate and log
        already_found = False
        for check in Branch:
            alternate_key = self._alternate(check, self._key)

            if alternate_key:
                if already_found:
                    raise exception.VaultCorruption(f"The vault in {vault.root} contains duplicates of {path}")
                already_found = True

                self._key = alternate_key

                if check != branch:
                    # Branch differs from expectation
                    # TODO This should be logged
                    self._branch = check

                if alternate_key.source != path:
                    # Path differs from expectation (e.g., source was
                    # moved or renamed)
                    # TODO This should be logged
                    pass

        # If a key already exists in the vault, then it must have at
        # least two hardlinks. If it has one, then the source file has
        # been removed...which is bad :P
        if self.path.exists() and file.hardlinks(self.path) == 1:
            raise exception.VaultCorruption(f"The vault in {vault.root} contains {self.source}, but this no longer exists outside the vault")

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

    def _alternate(self, branch:Branch, key:_VaultFileKey) -> T.Optional[_VaultFileKey]:
        # TODO This should be migrated from _VaultFileKey.alternate
        pass

    @property
    def path(self) -> T.Path:
        return self.vault.location / self.branch.value / self._key

    @property
    def source(self) -> T.Path:
        return self.vault.location / self._key.source

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
    _branch_enum = Branch
    _file_type   = VaultFile
    _vault       = T.Path(".vault")

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

    def list(self, branch:Branch) -> T.Iterator[T.Path]:
        # TODO
        pass
