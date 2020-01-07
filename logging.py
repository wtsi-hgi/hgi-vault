"""
Copyright (c) 2019 Genome Research Limited

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

import logging
import sys
from enum import Enum
from traceback import print_tb
from types import TracebackType

from . import types as T, time


def _exception_handler(logger:logging.Logger) -> T.Callable:
    """
    Create an exception handler that logs uncaught exceptions (except
    keyboard interrupts) and spews the traceback to stderr (in debugging
    mode) before terminating
    """
    def _log_uncaught_exception(exc_type:T.Type[Exception], exc_val:Exception, traceback:TracebackType) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_val, traceback)

        else:
            logger.critical(str(exc_val) or exc_type.__name__)
            if __debug__:
                print_tb(traceback)

            sys.exit(1)

    return _log_uncaught_exception


class Level(Enum):
    """ Convenience enumeration for logging levels """
    Debug    = logging.DEBUG
    Info     = logging.INFO
    Warning  = logging.WARNING
    Error    = logging.ERROR
    Critical = logging.CRITICAL


class Logger:
    _logger:logging.Logger
    _level:Level
    _format:logging.Formatter

    def __init__(self, name:str, level:Level, formatter:logging.Formatter) -> None:
        self._logger = logging.getLogger(name)
        self._level  = level
        self._format = formatter

        self._logger.setLevel(level.value)
        self._add_handler(logging.NullHandler())

        sys.excepthook = _exception_handler(self._logger)

    def _add_handler(self, handler:logging.Handler) -> None:
        handler.setLevel(self._level.value)
        handler.setFormatter(self._format)
        self._logger.addHandler(handler)

    def to_tty(self) -> None:
        self._add_handler(logging.StreamHandler())

    def to_file(self, filename:T.Path) -> None:
        self._add_handler(logging.FileHandler(filename))

    def __call__(self, message:str, level:Level = Level.Info) -> None:
        """ Log a message at an optional level """
        self._logger.log(level.value, message)

    def debug(self, message:str) -> None:
        # Convenience alias
        self(message, Level.Debug)

    def info(self, message:str) -> None:
        # Convenience alias
        self(message, Level.Info)

    def warning(self, message:str) -> None:
        # Convenience alias
        self(message, Level.Warning)

    def error(self, message:str) -> None:
        # Convenience alias
        self(message, Level.Error)

    def critical(self, message:str) -> None:
        # Convenience alias
        self(message, Level.Critical)


_LOGGER = "shepherd"
_LEVEL  = Level.Debug if __debug__ else Level.Info
_FORMAT = logging.Formatter(fmt="%(asctime)s\t%(levelname)s\t%(message)s", datefmt=time.ISO8601)

log = Logger(_LOGGER, _LEVEL, _FORMAT)
