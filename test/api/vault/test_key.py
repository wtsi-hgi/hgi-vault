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
from core.utils import base64
from .utils import VFK, VFK_k


_DUMMY = T.Path("foo/bar/quux")
_B64_DUMMY = base64.encode(_DUMMY)

_DUMMY_LONG = T.Path('this/path/is/going/to/be/much/much/much/much/much/much/'
                     'much/much/much/much/much/much/much/much/much/much/much/much/much/much/much'
                     '/much/much/much/much/much/much/much/much/much/much/much/much/much/much/'
                     'much/much/much/much/much/much/much/much/much/longer/than/two/hundred/and/'
                     'fifty/five/characters')
_B64_DUMMY_LONG = base64.encode(_DUMMY_LONG)
# Assuming test is run on a filesystem (such as Linux) where NAME_MAX = 255.
# If NAME_MAX != 255, these tests for long and really long relative paths
# would fail.
_B64_DUMMY_LONG_FIRST_PART = _B64_DUMMY_LONG[0:252]
_B64_DUMMY_LONG_SECOND_PART = _B64_DUMMY_LONG[252:]

_DUMMY_LONGEST = T.Path('this/path/is/going/to/be/much/much/much/much/much/much'
                        '/much/much/much/much/much/much/much/much/much/much/much/much/much/much/'
                        'much/much/much/much/much/much/much/much/much/much/much/much/much/much/much'
                        '/much/much/much/much/much/much/much/much/much/much/much/much/much/much/'
                        'much/much/much/much/much/much/much/much/much/much/much/much/much/much/much'
                        '/much/much/much/much/much/much/much/much/much/much/much/much/much/much/much'
                        '/much/much/much/longer/than/two/hundred/and/fifty/five/characters')

# Assuming test is run on a filesystem (such as Linux) where NAME_MAX = 255.
# If NAME_MAX != 255, these tests for long and really long relative paths
# would fa
_B64_DUMMY_LONGEST = base64.encode(_DUMMY_LONGEST)
_B64_DUMMY_LONGEST_FIRST_PART = _B64_DUMMY_LONGEST[0:252]
_B64_DUMMY_LONGEST_SECOND_PART = _B64_DUMMY_LONGEST[252:504]
_B64_DUMMY_LONGEST_THIRD_PART = _B64_DUMMY_LONGEST[504:]


