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

from api.logging import Loggable
from api.persistence import models
from core import typing as T


class HandlerBusy(Exception):
    """ Raised when the downstream handler is busy """

class DownstreamFull(Exception):
    """ Raised when the downstream handler reports it's out of capacity """

class DrainageFailure(Exception):
    """ Raised when the downstream handler fails to consume to staging queue """


class Handler(Loggable):
    _handler:T.Path

    def __init__(self, handler:T.Path) -> None:
        self._handler = handler

    def preflight(self, capacity:int) -> None:
        """
        Run the handler preflight-check with the given required capacity

        @param   capacity        Required capacity (bytes)
        @raises  HandlerBusy     Handler responds that it's busy
        @raises  DownstreamFull  Handler responds that it lacks capacity
        """
        # TODO

    def consume(self, queue:models.FileCollection.StagedQueue) -> None:
        """
        @param   queue            Staging queue
        @raises  DrainageFailure  Handler did not accept the queue
        """
        # TODO
