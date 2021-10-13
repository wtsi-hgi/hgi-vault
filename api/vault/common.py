"""
Copyright (c) 2020, 2021 Genome Research Limited

Authors:
* Christopher Harrison <ch12@sanger.ac.uk>
* Piyush Ahuja <pa11@sanger.ac.uk>

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

from abc import abstractmethod

import core.vault
from core import logging, typing as T


class Branch(core.vault.base.Branch):
    """ HGI vault branches """
    Keep    = T.Path("keep")
    Archive = T.Path("archive")
    Staged  = T.Path(".staged")
    Limbo   = T.Path(".limbo")
    Stash   = T.Path(".stash")


class BaseHGIVault(core.vault.base.Vault, logging.base.LoggableMixin):
    """ Abstract base class for HGI's vault implementation """
    # NOTE This isn't strictly necessary and may be seen as an
    # abstraction too far, but is here to allow us to split up the vault
    # implementation module without Python failing on circular
    # dependencies

    _branch_enum = Branch
    _vault       = T.Path(".vault")

    # Class-level logging configuration
    _level     = logging.levels.default
    _formatter = logging.formats.with_username

    @property
    @abstractmethod
    def group(self) -> int:
        """ Return the group ID of the vault location """

    @property
    @abstractmethod
    def owners(self) -> T.Iterator[int]:
        """ Return an iterator of group owners' user IDs """
