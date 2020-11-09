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



# Please implement the function "can_delete", which takes two positional
# arguments and returns a Boolean result. The arguments are:

# 1. "file", of type core.file.BaseFile
# 2. "threshold", of type core.typing.TimeDelta

# core.file.BaseFile is defined in core/file.py (L25-35)

# core.typing.TimeDelta is a wrapper for datetime.timedelta, from the
# Python standard library [1]

# The function should return truthfully if the file's age meets or exceeds
# the threshold. It should return false, otherwise. (I told you it was
# trivial!)

# [1] https://docs.python.org/3.8/library/datetime.html#datetime.timedelta

from core import file
from core import typing as T

def can_delete(file: file.BaseFile , threshold: T.TimeDelta): 
	"""The function should return truthfully if the file's age meets or exceeds
the threshold. It should return false, otherwise. """
	if file.age >= threshold:
		return True

	return False