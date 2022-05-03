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

from enum import Enum
import os
import sys

import core.vault

from api.logging import log
from api.vault import Branch, Vault
from api.vault.key import VaultFileKey
from bin.common import idm, config
from core import file, time, typing as T

from . import usage
from .recover import move_with_path_safety_checks, relativise, derelativise, exception as RecoverExc


def _create_vault(relative_to: T.Path) -> Vault:
    # Defensively create a vault with the common IdM
    try:
        return Vault(relative_to, idm=idm)

    except core.vault.exception.VaultConflict as e:
        # Non-managed file(s) exists where the vault should be
        log.critical(e)
        sys.exit(1)


class ViewContext(Enum):
    All = "all"
    Here = "here"
    Mine = "mine"


def view(branch: Branch, view_mode: ViewContext, absolute: bool) -> None:
    """ List the contents of the given branch

    :param branch: Which Vault branch we're going to look at
    :param view_mode:
        ViewContext.All: list all files,
        ViewContext.Here: list files in current directory,
        ViewContext.Mine: files owned by current user
    :param absolute: - Whether to view absolute paths or not
    """
    cwd = file.cwd()
    vault = _create_vault(cwd)
    count = 0
    for path, _limbo_file in vault.list(branch):
        relative_path = relativise(path, cwd)
        if view_mode == ViewContext.Here and "/" in str(relative_path):
            continue
        elif view_mode == ViewContext.Mine and path.stat().st_uid != os.getuid():
            continue

        if branch == Branch.Limbo:
            time_to_live = config.deletion.limbo - \
                (time.now() - time.epoch(_limbo_file.stat().st_mtime))
            print(
                relative_path if absolute else relative_path,
                f"{round(time_to_live/time.delta(hours=1), 1)} hours", sep="\t"
            )
        else:
            print(path if absolute else relative_path)

        count += 1
    log.info(f"""{branch} branch of the vault in {vault.root} contains {count} files
        {'in the current directory' if view_mode == ViewContext.Here
        else 'owned by the current user' if view_mode == ViewContext.Mine
        else ''}""")


def add(branch: Branch, files: T.Iterable[T.Path]) -> None:
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


def untrack(files: T.Iterable[T.Path]) -> None:
    """ Untrack the given files """
    for f in files:
        if not file.is_regular(f):
            # Skip non-regular files
            log.warning(f"Cannot untrack {f}: Doesn't exist or is not regular")
            log.info(
                "Contact HGI if a file exists in the vault, but has been deleted outside")
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


def recover(files: T.Optional[T.Iterable[T.Path]] = None) -> None:
    """
    Recover the given files from Limbo branch or Recover all files from
    the Limbo branch

    @ param list of file paths relative to the working directory
    example: ["../file1" "file1"]
    """
    cwd = file.cwd()
    vault = _create_vault(cwd)
    bpath = vault.location / Branch.Limbo

    RECOVER_ALL = files is None

    if not RECOVER_ALL:
        vault_root = vault.root
        files_to_recover = {
            vault_root / derelativise(path, cwd, vault_root): path for path in files}
    for dirname, _, files in os.walk(bpath):
        for f in files:
            limbo_relative_path = T.Path(dirname, f).relative_to(bpath)
            try:
                vfk = VaultFileKey.Reconstruct(limbo_relative_path)
            except Exception as e:
                raise core.vault.exception.VaultCorruption(
                    f"Failed to reconstruct VaultFileKey for {limbo_relative_path}")

            original_file = vault.root / vfk.source
            vfkpath = bpath / vfk.path
            if RECOVER_ALL or original_file in files_to_recover:
                try:
                    move_with_path_safety_checks(vfkpath, original_file)
                except RecoverExc.NoSourceFound as e:
                    log.error(f"Recovery source {vfkpath} does not exist: {e}")
                except RecoverExc.NoParentForDestination:
                    log.error(
                        f"Source path exists {vfkpath} but destination parent {original_file.parent} does not exist")
                except RecoverExc.DestinationAlreadyExists:
                    log.error(
                        f"Destination {original_file} already has an existing file")


# Mapping of view contexts to enumeration
_view_contexts = {
    "all": ViewContext.All,
    "here": ViewContext.Here,
    "mine": ViewContext.Mine
}


def main(argv: T.List[str] = sys.argv) -> None:
    args = usage.parse_args(argv[1:])

    # Note: Actions do not map 1:1 to branches
    # e.g. "archive" action can map to Stash or Staged branches.
    if args.action == "keep":
        if context := args.view:
            view(Branch.Keep, _view_contexts[context], args.absolute)
        else:
            if args.files:
                add(Branch.Keep, args.files)

    if args.action == "archive":
        if context := args.view:
            view(Branch.Archive, _view_contexts[context], args.absolute)
            view(Branch.Stash, _view_contexts[context], args.absolute)
        elif context := args.view_staged:
            view(Branch.Staged, _view_contexts[context], args.absolute)
        else:
            if args.stash:
                branch = Branch.Stash
            else:
                branch = Branch.Archive
            if args.files:
                add(branch, args.files)

    if args.action == "recover":
        if context := args.view:
            view(Branch.Limbo, _view_contexts[context], args.absolute)
        else:
            recover(None if args.all else args.files)

    if args.action == "untrack":
        untrack(args.files)
