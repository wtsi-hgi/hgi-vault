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

import os
import os.path
import stat

from core import typing as T, file, ldap
from core.logging import Logger
from core.utils import base64
from core.vault import base, exception


class Branch(base.Branch):
    """ HGI vault branches """
    Keep    = T.Path("keep")
    Archive = T.Path("archive")


_PrefixSuffixT = T.Tuple[T.Optional[T.Path], str]

class _VaultFileKey(os.PathLike):
    """ HGI vault file key properties """
    # NOTE This is implemented in a separate class to keep that part of
    # the logic outside VaultFile and to decouple it from the filesystem
    _delimiter:T.ClassVar[str] = "-"

    _prefix:T.Optional[T.Path]  # inode prefix path, without the LSB
    _suffix:str                 # LSB and encoded basename suffix name

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
        basename = chunks[-1] + self._delimiter + base64.encode(str(path))

        return dirname, basename

    def _recover(self, path:T.Path) -> _PrefixSuffixT:
        """ Recover the vault file key from a vault file key path """
        dirname, basename = os.path.split(path)
        prefix = T.Path(dirname) if dirname else None
        return prefix, basename

    def __eq__(self, rhs:_VaultFileKey) -> bool:
        return self._prefix == rhs._prefix \
           and self._suffix == rhs._suffix

    def __bool__(self) -> bool:
        return True

    def __fspath__(self) -> str:
        return str(self.path)

    @property
    def path(self) -> T.Path:
        return T.Path(self._suffix) if self._prefix is None \
          else T.Path(self._prefix, self._suffix)

    @property
    def source(self) -> T.Path:
        """ Return the source file path """
        _, encoded = self._suffix.split(self._delimiter)
        return T.Path(base64.decode(encoded).decode())

    @property
    def search_criteria(self) -> _PrefixSuffixT:
        """ Return the prefix and suffix glob pattern """
        lsb, _ = self._suffix.split(self._delimiter)
        return self._prefix, f"{lsb}{self._delimiter}*"


class VaultFile(base.VaultFile):
    """ HGI vault file implementation """
    _key:_VaultFileKey  # Vault key of external file

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
        self._key = expected_key = _VaultFileKey(inode=inode, path=path)

        # Check for corresponding keys in the vault, automatically
        # update if the branch or path differ in that alternate and log
        already_found = False
        for check in Branch:
            # NOTE The alternate key could be the expected key; we don't
            # bother checking for that, because it's effectively a noop
            alternate_key = self._preexisting(check, expected_key)

            if alternate_key:
                if already_found:
                    raise exception.VaultCorruption(f"The vault in {vault.root} contains duplicates of {path} in the {already_found.name} branch")
                already_found = check

                self._key = alternate_key

                if check != branch:
                    # Branch differs from expectation
                    # TODO This should be logged
                    self._branch = check

                if alternate_key.source != path:
                    # Path differs from expectation
                    # (i.e., source was moved or renamed)
                    # TODO This should be logged
                    pass

        # If a key already exists in the vault, then it must have at
        # least two hardlinks. If it has one, then the source file has
        # been removed...which is bad :P
        if self.exists and file.hardlinks(self.path) == 1:
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

    def _preexisting(self, branch:Branch, key:_VaultFileKey) -> T.Optional[_VaultFileKey]:
        """
        Return an pre-existing key, if one exists, in the given branch

        @param   branch  Branch to search
        @param   key     Key to match
        @return  Pre-existing key (None, if not found)
        """
        key_base, key_glob = key.search_criteria

        search_base = self.vault.location / branch.value
        if key_base is not None:
            search_base = search_base / key_base

        try:
            alt_suffix, *others = search_base.glob(key_glob)
        except ValueError:
            # Alternate not found
            return None

        if len(others) != 0:
            # If the glob finds multiple matches, that's bad!
            raise exception.VaultCorruption(f"The vault in {self.vault.root} contains duplicates of {key.path} in the {branch.name} branch")

        alternate = T.Path(alt_suffix)
        if key_base is not None:
            alternate = key_base / alternate

        return _VaultFileKey(key_path=alternate)

    @property
    def path(self) -> T.Path:
        return self.vault.location / self.branch.value / self._key

    @property
    def source(self) -> T.Path:
        return self.vault.location / self._key.source

    @property
    def can_add(self) -> bool:
        # Check that the file is:
        # * Regular
        # * Has at least ug+rw permissions
        # * Have equal user and group permissions
        # * Has a parent directory with at least ug+wx permissions
        source = self.source

        if not file.is_regular(source):
            # TODO Log file isn't regular
            return False

        source_mode = source.stat().st_mode
        ugrw = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP
        if not source_mode & ugrw:
            # TODO Log file isn't ug+rw
            return False

        user_perms = (source_mode & stat.S_IRWXU) >> 3
        group_perms = source_mode & stat.S_IRWXG
        if user_perms != group_perms:
            # TODO Log user and group permissions don't match
            return False

        parent_mode = source.parent.stat().st_mode
        ugwx = stat.S_IWUSR | stat.S_IXUSR | stat.S_IWGRP | stat.S_IXGRP
        if not parent_mode & ugwx:
            # TODO Log parent directory isn't ug+wx
            return False

        return True

    @property
    def can_remove(self) -> bool:
        # We have an additional constraint on removal: Only owners of
        # the group or the file itself can remove it from the vault
        source = self.source
        owner = source.stat().st_uid

        whoami = os.getuid()
        if whoami not in [*self.vault.owners, owner]:
            # TODO Log current user is not the group/file owner
            return False

        return self.can_add


class Vault(base.Vault):
    """ HGI vault implementation """
    _branch_enum = Branch
    _file_type   = VaultFile
    _vault       = T.Path(".vault")

    _ldap:ldap.LDAP
    log:Logger

    def __init__(self, relative_to:T.Path, *, log:Logger, ldap:ldap.LDAP) -> None:
        self.log = log
        self._ldap = ldap

        # TODO Set root location
        # TODO Create vault, if necessary

    @property
    def group(self) -> int:
        """ Return the group ID of the vault location """
        # TODO

    @property
    def owners(self) -> T.Iterator[int]:
        """ Return an iterator of group owners' user IDs """
        # TODO

    def add(self, branch:Branch, path:T.Path) -> None:
        # TODO
        pass

    def remove(self, branch:Branch, path:T.Path) -> None:
        # TODO
        pass

    def list(self, branch:Branch) -> T.Iterator[T.Path]:
        # TODO
        pass
