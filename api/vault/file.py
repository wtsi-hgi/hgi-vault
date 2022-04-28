"""
Copyright (c) 2020, 2021 Genome Research Limited

Authors:
* Christopher Harrison <ch12@sanger.ac.uk>
* Piyush Ahuja <pa11@sanger.ac.uk>
* Michael Grace <mg38@sanger.ac.uk>
* Pavlos Antoniou <pa10@sanger.ac.uk>

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

import fnmatch
import os
import stat

import core.vault
from core import time, file, typing as T
from .common import Branch, BaseHGIVault
from .key import VaultFileKey

VaultExc = core.vault.exception


class VaultFile(core.vault.base.VaultFile):
    """ HGI vault file implementation """
    _key: VaultFileKey  # Vault key of external file

    def __init__(self, vault: BaseHGIVault, branch: Branch, path: T.Path) -> None:
        self.vault = vault
        self.branch = branch
        log = vault.log
        path = path.resolve()

        if not path.exists():
            raise VaultExc.DoesNotExist(f"{path} does not exist")

        if not file.is_regular(path):
            raise VaultExc.NotRegularFile(f"{path} is not a regular file")

        max_file_name_length: int = os.pathconf(path, "PC_NAME_MAX")

        inode = file.inode_id(path)
        path = self._relative_path(path)
        self._key = expected_key = VaultFileKey(
            path, inode, max_file_name_length)

        # Check for corresponding keys in the vault, automatically
        # update if the branch or path differ in that alternate and log
        already_found = False
        for check in Branch:
            # NOTE The alternate key could be the expected key; we don't
            # bother checking for that, because it's effectively a noop
            if alternate_key := self._preexisting(check, expected_key):
                if already_found:
                    raise VaultExc.VaultCorruption(
                        f"The vault in {vault.root} contains duplicates of {path} in the {already_found} branch")
                already_found = check

                self._key = alternate_key

                if check != branch:
                    # Branch differs from expectation
                    log.info(
                        f"{path} was found in the {check} branch, rather than {branch}")
                    self.branch = check

                if alternate_key.source != path:
                    # Path differs from expectation
                    # (i.e., source was moved or renamed)
                    log.info(
                        f"{path} was found in the vault as {alternate_key.source}")

        # If a key already exists in the vault, then it must have:
        # * At least two hardlinks, when in the Keep or Archive branch
        # * Exactly one hardlink, when in the Staged branch
        # * Exactly one hardlink, when in the Limbo branch

        if self.exists:
            staged = self.branch == Branch.Staged
            limboed = self.branch == Branch.Limbo
            single_hardlink = file.hardlinks(self.path) == 1

            if not staged and not limboed and single_hardlink:
                # NOTE This is not physically possible
                raise VaultExc.VaultCorruption(
                    f"The vault in {vault.root} contains {self.source}, but this no longer exists outside the vault")

            if limboed and not single_hardlink:
                raise VaultExc.VaultCorruption(
                    f"{self.source} is soft deleted in the vault in {vault.root}, but also exists outside the vault")

    def _relative_path(self, path: T.Path) -> T.Path:
        """
        Return the specified path relative to the vault's root
        directory. If the path is outside the root, then raise an
        IncorrectVault exception; if that path is physically within the
        vault, then raise a PhysicalVaultFile exception.

        @param   path  Path
        @return  Path relative to vault root
        """
        path = path.resolve()
        root = self.vault.root
        vault = self.vault.location

        try:
            _ = path.relative_to(vault)
            raise VaultExc.PhysicalVaultFile(
                f"{path} is physically contained in the vault in {root}")
        except ValueError:
            pass

        try:
            return path.relative_to(root)
        except ValueError:
            raise VaultExc.IncorrectVault(
                f"{path} does not belong to the vault in {root}")

    def _preexisting(self, branch: Branch, key: VaultFileKey) -> T.Optional[VaultFileKey]:
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
            alt_suffix, *others = (
                T.Path(dirname, f) for dirname, _, subfiles in os.walk(search_base)
                for f in subfiles if fnmatch.fnmatch(T.Path(dirname, f), key_glob)
            )
        except ValueError:
            # Alternate not found
            return None

        if len(others) != 0:
            # If the glob finds multiple matches, that's bad!
            raise VaultExc.VaultCorruption(
                f"The vault in {self.vault.root} contains duplicates of {key.path} in the {branch} branch")

        alternate = T.Path(alt_suffix)
        if key_base is not None:
            alternate = key_base / alternate

        # The VFK must be relative to the branch
        return VaultFileKey.Reconstruct(alternate.relative_to(branch_base))

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
        # * The file isn't owned by the root user
        # * Current user is the owner or in the file's group
        log = self.vault.log
        source = self.source

        if not file.is_regular(source):
            log.info(f"{source} is not a regular file")
            return False

        source_mode = source.stat().st_mode
        ugrw = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP
        if source_mode & ugrw != ugrw:
            log.info(
                f"{source} is not read-writable by both its owner and group")
            return False

        user_perms = (source_mode & stat.S_IRWXU) >> 3
        group_perms = source_mode & stat.S_IRWXG
        if user_perms != group_perms:
            log.info(
                f"The owner and group permissions do not match for {source}")
            return False

        parent_mode = source.parent.stat().st_mode
        ugwx = stat.S_IWUSR | stat.S_IXUSR | stat.S_IWGRP | stat.S_IXGRP
        if parent_mode & ugwx != ugwx:
            log.info(
                f"The parent directory of {source} is not writable or executable for both its owner and group")
            return False

        if source.stat().st_uid == 0:
            # Theoretically, the only user with higher priority
            # than any user using this (including the batch process
            # user) will be the root user. We can't have this - the
            # batch process user needs full control over all files
            log.info(f"{source} is owned by the root user")
            return False

        if os.getuid() != source.stat().st_uid and source.stat().st_gid not in os.getgroups():
            log.info(f"The user isn't the owner or in the group for {source}")
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
            log.info(
                f"The current user is not the owner of {source} nor a group owner")
            return False

        return self.can_add
