"""
Copyright (c) 2019, 2020 Genome Research Limited

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

from sys import version_info

# Make Python's type definitions available
from numbers import *
from pathlib import *
from types import *
from typing import *

# NOTE From Python 3.8, the below submodules have been removed and their
# contents bundled up into the root typing module
# FIXME Propose requirement of at least Python 3.8?
if version_info < (3, 8):
    from typing.io import *
    from typing.re import *

from .time import datetime as DateTime, \
                  timedelta as TimeDelta
