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

import subprocess
from subprocess import PIPE, DEVNULL

import core.persistence
from api.logging import Loggable, log
from api.persistence.models import State
from core import typing as T
from core.utils import human_size
from bin.common import config

Anything = core.persistence.Anything
Filter = core.persistence.Filter


class _StagingQueueEmpty(Exception):
    """ Raised when the staging queue is empty """

class _StagingQueueUnderThreshold(Exception):
    """ Raised when the staging queue has yet to cross its threshold size """

class _HandlerBusy(Exception):
    """ Raised when the downstream handler is busy """

class _DownstreamFull(Exception):
    """ Raised when the downstream handler reports it's out of capacity """

class _UnknownHandlerError(Exception):
    """ Raised when the downstream handler breaks apropos of nothing """


_preflight_exception = {
    1: _HandlerBusy,
    2: _DownstreamFull
}

class _Handler(Loggable):
    """ Downstream handler """
    _handler:T.Path

    def __init__(self, handler:T.Path) -> None:
        self._handler = handler.resolve()

    def preflight(self, capacity:int) -> None:
        """
        Run the handler preflight-check with the given required capacity

        @param   capacity              Required capacity (bytes)
        @raises  _HandlerBusy          Handler responds that it's busy
        @raises  _DownstreamFull       Handler responds that it lacks capacity
        @raises  _UnknownHandlerError  Handler fails unexpectedly
        """
        try:
            subprocess.run([self._handler, "ready", str(capacity)],
                           capture_output=True, check=True)

        except CalledProcessError as response:
            raise _preflight_exception.get(response.returncode, _UnknownHandlerError)()

    def consume(self, files:T.Iterator[T.Path]) -> None:
        """
        Drain the files, NULL-delimited, through the handler's stdin

        @param   files                File queue
        @raises  _UnknownHandlerError  Handler did not accept the queue
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
            raise _UnknownHandlerError()


def drain(persistence:core.persistence.base.Persistence, *, force:bool = False) -> int:
    """ Drain phase """
    handler = _Handler(config.archive.handler)
    criteria = Filter(state=State.Staged(notified=True), stakeholder=Anything)

    try:
        with persistence.files(criteria) as staging_queue:
            # NOTE The returned files will be purged on exit of this
            # context manager. An exception MUST be raised to avoid that
            # (e.g., if we need to cancel the drain, or if the
            # downstream handler fails, etc.)
            if (count := len(staging_queue)) == 0:
                raise _StagingQueueEmpty()

            if count < config.archive.threshold and not force:
                raise _StagingQueueUnderThreshold(f"Only {count} files to archive; use --force-drain to ignore the threshold")

            required_capacity = staging_queue.accumulator
            log.info(f"Checking downstream handler is ready for {human_size(required_capacity)}B...")
            handler.preflight(required_capacity)

            log.info("Handler is ready; beginning drain...")
            handler.consume(f.key for f in staging_queue)
            log.info(f"Successfully drained {count} files into the downstream handler")

    except _StagingQueueEmpty:
        log.info("Staging queue is empty")

    except _StagingQueueUnderThreshold as e:
        log.info(f"Skipping: {e}")

    except _HandlerBusy:
        log.warning("The downstream handler is busy; try again later...")

    except _DownstreamFull:
        log.error("The downstream handler is reporting it is out of capacity and cannot proceed")
        return 1

    except _UnknownHandlerError:
        log.critical("The downstream handler failed unexpectedly; please check its logs for details...")
        return 1

    return 0
