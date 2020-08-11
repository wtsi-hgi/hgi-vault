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

from dataclasses import dataclass

from core import idm, persistence, typing as T


@dataclass
class File(persistence.base.File):
    """ File metadata """
    inode:int
    path:T.Path
    mtime:T.DateTime
    owner:idm.base.User
    group:idm.base.Group
    size:int


class Deleted(persistence.base.State):
    """ File deleted """

class Staged(persistence.base.State):
    """ File staged """

@dataclass
class Warned(persistence.base.State):
    """ File warned for deletion """
    tminus:T.Union[T.TimeDelta, persistence.Anything]
