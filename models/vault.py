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

from core import typing as T, file
from core.ldap import LDAP
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
        if len(inode_hex := f"{inode:x}") % 2:
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

def _decode_key(path:T.Path) -> T.Path:
    """ Convenience function to decode a key path into its source """
    return _VaultFileKey(key_path=path).source


class VaultFile(base.VaultFile):
    """ HGI vault file implementation """
    _key:_VaultFileKey  # Vault key of external file

    def __init__(self, vault:Vault, branch:Branch, path:T.Path) -> None:
        self.vault = vault
        self.branch = branch
        log = vault.log
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
            if alternate_key := self._preexisting(check, expected_key):
                if already_found:
                    raise exception.VaultCorruption(f"The vault in {vault.root} contains duplicates of {path} in the {already_found.name} branch")
                already_found = check

                self._key = alternate_key

                if check != branch:
                    # Branch differs from expectation
                    log.info(f"{path} was found in the {check.name} branch, rather than {branch.name}")
                    self._branch = check

                if alternate_key.source != path:
                    # Path differs from expectation
                    # (i.e., source was moved or renamed)
                    log.info(f"{path} was found in the vault as {alternate_key.source}")

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
        log = self.vault.log
        source = self.source

        if not file.is_regular(source):
            log.info(f"{source} is not a regular file")
            return False

        source_mode = source.stat().st_mode
        ugrw = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP
        if not source_mode & ugrw:
            log.info(f"{source} is not read-writable by both its owner and group")
            return False

        user_perms = (source_mode & stat.S_IRWXU) >> 3
        group_perms = source_mode & stat.S_IRWXG
        if user_perms != group_perms:
            log.info(f"The owner and group permissions do not match for {source}")
            return False

        parent_mode = source.parent.stat().st_mode
        ugwx = stat.S_IWUSR | stat.S_IXUSR | stat.S_IWGRP | stat.S_IXGRP
        if not parent_mode & ugwx:
            log.info(f"The parent directory of {source} is not writable or executable for both its owner and group")
            return False

        return True

    @property
    def can_remove(self) -> bool:
        # We have an additional constraint on removal: Only owners of
        # the group or the file itself can remove it from the vault
        log = self.vault.log
        source = self.source
        owner = source.stat().st_uid

        if os.getuid() not in [*self.vault.owners, owner]:
            log.info(f"The current user is not the owner of {source} nor a group owner")
            return False

        return self.can_add


# Vault permissions: ug+rwx, g+s (i.e., 02770)
_PERMS = stat.S_ISGID | stat.S_IRWXU | stat.S_IRWXG

class Vault(base.Vault):
    """ HGI vault implementation """
    _branch_enum = Branch
    _file_type   = VaultFile
    _vault       = T.Path(".vault")

    # Injected dependencies
    log:Logger

    # Internal state
    _gid:int
    _owners:T.List[int]

    def __init__(self, relative_to:T.Path, *, log:Logger, ldap:LDAP) -> None:
        self.log = log

        # The vault's location is the root of the homogroupic subtree
        # that contains relative_to; that's where we start and traverse up
        relative_to = relative_to.resolve()
        root = relative_to.parent if not relative_to.is_dir() else relative_to
        while root != T.Path("/") and root.group() == root.parent.group():
            root = root.parent

        self.root = root  # NOTE self.root can only be set once
        self._gid = root.stat().st_gid

        # NOTE As the frequency of LDAP record changes is dwarfed by
        # that of vault construction, it makes sense to only lookup the
        # owner list here, rather than carrying around the LDAP
        # interface and doing expensive lookups on demand
        self._owners = []  # TODO Waiting on LDAP interface...

        # TODO Vault logger should have an additional handler that
        # writes to self.location / .audit -- this can't be kept
        # upstream, because it relies on knowing self.location...
        log_file = self.location / ".audit"

        # Create vault, if it doesn't already exist
        if not self.location.is_dir():
            try:
                self.location.mkdir(_PERMS)
                log.info(f"Vault created in {root}")
            except FileExistsError:
                raise exception.VaultConflict(f"Cannot create a vault in {root}; user file already exists")

        # Create branches, if they don't already exists
        for branch in Branch:
            if not (bpath := self.location / branch.value).is_dir():
                try:
                    bpath.mkdir(_PERMS)
                    log.info(f"{branch.name} branch created in the vault in {root}")
                except FileExistsError:
                    raise exception.VaultConflict(f"Cannot create a {branch.name} branch in the vault in {root}; user file already exists")

    @property
    def group(self) -> int:
        """ Return the group ID of the vault location """
        return self._gid

    @property
    def owners(self) -> T.Iterator[int]:
        """ Return an iterator of group owners' user IDs """
        yield from self._owners

    def add(self, branch:Branch, path:T.Path) -> None:
        log = self.log

        if not (to_add := self.file(branch, path)).can_add:
            raise exception.PermissionDenied(f"Cannot add {path} to the vault in {self.root}")

        if to_add.exists:
            # File is already in the vault
            if to_add.source.resolve() != path.resolve() or to_add.branch != branch:
                # If the file is in the vault, but it's been renamed or
                # is found in a different branch, then we delete it from
                # its incorrect location and re-add it (rather than
                # attempting to correct by moving)
                log.info(f"Correcting vault entry for {path}")
                to_add.path.unlink()
                self.add(branch, path)

            else:
                log.info(f"{path} is already in the {branch.name} branch of the vault in {self.root}"

        else:
            # File is not in the vault
            to_add.path.parent.mkdir(_PERMS, parents=True, exist_ok=True)
            to_add.source.link_to(to_add.path)

            log.info(f"{to_add.source} added to the {to_add.branch.name} branch of the vault in {self.root}")

    def remove(self, branch:Branch, path:T.Path) -> None:
        # TODO
        pass

    def list(self, branch:Branch) -> T.Iterator[T.Path]:
        # NOTE The order in which the listing is generated is
        # unspecified (I suspect it will be by inode ID); it is up to
        # downstream to modify this, as required
        bpath = self.location / branch.value

        return (
            _decode_key(T.Path(dirname, file).relative_to(bpath))
            for dirname, _, files in os.walk(bpath)
            for file in files
        )
