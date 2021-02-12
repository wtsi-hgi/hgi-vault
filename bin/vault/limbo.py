"""
Copyright (c) 2020 Genome Research Limited

Author: Piyush Ahuja <pa11@sanger.ac.uk>

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
from os.path import relpath
from core import time,file, typing as T
from api.vault.key import VaultFileKey
from api.logging import log

def convert_vault_rel_to_work_dir_rel(path: T.Path, relative_to: T.Path) -> T.Path:
    """
    Canonicalises a path relative to the Vault root, such that it is also relative to the working directory under the Vault root

    Example: 
    f(this/is/another/path, this/is/my/path) = ../../another/path
    """

    #Both the inputs need to be relativised to the same Vault root. 
    return T.Path(relpath(path, relative_to))



def convert_work_dir_rel_to_vault_rel(path: T.Path, relative_to: T.Path, vault_root: T.Path) -> T.Path:
    """
    Takes a canonicalises Vault path, relative to some directory under the Vault root, and converts it back to a "full" Vault path

    Example: 
    f(../../another/path, this/is/my/path) = this/is/another/path
    
    """

    #Both the inputs need to be relativised to the same Vault root.

    joined_path = (relative_to / path) # this/is/my/path/../../another/path
    new_resolved_path = joined_path.resolve() # /path/to/vault/root/this/is/another/path
    resolved_vault_path = vault_root.resolve() # /path/to/vault/root
    vault_relative_path = T.Path(relpath(new_resolved_path, resolved_vault_path)) # this/is/another/path
    return vault_relative_path


def hardlink_and_remove(full_source_path: T.Path, full_dest_path: T.Path) -> None:
    """Method that recovers a file from the .limbo branch"""
    if not full_source_path.exists():
        log.error(f"Source file {full_source_path} does not exist")
        return
    if not full_dest_path.parent.exists():
        log.error(f"Source path exists {full_source_path} but destination {full_dest_path.parent} does not seem to exist")
        return     

    full_source_path.link_to(full_dest_path)
    log.debug(f"{full_source_path} hardlinked at {full_dest_path} ")
    current_time = time.now()
    file.update_mtime(full_dest_path, current_time)
    full_source_path.unlink()
    log.debug(f"File has been removed from {full_source_path}")
    log.info(f"File has been restored at {full_dest_path}")



def find_vfpath_without_inode(path: T.Path, vault_root: T.Path, branch) -> T.Path:
    bpath = vault_root / ".vault"/ branch
    for dirname, _, files in os.walk(bpath):
        for file in files:
            vault_file_key = VaultFileKey.Reconstruct(T.Path(dirname, file).relative_to(bpath))
            original_source = vault_root / vault_file_key.source
            if original_source.resolve() == path.resolve():
                vault_file_path = vault_file_key.path
                log.info(f"Found VFK for source {path} at location {vault_file_path}")
                return (bpath / vault_file_path)


                