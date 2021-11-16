"""
Copyright (c) 2021 Genome Research Limited

Authors: 
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

from core.typing import PosixPath
import api.vault


class _MockOtherUserOwnedFile(PosixPath):
    """
    In a testing environment, we can't simulate files being owned by other
    users, as we need root permissions to change the file owner.

    Therefore, in some test cases we'll use this class which inherits
    the majority of its methods from pathlib.PosixPath, except the stat()
    method, which allows us to artificially change the owner and group
    """
    class _StatResult:
        """_StatResult allows the individual parts of a stat() call to
        be accessed, including our fake owner and group info."""
        def __init__(self, stats, id) -> None:
            self.st_gid = id
            self.st_uid = id
            self.st_mode = stats.st_mode
            self.st_ino = stats.st_ino

    def __new__(cls, _, *args, **kwargs):
        return PosixPath.__new__(_MockOtherUserOwnedFile, *args, **kwargs)

    def __init__(self, id, *_) -> None:
        self.id: int = id
        super().__init__()

    def stat(self):
        """stat() overrides the PosixPath's version, allowing
        us to return whatever stat result we want
        
        We check if the object has the `id` attribute first, because
        the PosixPath class may attempt to create more instances of
        this class, not knowing it needs a fake user/group id
        """
        if not hasattr(self, 'id'):
            self.id = super().stat().st_uid

        return self._StatResult(super().stat(), self.id)


class MockRootOwnedVaultFile(api.vault.VaultFile):
    """MockRootOwnedVaultFile extends VaultFile, overriding
    the source property, which gives a _MockOtherUserOwnedFile
    """
    @property
    def source(self):
        return _MockOtherUserOwnedFile(0, super().source) # 0 is root user UID


class MockOtherUserOwnedVaultFile(api.vault.VaultFile):
    """MockOtherUserOwnedVaultFile extends VaultFile, overriding
    the source property, which gives a _MockOtherUserOwnedFile
    """
    @property
    def source(self):
        return _MockOtherUserOwnedFile(-1, super().source) # -1 will never be current UID
