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
from functools import cached_property

from core import typing as T, file, idm as IdM, logging
from core.utils import base64, umask
from core.vault import base, exception


class Branch(base.Branch):
    """ HGI vault branches """
    Keep    = T.Path("keep")
    Archive = T.Path("archive")
    Staged  = T.Path(".staged")


_PrefixSuffixT = T.Tuple[T.Optional[T.Path], str]

class _VaultFileKey(os.PathLike):
    """ HGI vault file key properties """
    # NOTE This is implemented in a separate class to keep that part of
    # the logic outside VaultFile and to decouple it from the filesystem
    _delimiter:T.ClassVar[str] = "-"

    _prefix:T.Optional[T.Path]  # inode prefix path, without the LSB
    _suffix:str                 # LSB and encoded basename suffix name

    def __init__(self, path:T.Path, inode:T.Optional[int] = None) -> None:
        """
        Construct the key from a path and (optional) inode

        @param   path      Path to construct from
        @param   inode     inode ID to construct from (defaults to inode
                           of path)
        """
        # Use the path's inode, if one is not explicitly provided
        if inode is None:
            inode = file.inode_id(path)

        # The byte-padded hexadecimal representation of the inode ID
        if len(inode_hex := f"{inode:x}") % 2:
            inode_hex = f"0{inode_hex}"

        # Chunk the inode ID into 8-bit segments
        chunks = [inode_hex[i:i+2] for i in range(0, len(inode_hex), 2)]

        # inode ID, without the least significant byte, if it exists
        self._prefix = None
        if len(chunks) > 1:
            self._prefix = T.Path(*chunks[:-1])

        # inode ID LSB, delimiter, and the base64 encoding of the path
        self._suffix = chunks[-1] + self._delimiter + base64.encode(path)

    @classmethod
    def Reconstruct(cls, key_path:T.Path) -> _VaultFileKey:
        """
        Alternative constructor: Reconstruct the key from a key path

        @param   key_path  Key path
        @return  Reconstructed _VaultFileKey
        """
        path, inode = cls._decode_key(key_path)
        return cls(path, inode)

    @classmethod
    def _decode_key(cls, key_path:T.Path) -> T.Tuple[T.Path, int]:
        """ Decode a key path into its original path and inode ID """
        inode_hex, path_b64 = "".join(key_path.parts).split(cls._delimiter)
        return T.Path(base64.decode(path_b64).decode()), int(inode_hex, 16)

    def __eq__(self, rhs:_VaultFileKey) -> bool:
        return self._prefix == rhs._prefix \
           and self._suffix == rhs._suffix

    def __bool__(self) -> bool:
        return True

    def __fspath__(self) -> str:
        return str(self.path)

    @cached_property
    def path(self) -> T.Path:
        return T.Path(self._suffix) if self._prefix is None \
          else T.Path(self._prefix, self._suffix)

    @cached_property
    def source(self) -> T.Path:
        """ Return the source file path """
        path, _ = self._decode_key(self.path)
        return path

    @cached_property
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
        log = vault.log
        path = path.resolve()

        if not path.exists():
            raise exception.DoesNotExist(f"{path} does not exist")

        if not file.is_regular(path):
            raise exception.NotRegularFile(f"{path} is not a regular file")

        inode = file.inode_id(path)
        path = self._relative_path(path)
        self._key = expected_key = _VaultFileKey(path, inode)

        # Check for corresponding keys in the vault, automatically
        # update if the branch or path differ in that alternate and log
        already_found = False
        for check in Branch:
            # NOTE The alternate key could be the expected key; we don't
            # bother checking for that, because it's effectively a noop
            if alternate_key := self._preexisting(check, expected_key):
                if already_found:
                    raise exception.VaultCorruption(f"The vault in {vault.root} contains duplicates of {path} in the {already_found} branch")
                already_found = check

                self._key = alternate_key

                if check != branch:
                    # Branch differs from expectation
                    log.info(f"{path} was found in the {check} branch, rather than {branch}")
                    self.branch = check

                if alternate_key.source != path:
                    # Path differs from expectation
                    # (i.e., source was moved or renamed)
                    log.info(f"{path} was found in the vault as {alternate_key.source}")

        # If a key already exists in the vault, then it must have:
        # * At least two hardlinks, when in the Keep or Archive branch
        # * Exactly one hardlink, when in the Staged branch
        if self.exists:
            staged = self.branch == Branch.Staged
            single_hardlink = file.hardlinks(self.path) == 1

            if not staged and single_hardlink:
                # NOTE This is not physically possible
                raise exception.VaultCorruption(f"The vault in {vault.root} contains {self.source}, but this no longer exists outside the vault")

            if staged and not single_hardlink:
                raise exception.VaultCorruption(f"{self.source} is staged in the vault in {vault.root}, but also exists outside the vault")

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

        search_base = branch_base = self.vault.location / branch
        if key_base is not None:
            search_base = search_base / key_base

        try:
            alt_suffix, *others = search_base.glob(key_glob)
        except ValueError:
            # Alternate not found
            return None

        if len(others) != 0:
            # If the glob finds multiple matches, that's bad!
            raise exception.VaultCorruption(f"The vault in {self.vault.root} contains duplicates of {key.path} in the {branch} branch")

        alternate = T.Path(alt_suffix)
        if key_base is not None:
            alternate = key_base / alternate

        # The VFK must be relative to the branch
        return _VaultFileKey.Reconstruct(alternate.relative_to(branch_base))

    @property
    def path(self) -> T.Path:
        return self.vault.location / self.branch / self._key

    @property
    def source(self) -> T.Path:
        return self.vault.root / self._key.source

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
        if source_mode & ugrw != ugrw:
            log.info(f"{source} is not read-writable by both its owner and group")
            return False

        user_perms = (source_mode & stat.S_IRWXU) >> 3
        group_perms = source_mode & stat.S_IRWXG
        if user_perms != group_perms:
            log.info(f"The owner and group permissions do not match for {source}")
            return False

        parent_mode = source.parent.stat().st_mode
        ugwx = stat.S_IWUSR | stat.S_IXUSR | stat.S_IWGRP | stat.S_IXGRP
        if parent_mode & ugwx != ugwx:
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
_UMASK = stat.S_IRWXO

