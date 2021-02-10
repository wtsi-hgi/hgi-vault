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
from api.vault.file import hardlink_and_remove, convert_work_dir_rel_to_vault_rel, convert_vault_rel_to_work_dir_rel
from api.vault.key import VaultFileKey
from bin.common import idm
from core import file, typing as T
from . import usage
import os

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
    cwd = file.cwd()
    vault = _create_vault(cwd)
    
    count = 0
    if branch == Branch.Limbo:
        vault_root = vault._find_root()
        bpath = vault_root / ".vault"/ branch
        for dirname, _, files in os.walk(bpath):
            for f in files:
                count +=1
                full_file_path = T.Path(dirname) / T.Path(f)
                vault_relativized_work_dir = T.Path(os.path.relpath(cwd, vault_root))
                work_dir_in_vault = bpath / vault_relativized_work_dir
                relative_path = convert_vault_rel_to_work_dir_rel(full_file_path, work_dir_in_vault )
                print(relative_path)
    else:
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

def find_vfpath_without_inode(path: T.Path, vault_root: T.Path, branch) -> T.Path:
    bpath = vault_root / ".vault"/ branch
    for dirname, _, files in os.walk(bpath):
        for file in files:
            vault_file_key = VaultFileKey.Reconstruct(T.Path(dirname, file).relative_to(bpath))
            original_source = vault_root / vault_file_key.source
            if original_source.resolve() == path.resolve():
                vault_file_path = bpath/ vault_file_key.path
                log.info(f"Found VFK for source {path} at location {vault_file_path}")
                return vault_file_path

def recover(files: T.List[T.Path]) -> None:
    """Recover the given files from Limbo branch
    Command to recover some/file1 and some/path/file1:
    some/path$ vault recover ../file1 file1
    """

    cwd = file.cwd()

    for f in files:
        vault = _create_vault(f)
        vault_root = vault._find_root()
        # Converts ../file1 to .vault/limbo/enc(/some/file1)
        vault_relative_path = convert_work_dir_rel_to_vault_rel(f, cwd , vault_root)
        full_dest_path = vault_root / vault_relative_path
        full_source_path = find_vfpath_without_inode(full_dest_path, vault_root, Branch.Limbo)
        hardlink_and_remove(full_source_path, full_dest_path)


# Mapping of actions to branch enumeration
_action_to_branch = {
    "keep":    Branch.Keep,
    "archive": Branch.Archive,
    "recover": Branch.Limbo
}

def main(argv:T.List[str] = sys.argv) -> None:
    args = usage.parse_args(argv[1:])

    if args.action in ["keep", "archive", "recover"]:
        branch = _action_to_branch[args.action]

        if args.view:
            view(branch)
        else:
            add(branch, args.files)

    else:
        remove(args.files)
