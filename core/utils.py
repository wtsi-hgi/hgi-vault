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

import os
from base64 import b64encode, b64decode
from contextlib import ContextDecorator
from dataclasses import dataclass
from math import ceil, log10
from functools import singledispatch

from . import typing as T


_ALT_CHARS = b"+_"  # instead of "+/"


@singledispatch
def _b64encode(data: T.Stringable) -> T.NoReturn:
    return _b64encode(str(data))


@_b64encode.register
def _(data: str) -> str:
    return _b64encode(data.encode())


@_b64encode.register
def _(data: bytes) -> str:
    return b64encode(data, altchars=_ALT_CHARS).decode()


@singledispatch
def _b64decode(data: T.Any) -> T.NoReturn:
    raise TypeError(f"Cannot base64 decode {type(data)} types")


@_b64decode.register
def _(data: str) -> bytes:
    return _b64decode(data.encode())


@_b64decode.register
def _(data: bytes) -> bytes:
    return b64decode(data, altchars=_ALT_CHARS)


class base64(T.SimpleNamespace):
    """ base64 wrapper that handles strings properly (imo) """
    encode = _b64encode
    decode = _b64decode


@dataclass
class umask(T.ContextManager[int], ContextDecorator):
    """ umask context manager/decorator """
    umask: int

    def __enter__(self) -> None:
        # Set the umask and preserve the displaced value
        self.umask = os.umask(self.umask)

    def __exit__(self, *exc) -> bool:
        # Reset the umask
        self.umask = os.umask(self.umask)
        return False


_SI = ["", "k",  "M",  "G",  "T",  "P"]
_IEC = ["", "Ki", "Mi", "Gi", "Ti", "Pi"]


def human_size(value: float, base: int = 1024, threshold: float = 0.8) -> str:
    """ Quick-and-dirty size quantifier """
    quantifiers = _IEC if base == 1024 else _SI
    sigfigs = ceil(log10(base * threshold))

    order = 0
    while order < len(quantifiers) - 1 and value > base * threshold:
        value /= base
        order += 1

    return f"{value:.{sigfigs}g} {quantifiers[order]}"


# NOTE This must be in descending order
_TQuant = [(60 * 60 * 24, "day"), (60 * 60, "hour"),
           (60, "minute"), (1, "second")]


def human_time(seconds: float, threshold: float = 0.8) -> str:
    """ Quick-and-dirty time quantifier """
    duration = 0.0
    quantifiers = iter(_TQuant)
    qualifier = ""

    while duration < threshold:
        try:
            divisor, unit = next(quantifiers)
        except StopIteration:
            break

        duration = seconds / divisor

    rounded = round(duration)

    if rounded > duration:
        qualifier = "nearly "

    if rounded == 0:
        # This will only happen at sub-threshold of the last unit
        qualifier = "less than "
        rounded = 1

    if rounded != 1:
        # Pluralise unit, if necessary
        unit += "s"

    return f"{qualifier}{rounded} {unit}"