class TestVaultFileKey(unittest.TestCase):
    def test_constructor(self):
        self.assertEqual(VFK(_DUMMY, 0x1).path, T.Path(f"01-{_B64_DUMMY}"))
        self.assertEqual(VFK(_DUMMY, 0x12).path, T.Path(f"12-{_B64_DUMMY}"))
        self.assertEqual(VFK(_DUMMY, 0x123).path,
                         T.Path(f"01/23-{_B64_DUMMY}"))
        self.assertEqual(VFK(_DUMMY, 0x1234).path,
                         T.Path(f"12/34-{_B64_DUMMY}"))

    def test_constructor_long(self):
        self.assertEqual(VFK(_DUMMY_LONG, 0x1).path, T.Path(
            f"01-{_B64_DUMMY_LONG_FIRST_PART}/{_B64_DUMMY_LONG_SECOND_PART}"))
        self.assertEqual(VFK(_DUMMY_LONG, 0x12).path, T.Path(
            f"12-{_B64_DUMMY_LONG_FIRST_PART}/{_B64_DUMMY_LONG_SECOND_PART}"))
        self.assertEqual(VFK(_DUMMY_LONG, 0x123).path, T.Path(
            f"01/23-{_B64_DUMMY_LONG_FIRST_PART}/{_B64_DUMMY_LONG_SECOND_PART}"))
        self.assertEqual(VFK(_DUMMY_LONG, 0x1234).path, T.Path(
            f"12/34-{_B64_DUMMY_LONG_FIRST_PART}/{_B64_DUMMY_LONG_SECOND_PART}"))

    def test_constructor_longest(self):
        self.assertEqual(VFK(_DUMMY_LONGEST, 0x1).path, T.Path(
            f"01-{_B64_DUMMY_LONGEST_FIRST_PART}/{_B64_DUMMY_LONGEST_SECOND_PART}/{_B64_DUMMY_LONGEST_THIRD_PART}"))
        self.assertEqual(VFK(_DUMMY_LONGEST, 0x12).path, T.Path(
            f"12-{_B64_DUMMY_LONGEST_FIRST_PART}/{_B64_DUMMY_LONGEST_SECOND_PART}/{_B64_DUMMY_LONGEST_THIRD_PART}"))
        self.assertEqual(VFK(_DUMMY_LONGEST, 0x123).path, T.Path(
            f"01/23-{_B64_DUMMY_LONGEST_FIRST_PART}/{_B64_DUMMY_LONGEST_SECOND_PART}/{_B64_DUMMY_LONGEST_THIRD_PART}"))
        self.assertEqual(VFK(_DUMMY_LONGEST, 0x1234).path, T.Path(
            f"12/34-{_B64_DUMMY_LONGEST_FIRST_PART}/{_B64_DUMMY_LONGEST_SECOND_PART}/{_B64_DUMMY_LONGEST_THIRD_PART}"))

    def test_reconstructor(self):
        self.assertEqual(VFK_k(T.Path(f"01-{_B64_DUMMY}")).source, _DUMMY)
        self.assertEqual(VFK_k(T.Path(f"12-{_B64_DUMMY}")).source, _DUMMY)
        self.assertEqual(VFK_k(T.Path(f"01/23-{_B64_DUMMY}")).source, _DUMMY)
        self.assertEqual(VFK_k(T.Path(f"12/34-{_B64_DUMMY}")).source, _DUMMY)

    def test_reconstructor_long(self):
        self.assertEqual(VFK_k(T.Path(
            f"01-{_B64_DUMMY_LONG_FIRST_PART}/{_B64_DUMMY_LONG_SECOND_PART}")).source, _DUMMY_LONG)
        self.assertEqual(VFK_k(T.Path(
            f"12-{_B64_DUMMY_LONG_FIRST_PART}/{_B64_DUMMY_LONG_SECOND_PART}")).source, _DUMMY_LONG)
        self.assertEqual(VFK_k(T.Path(
            f"01/23-{_B64_DUMMY_LONG_FIRST_PART}/{_B64_DUMMY_LONG_SECOND_PART}")).source, _DUMMY_LONG)
        self.assertEqual(VFK_k(T.Path(
            f"12/34-{_B64_DUMMY_LONG_FIRST_PART}/{_B64_DUMMY_LONG_SECOND_PART}")).source, _DUMMY_LONG)

    def test_reconstructor_longest(self):
        self.assertEqual(VFK_k(T.Path(
            f"01-{_B64_DUMMY_LONGEST_FIRST_PART}/{_B64_DUMMY_LONGEST_SECOND_PART}/{_B64_DUMMY_LONGEST_THIRD_PART}")).source, _DUMMY_LONGEST)
        self.assertEqual(VFK_k(T.Path(
            f"12-{_B64_DUMMY_LONGEST_FIRST_PART}/{_B64_DUMMY_LONGEST_SECOND_PART}/{_B64_DUMMY_LONGEST_THIRD_PART}")).source, _DUMMY_LONGEST)
        self.assertEqual(VFK_k(T.Path(
            f"01/23-{_B64_DUMMY_LONGEST_FIRST_PART}/{_B64_DUMMY_LONGEST_SECOND_PART}/{_B64_DUMMY_LONGEST_THIRD_PART}")).source, _DUMMY_LONGEST)
        self.assertEqual(VFK_k(T.Path(
            f"12/34-{_B64_DUMMY_LONGEST_FIRST_PART}/{_B64_DUMMY_LONGEST_SECOND_PART}/{_B64_DUMMY_LONGEST_THIRD_PART}")).source, _DUMMY_LONGEST)

    def test_resolve(self):
        self.assertEqual(VFK(_DUMMY, 0).source, _DUMMY)
        self.assertEqual(VFK_k(T.Path(f"01-{_B64_DUMMY}")).source, _DUMMY)

    def test_resolve_long(self):
        self.assertEqual(VFK(_DUMMY_LONG, 0).source, _DUMMY_LONG)
        self.assertEqual(VFK_k(T.Path(
            f"01-{_B64_DUMMY_LONG_FIRST_PART}/{_B64_DUMMY_LONG_SECOND_PART}")).source, _DUMMY_LONG)

    def test_resolve_longest(self):
        self.assertEqual(VFK(_DUMMY_LONGEST, 0).source, _DUMMY_LONGEST)
        self.assertEqual(VFK_k(T.Path(
            f"01-{_B64_DUMMY_LONGEST_FIRST_PART}/{_B64_DUMMY_LONGEST_SECOND_PART}/{_B64_DUMMY_LONGEST_THIRD_PART}")).source, _DUMMY_LONGEST)

    def test_equality(self):
        self.assertEqual(VFK(_DUMMY, 0x12), VFK_k(T.Path(f"12-{_B64_DUMMY}")))
        self.assertEqual(VFK(_DUMMY, 0x123), VFK_k(
            T.Path(f"01/23-{_B64_DUMMY}")))

    def test_equality_long(self):
        self.assertEqual(VFK(_DUMMY_LONG, 0x12), VFK_k(
            T.Path(f"12-{_B64_DUMMY_LONGEST_FIRST_PART}/{_B64_DUMMY_LONG_SECOND_PART}")))
        self.assertEqual(VFK(_DUMMY_LONG, 0x123), VFK_k(
            T.Path(f"01/23-{_B64_DUMMY_LONGEST_FIRST_PART}/{_B64_DUMMY_LONG_SECOND_PART}")))

    def test_equality_longest(self):
        self.assertEqual(VFK(_DUMMY_LONGEST, 0x12), VFK_k(T.Path(
            f"12-{_B64_DUMMY_LONGEST_FIRST_PART}/{_B64_DUMMY_LONGEST_SECOND_PART}/{_B64_DUMMY_LONGEST_THIRD_PART}")))
        self.assertEqual(VFK(_DUMMY_LONGEST, 0x123), VFK_k(T.Path(
            f"01/23-{_B64_DUMMY_LONGEST_FIRST_PART}/{_B64_DUMMY_LONGEST_SECOND_PART}/{_B64_DUMMY_LONGEST_THIRD_PART}")))


if __name__ == "__main__":
    unittest.main()
