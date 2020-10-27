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

from functools import singledispatchmethod

from api.logging import Loggable
from api.vault import Vault, Branch
from core.vault import exception as VaultExc
from . import walk


class Sweeper(Loggable):
    """ Encapsulation of the sweep phase """
    _walker:walk.BaseWalker
    _dry_run:bool

    def __init__(self, walker:walk.BaseWalker, dry_run:bool) -> None:
        self._walker = walker
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
        # TODO

    ####################################################################

    @_handler.register
    def _(self, status:VaultExc.VaultCorruption, vault, file):
        """ Handle files that raise a vault corruption """
        # TODO

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
