"""
Copyright (c) 2020, 2021 Genome Research Limited

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

def vault_relative_to_wd_relative(path: T.Path, working_directory: T.Path) -> T.Path:
    """
    Canonicalises a path relative to the Vault root, such that it is also relative to the working directory under the Vault root

    @param  path  location relative to vault
    @param  working_directory  working directory relative to vault

    Example: 
    f(this/is/project/this/is/file, this/is/project/this/is/working/directory) = ../../file
    """
    return T.Path(relpath(path, working_directory))



def wd_relative_to_vault_relative(path: T.Path, working_directory: T.Path, vault_root: T.Path) -> T.Path:
    """
    Takes a canonicalises Vault path, relative to some directory under the Vault root, and converts it back to a "full" Vault path
    Both the inputs need to be relativised to the same Vault root.

    @param  path  location relative to some directory under vault root
    @param  working_directory  working directory relative to vault

    Example: 
    f(../../relative/path, this/is/working/directory) = this/is/relative/path
    
    """
    joined_path = (working_directory / path) # this/is/working/directory/../../relative/path
    new_resolved_path = joined_path.resolve() # /path/to/vault/root/this/is/relative/path
    resolved_vault_root = vault_root.resolve() # /path/to/vault/root
    vault_relative_path = T.Path(relpath(new_resolved_path, resolved_vault_root)) # this/is/another/path
    return vault_relative_path


def hardlink_and_remove(full_source_path: T.Path, full_dest_path: T.Path) -> None:
    """Method that recovers a file from the Limbo branchm, with various checks that the source and desination are well behaved"""
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


