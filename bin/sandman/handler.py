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

# FIXME This was put together quickly for demonstration purposes

import subprocess
from subprocess import PIPE, DEVNULL

from api.logging import Loggable
from core import typing as T


class HandlerBusy(Exception):
    """ Raised when the downstream handler is busy """

class DownstreamFull(Exception):
    """ Raised when the downstream handler reports it's out of capacity """

class UnknownHandlerError(Exception):
    """ Raised when the downstream handler breaks apropos of nothing """


_preflight_exception = {
    1: HandlerBusy,
    2: DownstreamFull
}

class Handler(Loggable):
    """ Downstream handler """
    _handler:T.Path

    def __init__(self, handler:T.Path) -> None:
        self._handler = handler.resolve()

    def preflight(self, capacity:int) -> None:
        """
        Run the handler preflight-check with the given required capacity

        @param   capacity             Required capacity (bytes)
        @raises  HandlerBusy          Handler responds that it's busy
        @raises  DownstreamFull       Handler responds that it lacks capacity
        @raises  UnknownHandlerError  Handler fails unexpectedly
        """
        try:
            subprocess.run([self._handler, "ready", str(capacity)],
                           capture_output=True, check=True)

        except CalledProcessError as response:
            raise _preflight_exception.get(response.returncode, UnknownHandlerError)()

    def consume(self, files:T.Iterator[T.Path]) -> None:
        """
        Drain the files, NULL-delimited, through the handler's stdin

        @param   files                File queue
        @raises  UnknownHandlerError  Handler did not accept the queue
        """
        handler = subprocess.Popen(self._handler, stdin=PIPE,
                                                  stdout=DEVNULL,
                                                  stderr=DEVNULL)
        for file in files:
            self.log.info(f"Draining: {file}")
            handler.stdin.write(bytes(file))
            handler.stdin.write(b"\0")

        handler.stdin.close()
        if handler.wait() != 0:
            raise UnknownHandlerError()
