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

from base64 import b64encode, b64decode
from functools import singledispatch

from core import typing as T


@singledispatch
def _b64encode(data:bytes) -> str:
    return b64encode(data).decode()

@_b64encode.register
def _(data:str) -> str:
    return b64encode(data.encode()).decode()

@singledispatch
def _b64decode(data:bytes) -> bytes:
    return b64decode(data)

@_b64decode.register
def _(data:str) -> bytes:
    return b64decode(data.encode())

class base64(T.SimpleNamespace):
    """ base64 wrapper that handles strings properly (imo) """
    encode = _b64encode
    decode = _b64decode
