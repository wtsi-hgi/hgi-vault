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


from hot.combinator import agreed, exception


_noop = lambda _: None

def _square(x):
    return x * x

def _another_square(x):
    return x ** 2

def _broken_square(x):
    return x

def _really_broken(x):
    raise Exception("Oh the humanity!")


class TestCombinator(unittest.TestCase):
    def test_quorum(self):
        self.assertRaises(exception.CorruptQuorum, agreed, quorum=1)
        self.assertRaises(exception.QuorumTooFew, agreed, _noop)
        self.assertRaises(exception.CorruptQuorum, agreed, _noop, _noop, _noop)

    def test_consensus(self):
        square = agreed(_square, _another_square, _broken_square)
        self.assertEqual(square(1), 1)
        self.assertRaises(exception.NoConsensusReached, square, 2)

        good_square = agreed(_square, _another_square, quorum=2)
        self.assertEqual(good_square(2), 4)

        head_raise = agreed(_really_broken, _square, _noop)
        self.assertRaises(exception.NoConsensusReached, head_raise, 1)

        tail_raise = agreed(_square, _really_broken, _noop)
        self.assertRaises(exception.NoConsensusReached, tail_raise, 1)


if __name__ == "__main__":
    unittest.main()
