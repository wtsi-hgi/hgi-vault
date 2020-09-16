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

import core.vault
from api.logging import log
from api.vault import Branch, Vault
from bin.common import idm
from core import file, typing as T
from . import usage


def _create_vault(relative_to:T.Path) -> Vault:
    # Defensively create a vault with the common IdM
    try:
        return Vault(relative_to, idm=idm)

    except core.vault.exception.VaultConflict as e:
        # Non-managed file(s) exists where the vault should be
        log.critical(e)
        sys.exit(1)


def view(branch:Branch) -> None:
    """ List the contents of the given branch """
    vault = _create_vault(file.cwd())

    count = 0
    for path in vault.list(branch):
        print(path)
        count += 1

    log.info(f"{branch} branch of the vault in {vault.root} contains {count} files")


def add(branch:Branch, files:T.List[T.Path]) -> None:
    """ Add the given files to the appropriate branch """
    for f in files:
        if not file.is_regular(f):
            # Skip non-regular files
            log.warning(f"Cannot add {f}: Doesn't exist or is not regular")
            continue

        try:
            vault = _create_vault(f)
            vault.add(branch, f)

        except core.vault.exception.VaultCorruption as e:
            # Corruption detected
            log.critical(f"Corruption detected: {e}")
            log.info("Contact HGI to resolve this corruption")

        except core.vault.exception.PermissionDenied as e:
            # User does have permission to add files
            log.error(f"Permission denied: {e}")

        except core.vault.exception.PhysicalVaultFile as e:
            # Trying to add a vault file to the vault
            log.error(f"Cannot add: {e}")


def remove(files:T.List[T.Path]) -> None:
    """ Remove the given files """
    for f in files:
        if not file.is_regular(f):
            # Skip non-regular files
            log.warning(f"Cannot remove {f}: Doesn't exist or is not regular")
            log.info("Contact HGI if a file exists in the vault, but has been deleted outside")
            continue

        vault = _create_vault(f)
        if (branch := vault.branch(f)) is not None:
            try:
                vault.remove(branch, f)

            except core.vault.exception.VaultCorruption as e:
                # Corruption detected
                log.critical(f"Corruption detected: {e}")
                log.info("Contact HGI to resolve this corruption")

            except core.vault.exception.PermissionDenied as e:
                # User doesn't have permission to remove files
                log.error(f"Permission denied: {e}")

            except core.idm.exception.NoSuchIdentity as e:
                # IdM doesn't know about the vault's group
                log.critical(f"Unknown vault group: {e}")
                log.info("Contact HGI to resolve this inconsistency")

            except core.vault.exception.PhysicalVaultFile:
                # This wouldn't make sense, so we just skip it sans log
                pass


# Mapping of actions to branch enumeration
_action_to_branch = {
    "keep":    Branch.Keep,
    "archive": Branch.Archive
}

def main(argv:T.List[str] = sys.argv):
    args = usage.parse_args(argv[1:])

    if args.action in ["keep", "archive"]:
        branch = _action_to_branch[args.action]

        if args.view:
            view(branch)
        else:
            add(branch, args.files)

    else:
        remove(args.files)


if __name__ == "__main__":
    main()
