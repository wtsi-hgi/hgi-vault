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
from api.vault import _VaultFileKey
from .utils import VFK, VFK_k


_DUMMY = T.Path("foo/bar/quux")
_B64_DUMMY = base64.encode(_DUMMY)


class TestVaultFileKey(unittest.TestCase):
    def test_constructor(self):
        self.assertEqual(VFK(0x1,    _DUMMY).path, T.Path(f"01-{_B64_DUMMY}"))
        self.assertEqual(VFK(0x12,   _DUMMY).path, T.Path(f"12-{_B64_DUMMY}"))
        self.assertEqual(VFK(0x123,  _DUMMY).path, T.Path(f"01/23-{_B64_DUMMY}"))
        self.assertEqual(VFK(0x1234, _DUMMY).path, T.Path(f"12/34-{_B64_DUMMY}"))

    def test_reconstructor(self):
        self.assertEqual(VFK_k(T.Path(f"01-{_B64_DUMMY}")).source,    _DUMMY)
        self.assertEqual(VFK_k(T.Path(f"12-{_B64_DUMMY}")).source,    _DUMMY)
        self.assertEqual(VFK_k(T.Path(f"01/23-{_B64_DUMMY}")).source, _DUMMY)
        self.assertEqual(VFK_k(T.Path(f"12/34-{_B64_DUMMY}")).source, _DUMMY)

    def test_resolve(self):
        self.assertEqual(VFK(0, _DUMMY).source, _DUMMY)
        self.assertEqual(VFK_k(T.Path(f"01-{_B64_DUMMY}")).source, _DUMMY)

    def test_equality(self):
        self.assertEqual(VFK(0x12,  _DUMMY), VFK_k(T.Path(f"12-{_B64_DUMMY}")))
        self.assertEqual(VFK(0x123, _DUMMY), VFK_k(T.Path(f"01/23-{_B64_DUMMY}")))


if __name__ == "__main__":
    unittest.main()
