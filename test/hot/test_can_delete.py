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
from random import choice, random

from core import file, time, typing as T
from hot import ch12, an12, gn5, pa11


class _DummyFile(file.BaseFile):
    _age:T.TimeDelta

    def __init__(self, age:T.TimeDelta) -> None:
        self._age = age

    @property
    def path(self):
        raise NotImplementedError()

    @property
    def age(self):
        return self._age


_implementations = [
    ch12.can_delete,
    an12.can_delete,
    gn5.can_delete,
    pa11.can_delete
]

class TestCanDelete(unittest.TestCase):
    def test_can_delete(self):
        cases = [time.delta(days=random()) for _ in range(100)]
        threshold = choice(cases)

        for fn in _implementations:
            for case in cases:
                self.assertEqual(
                    fn(_DummyFile(case), threshold),
                    case >= threshold,
                    f"{fn.__module__}.{fn.__name__}(age={case}, threshold={threshold})")


if __name__ == "__main__":
    unittest.main()
