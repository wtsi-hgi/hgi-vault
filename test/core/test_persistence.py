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

from core import typing as T
from core.persistence import GroupSummary


class TestGroupSummary(unittest.TestCase):
    def test_aggregation(self):
        def GS(path, count, size): return GroupSummary(
            T.Path(path), count, size)

        (_, accumulator), *cases = [
            # Test Case                       Running accumulator
            (GS("/foo/bar/quux", 1, 1), GS("/foo/bar/quux", 1, 1)),
            (GS("/foo/bar/quux/baz", 1, 2), GS("/foo/bar/quux", 2, 3)),
            (GS("/foo/bar/baz", 1, 3), GS("/foo/bar", 3, 6)),
            (GS("/foo/bar", 1, 4), GS("/foo/bar", 4, 10)),
            (GS("/xyzzy", 1, 5), GS("/", 5, 15))
        ]

        for this, check in cases:
            accumulator += this
            self.assertEqual(accumulator, check)


if __name__ == "__main__":
    unittest.main()
