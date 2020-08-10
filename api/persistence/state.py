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

from core import persistence, time, typing as T


class Deleted(persistence.base.State):
    """ File deleted """

class Staged(persistence.base.State):
    """ File staged """

@dataclass(init=False)
class Warned(persistence.base.State):
    """ File warned for deletion """
    checkpoints:T.List[time.delta]

    def __init__(self, *tminus:time.delta) -> None:
        assert len(tminus) > 0
        self.checkpoints = sorted(set(tminus))
