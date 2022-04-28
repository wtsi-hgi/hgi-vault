"""
Copyright (c) 2020, 2021 Genome Research Limited

Authors: 
    * Christopher Harrison <ch12@sanger.ac.uk>
    * Michael Grace <mg38@sanger.ac.uk>

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

from __future__ import annotations

import os
from functools import cached_property

from core import file, typing as T
from core.utils import base64


_PrefixSuffixT = T.Tuple[T.Optional[T.Path], str]
_default_max_name_length: int = os.pathconf(".", "PC_NAME_MAX")


class VaultFileKey(os.PathLike):
    """ HGI vault file key properties """
    # NOTE This is implemented in a separate class to keep that part of
    # the logic outside VaultFile and to decouple it from the filesystem
    _delimiter: T.ClassVar[str] = "-"

    _prefix: T.Optional[T.Path]  # inode prefix path, without the LSB
    _suffix: str                 # LSB and encoded basename suffix name

    def __init__(self, path: T.Path, inode: T.Optional[int] = None, max_file_name_length: int = _default_max_name_length) -> None:
        """
        Construct the key from a path and (optional) inode

        @param   path           Path to construct from
        @param   inode          inode ID to construct from (defaults to inode
                                    of path)
        @param   max_file_name  The maximum length of a filename. Defaults to
                                    current directory, however can be passed
                                    in for each path being added to the Vault
        """
        # Use the path's inode, if one is not explicitly provided
        if inode is None:
            inode = file.inode_id(path)

        # The byte-padded hexadecimal representation of the inode ID
        if len(inode_hex := f"{inode:x}") % 2:
            inode_hex = f"0{inode_hex}"

        # Chunk the inode ID into 8-bit segments
        chunks = [inode_hex[i:i+2] for i in range(0, len(inode_hex), 2)]

        # inode ID, without the least significant byte, if it exists
        self._prefix = None
        if len(chunks) > 1:
            self._prefix = T.Path(*chunks[:-1])

        # inode ID LSB, delimiter, and the base64 encoding of the path.
        # If the relative file path is too long, we split it by max file name length
        # and save each part as a directory until we get to a final file
        encoded_path = base64.encode(path)
        max_file_name_length -= 3
        self._suffix = chunks[-1] + self._delimiter + str(
            T.Path(*[encoded_path[i:i+max_file_name_length]
                     for i in range(0, len(encoded_path), max_file_name_length)])
        )

    @classmethod
    def Reconstruct(cls, key_path: T.Path) -> VaultFileKey:
        """
        Alternative constructor: Reconstruct the key from a key path

        @param   key_path  Key path
        @return  Reconstructed VaultFileKey
        """
        path, inode = cls._decode_key(key_path)
        return cls(path, inode)

    @classmethod
    def _decode_key(cls, key_path: T.Path) -> T.Tuple[T.Path, int]:
        """ Decode a key path into its original path and inode ID """
        inode_hex, path_b64 = "".join(key_path.parts).split(cls._delimiter)
        return T.Path(base64.decode(path_b64).decode()), int(inode_hex, 16)

    def __eq__(self, rhs: VaultFileKey) -> bool:
        return self._prefix == rhs._prefix \
            and self._suffix == rhs._suffix

    def __bool__(self) -> bool:
        return True

    def __fspath__(self) -> str:
        return str(self.path)

    @cached_property
    def path(self) -> T.Path:
        return T.Path(self._suffix) if self._prefix is None \
            else T.Path(self._prefix, self._suffix)

    @cached_property
    def source(self) -> T.Path:
        """ Return the source file path """
        path, _ = self._decode_key(self.path)
        return path

    @cached_property
    def search_criteria(self) -> _PrefixSuffixT:
        """ Return the prefix and suffix glob pattern """
        lsb, _ = self._suffix.split(self._delimiter)
        return self._prefix, f"*{lsb}{self._delimiter}*"
