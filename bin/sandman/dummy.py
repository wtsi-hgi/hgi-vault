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

import sys

from api.logging import log
from api.persistence import Persistence, models
from api.vault import Branch, Vault
from core import typing as T
from bin.common import config, idm


def main(argv:T.List[str] = sys.argv):
    log.info("FOR DEMONSTRATION ONLY")
    persistence = Persistence(config.persistence, idm)

    # TODO
    # * For all given vaults, move all "archived" files into the
    #   "staged" branch, record this in the DB appropriately ("staged
    #   queue") and delete the external counterpart.
    # * Drain the staged queue, no matter what size, into the archive
    #   handler, following the appropriate interface. It is then the
    #   handler's responsibility to archive and ultimately delete these
    #   files from the staging branch.


if __name__ == "__main__":
    main()
