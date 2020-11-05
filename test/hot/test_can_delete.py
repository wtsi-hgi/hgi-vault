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

import unittest
from functools import partial

from core import file, time, typing as T
from hot import ch12, pa11, gn5


class _DummyFile(file.BaseFile):
    @property
    def path(self):
        return T.Path("/foo")

    @property
    def age(self):
        return time.delta(hours=123)


_implementations = [
    ch12.can_delete
    # pa11.can_delete,
    # gn5.can_delete
]

class TestCanDelete(unittest.TestCase):
    def test_can_delete(self):
        cases = [
            (time.delta(hours=0),              True),
            (time.delta(hours=123),            True),
            (time.delta(hours=123, seconds=1), False),
            (time.delta(hours=456),            False)
        ]

        for implementation in _implementations:
            fn = partial(implementation, _DummyFile())
            for case, expected in cases:
                self.assertEqual(fn(case), expected)


if __name__ == "__main__":
    unittest.main()