class Vault(base.Vault, logging.base.LoggableMixin):
    """ HGI vault implementation """
    _branch_enum = Branch
    _file_type   = VaultFile
    _vault       = T.Path(".vault")

    # Injected dependencies
    _idm:IdM.base.IdentityManager

    # Class-level logging configuration
    _level     = logging.levels.default
    _formatter = logging.formats.with_username

    def __init__(self, relative_to:T.Path, *, idm:IdM.base.IdentityManager, autocreate:bool = True) -> None:
        """
        Constructor

        @param  relative_to  Location relative to Vault
        @param  idm          Identity manager
        @param  autocreate   Automatically create infrastructure if it
                             doesn't exist, otherwise raise NoSuchVault
        """
        self._idm = idm

        # NOTE self.root can only be set once
        self.root = root = self._find_root(relative_to)

        # Initialise TTY logging for the vault
        self._logger = str(root)
        self.log.to_tty()

        with umask(_UMASK):
            if not self.location.is_dir():
                # Fail if we're not autocreating
                if not autocreate:
                    raise exception.NoSuchVault(f"No vault contained in {root}")

                # Create vault, if it doesn't already exist
                try:
                    self.location.mkdir(_PERMS)

                    # Make sure the ownership and permissions on the
                    # vault directory are correct...or it won't work!
                    os.chown(self.location, uid=-1, gid=self.group)
                    self.location.chmod(_PERMS)  # See Python issue 41419

                    self.log.info(f"Vault created in {root}")
                except FileExistsError:
                    raise exception.VaultConflict(f"Cannot create a vault in {root}; user file already exists")

            # The vault must exist at this point, so persist log to disk
            (log_file := self.location / ".audit").touch()
            self.log.to_file(log_file)

            # Create branches, if they don't already exists
            for branch in Branch:
                if not (bpath := self.location / branch).is_dir():
                    try:
                        bpath.mkdir(_PERMS)
                        self.log.info(f"{branch} branch created in the vault in {root}")
                    except FileExistsError:
                        raise exception.VaultConflict(f"Cannot create a {branch} branch in the vault in {root}; user file already exists")

    @staticmethod
    def _find_root(relative_to:T.Path) -> T.Path:
        """
        The vault's location is the root of the homogroupic subtree that
        contains relative_to; that's where we start and traverse up
        """
        relative_to = relative_to.resolve()
        root = relative_to.parent if not relative_to.is_dir() else relative_to
        while root != T.Path("/") and root.group() == root.parent.group():
            root = root.parent

        return root

    @cached_property
    def group(self) -> int:
        """ Return the group ID of the vault location """
        return self.root.stat().st_gid

    @cached_property
    def owners(self) -> T.Iterator[int]:
        """ Return an iterator of group owners' user IDs """
        if (group := self._idm.group(gid=self.group)) is None:
            raise IdM.exception.NoSuchIdentity(f"No group found with ID {self.group}")

        return (user.uid for user in group.owners)

    def add(self, branch:Branch, path:T.Path) -> VaultFile:
        log = self.log

        if (to_add := self.file(branch, path)).exists:
            # File is already in the vault
            if to_add.source.resolve() != path.resolve() or to_add.branch != branch:
                # If the file is in the vault, but it's been renamed or
                # is found in a different branch, then we delete it from
                # its incorrect location and re-add it (rather than
                # attempting to correct by moving)
                log.info(f"Correcting vault entry for {path}")
                to_add.path.unlink()
                to_add = self.add(branch, path)

            else:
                log.info(f"{path} is already in the {branch} branch of the vault in {self.root}")

        else:
            # File is not in the vault
            if not to_add.can_add:
                raise exception.PermissionDenied(f"Cannot add {path} to the vault in {self.root}")

            with umask(_UMASK):
                to_add.path.parent.mkdir(_PERMS, parents=True, exist_ok=True)
                to_add.source.link_to(to_add.path)

            log.info(f"{to_add.source} added to the {to_add.branch} branch of the vault in {self.root}")

        return to_add

    def remove(self, branch:Branch, path:T.Path) -> None:
        # NOTE We are not interested in the branch
        log = self.log

        if not (to_remove := self.file(branch, path)).can_remove:
            # NOTE This exception is raised whether the file is in the
            # vault or not (i.e., so not to reveal that information)
            raise exception.PermissionDenied(f"Cannot remove {path} from the vault in {self.root}")

        if to_remove.exists:
            # NOTE to_remove.branch and to_remove.source might not match
            # branch and path, respectively
            to_remove.path.unlink()
            log.info(f"{to_remove.source} has been removed from the {to_remove.branch} branch of the vault in {self.root}")

        else:
            log.info(f"{to_remove.source} is not in the vault in {self.root}")

    def list(self, branch:Branch) -> T.Iterator[T.Path]:
        # NOTE The order in which the listing is generated is
        # unspecified (I suspect it will be by inode ID); it is up to
        # downstream to modify this, as required
        bpath = self.location / branch

        return (
            self.root / _VaultFileKey.Reconstruct(T.Path(dirname, file).relative_to(bpath)).source
            for dirname, _, files in os.walk(bpath)
            for file in files
        )
