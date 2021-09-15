"""
Copyright (c) 2020, 2021 Genome Research Limited

Authors: 
    * Christopher Harrison <ch12@sanger.ac.uk>
    * Michael Grace <mg38@sanger.ac.uk>

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

import os
import stat
from functools import cached_property

from core import file, typing as T
from core.idm import base as IdM, exception as IdMExc
from core.utils import umask
from core.vault import exception as VaultExc
from .common import Branch, BaseHGIVault
from .file import VaultFile
from .key import VaultFileKey


# Vault permissions: ug+rwx, g+s (i.e., 02770)
_PERMS = stat.S_ISGID | stat.S_IRWXU | stat.S_IRWXG
_UMASK = stat.S_IRWXO

class Vault(BaseHGIVault):
    """ HGI vault implementation """
    _file_type = VaultFile

    # Injected dependencies
    _idm:IdM.IdentityManager

    def __init__(self, relative_to:T.Path, *, idm:IdM.IdentityManager, autocreate:bool = True) -> None:
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
                    raise VaultExc.NoSuchVault(f"No vault contained in {root}")

                # Create vault, if it doesn't already exist
                try:
                    self.location.mkdir(_PERMS)

                    # Make sure the ownership and permissions on the
                    # vault directory are correct...or it won't work!
                    os.chown(self.location, uid=-1, gid=self.group)
                    self.location.chmod(_PERMS)  # See Python issue 41419

                    self.log.info(f"Vault created in {root}")
                except FileExistsError:
                    raise VaultExc.VaultConflict(f"Cannot create a vault in {root}; user file already exists")

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
                        raise VaultExc.VaultConflict(f"Cannot create a {branch} branch in the vault in {root}; user file already exists")

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
        return self.root.stat().st_gid

    @cached_property
    def owners(self) -> T.Iterator[int]:
        if (group := self._idm.group(gid=self.group)) is None:
            raise IdMExc.NoSuchIdentity(f"No group found with ID {self.group}")

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
                file.delete(to_add.path)
                to_add = self.add(branch, path)

            else:
                log.info(f"{path} is already in the {branch} branch of the vault in {self.root}")

        else:
            # File is not in the vault
            if not to_add.can_add:
                raise VaultExc.PermissionDenied(f"Cannot add {path} to the vault in {self.root}")

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
            raise VaultExc.PermissionDenied(f"Cannot remove {path} from the vault in {self.root}")

        if to_remove.exists:
            # NOTE to_remove.branch and to_remove.source might not match
            # branch and path, respectively
            file.delete(to_remove.path)
            log.info(f"{to_remove.source} has been removed from the {to_remove.branch} branch of the vault in {self.root}")

        else:
            log.info(f"{to_remove.source} is not in the vault in {self.root}")

    def list(self, branch:Branch) -> T.Iterator[T.Tuple[T.Path, T.Path]]:
        # NOTE The order in which the listing is generated is
        # unspecified (I suspect it will be by inode ID); it is up to
        # downstream to modify this, as required
        bpath = self.location / branch

        return (
            (self.root / VaultFileKey.Reconstruct(T.Path(dirname, file).relative_to(bpath)).source,
            T.Path(dirname, file))
            for dirname, _, files in os.walk(bpath)
            for file in files
        )
