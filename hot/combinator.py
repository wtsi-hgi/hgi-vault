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

from core import typing as T


_QUORUM_SIZE = 3


class exception(T.SimpleNamespace):
    """ Namespace of exceptions to make importing easier """
    class NoConsensusReached(Exception):
        """ Raised when consensus is split """

    class QuorumTooFew(Exception):
        """ Raised when the quorum of functions is too few """

    class CorruptQuorum(Exception):
        """ Raised when the quorum of functions has duplicates or too small """


_ArgT = T.TypeVar("_ArgT")
_RetT = T.TypeVar("_RetT")
_HotCode = T.Callable[..., _RetT]  # FIXME Callable[_ArgT, _RetT] doesn't parse

def _run(fn:_HotCode) -> _HotCode:
    name = f"{fn.__module__}.{fn.__name__}"

    def _wrapper(*args, **kwargs) -> _RetT:
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            raise exception.NoConsensusReached(f"{name} failed with: {exc}")

    return _wrapper

def agreed(*fn:_HotCode, quorum:int = _QUORUM_SIZE) -> _HotCode:
    """
    Return a function that runs the argument functions and checks that
    they all agree, in terms of return value; otherwise, raise a
    NoConsensusReached exception

    @param   *fn     Input functions
    @param   quorum  Minimum number of expected input functions
    @return  Consensus function
    """
    if quorum < 2:
        raise exception.CorruptQuorum("The quorum must have more than one member")

    if len(fn) < quorum:
        raise exception.QuorumTooFew(f"Not enough functions to combine; expected {quorum}, got {len(fn)}")

    if len(set(fn)) < len(fn):
        raise exception.CorruptQuorum("The quorum is made up of non-unique functions")

    def _wrapper(*args, **kwargs) -> _RetT:
        head, *tail = fn
        head_id = f"{head.__module__}.{head.__name__}"

        result = _run(head)(*args, **kwargs)

        for f in tail:
            if _run(f)(*args, **kwargs) != result:
                f_id = f"{f.__module__}.{f.__name__}"
                raise exception.NoConsensusReached(f"{f_id} does not agree with {head_id}")

        return result

    return _wrapper
