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


        ## IMPORTANT ###########################################
        ##                                                    ##
        ##  Search for "DELETION WARNING" for sensitive code  ##
        ##                                                    ##
        ########################################################


from functools import singledispatchmethod

from api.logging import Loggable
from api.persistence import models
from api.vault import Vault, Branch
from bin.common import idm
from core import persistence, time, typing as T
from core.vault import exception as VaultExc
from . import walk


def _to_persistence(file:walk.File, vault_key:T.Optional[T.Path] = None) -> models.File:
    """
    Convert a walker file model into a persistence file model

    @param   file       Walker file
    @param   vault_key  Vault key path (if known)
    @return  Persistence file
    """
    # NOTE Do the conversion before any file operation (e.g., deletion)
    stat = file.stat
    return models.File(device = stat.st_dev,
                       inode  = stat.st_ino,
                       path   = file.path,
                       key    = vault_key,
                       mtime  = time.epoch(stat.st_mtime),
                       owner  = idm.user(uid=stat.st_uid),
                       group  = idm.group(gid=stat.st_gid),
                       size   = stat.st_size)


class Sweeper(Loggable):
    """ Encapsulation of the sweep phase """
    _walker:walk.BaseWalker
    _persistence:persistence.base.Persistence
    _dry_run:bool

    def __init__(self, walker:walk.BaseWalker, persistence:persistence.base.Persistence, dry_run:bool) -> None:
        self._walker = walker
        self._persistence = persistence
        self._dry_run = dry_run

        # Run the phase steps
        self.sweep()
        self.notify()

    def sweep(self) -> None:
        """ Walk the files and pass them off to be handled """
        for vault, file, status in self._walker.files():
            self._handler(status, vault, file)

    def notify(self) -> None:
        """ E-mail stakeholders and output summary """
        # TODO

    @property
    def Yes_I_Really_Mean_It_This_Time(self) -> bool:
        # Solemnisation :)
        return not self._dry_run

    @singledispatchmethod
    def _handler(self, status, vault:Vault, file:walk.File) -> None:
        """
        Single dispatch handler for files reported by the sweep

        @param  status  Vault status of said file
        @param  vault   The Vault that takes command over the file
        @param  file    The file and its stat information
        """
        raise NotImplementedError(f"Unknown status for {file}: {repr(status)}")

    ## File Handler Implementations ####################################

    @_handler.register
    def _(self, status:VaultExc.PhysicalVaultFile, vault, file):
        """
        Handle files that are physically contained within the vault's
        special directories
        """
        log = self.log
        log.debug(f"{file.path} is physically contained within the vault in {vault.root}")

        # We only need to check for corruptions (i.e., single hardlink)
        # of files that physically exist in the keep or archive branches
        for branch in Branch.Keep, Branch.Archive:
            bpath = vault.location / branch

            try:
                _ = file.path.relative_to(bpath)
            except ValueError:
                # File is not in the current branch
                continue

            if file.stat.st_nlink == 1:
                log.warning(f"Corruption detected: Physical vault file {file.path} does not link to any source")
                if self.Yes_I_Really_Mean_It_This_Time:
                    # DELETION WARNING
                    file.path.unlink()
                    log.info(f"Corruption corrected: {file.path} deleted")

    ####################################################################

    @_handler.register
    def _(self, status:VaultExc.VaultCorruption, vault, file):
        """
        Handle files that raise a vault corruption

        That is, tracked files that:
        1. Exist in the same/multiple branches simultaneously
        2. Are staged, but have more than 1 hardlink each
        3. Are not staged, but have only 1 hardlink each

        1. and 2. should never happen during normal operation; while 3.
        can happen, it would be impossible to detect from this direction
        and, instead, is corrected by the physical vault file handler
        (above). As such, as we cannot distinguish amongst these cases,
        all we can realistically do is log it here and move on.
        """
        self.log.error(f"Corruption detected: {status}")

    ####################################################################

    @_handler.register
    def _(self, status:None, vault, file):
        """ Handle files that are not tracked by the vault """
        # TODO

    ####################################################################

    @_handler.register
    def _(self, status:Branch, vault, file):
        """ Handle files that are tracked by the vault """
        # TODO
