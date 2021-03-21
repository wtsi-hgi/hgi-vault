"""
Copyright (c) 2021 Genome Research Limited

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

from os.path import relpath

from core import time,file,typing as T
from api.logging import log

def relativise(path: T.Path, working_directory: T.Path) -> T.Path:
    """
    Canonicalises a path relative to the Vault root, such that it is 
    also relative to the working directory under the Vault root

    @param  path  location relative to vault
    @param  working_directory  working directory relative to vault

    Example: 
    path: this/is/project/this/is/file
    working_directory: this/is/project/this/is/working/directory)

    output: ../../file
    """
    return T.Path(relpath(path, working_directory))


def derelativise(path: T.Path, working_directory: T.Path, vault_root: T.Path) -> T.Path:
    """
    Takes a canonicalises Vault path, relative to some directory under 
    the Vault root, and converts it back to a "full" Vault path
    
    Both the inputs need to be relativised to the same Vault root.

    @param  path  location relative to some directory under vault root
    @param  working_directory  working directory relative to vault
    @param  vault_root full path to the root of the vault

    Example: 
    path: ../../relative/path
    working_diretory: this/is/working/directory)
    vault_root: /this/is/vault/root

    output: this/is/relative/path
    """

    full_path = (vault_root/ working_directory / path).resolve() 
    return T.Path(relpath(full_path, vault_root))

  
   


def hardlink_and_remove(full_source_path: T.Path, full_dest_path: T.Path) -> None:
    """
    Method that recovers a file from the Limbo branchm, with various 
    checks that the source and desination are well behaved
    """
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
