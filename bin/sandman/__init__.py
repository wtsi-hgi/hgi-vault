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

from api.config import Executable
from api.logging import log
from api.persistence import Persistence
from bin.common import generate_config
from core import typing as T
from . import usage
from .walk import InvalidVaultBases, FilesystemWalker, mpistatWalker
from .sweep import Sweeper
from .drain import drain

config, idm = generate_config(Executable.SANDMAN)


def main(argv: T.List[str] = sys.argv) -> None:
    args = usage.parse_args(argv[1:])

    log.info("Enter Sandman")

    # Cheery thoughts
    if args.weaponise:
        log.warning("Weaponised: Now I am become Death, "
                    "the destroyer of worlds")
    else:
        log.info("Dry Run: The filesystem will not be affected "
                 "and the drain phase will not run")

    persistence = Persistence(config.persistence, idm)

    # Sweep Phase
    log.info("Starting the sweep phase")

    try:
        if args.stats is not None:
            log.info(f"Walking mpistat output from {args.stats}")
            log.warning("mpistat data may not be up to date")
            walker = mpistatWalker(args.stats, *args.vaults)

        else:
            log.info("Walking the filesystem directly")
            log.warning("This is an expensive operation")
            walker = FilesystemWalker(*args.vaults)

    except InvalidVaultBases as e:
        # Safety checks failed on input Vault paths
        log.critical(e)
        sys.exit(1)

    Sweeper(walker, persistence, args.weaponise)

    # Drain Phase
    if args.weaponise:
        log.info("Starting the drain phase")
        if (exit_code := drain(persistence, force=args.force_drain)) != 0:
            sys.exit(exit_code)

    log.info("Off to Never, Neverland")
