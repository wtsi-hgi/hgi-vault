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


class Level(Enum):
    """ Convenience enumeration for logging levels """
    Debug    = logging.DEBUG
    Info     = logging.INFO
    Warning  = logging.WARNING
    Error    = logging.ERROR
    Critical = logging.CRITICAL


_LOGGER = "shepherd"
_LEVEL  = Level.Debug if __debug__ else Level.Info

def _exception_handler(logger:logging.Logger) -> T.Callable:
    """
    Create an exception handler that logs uncaught exceptions (except
    keyboard interrupts) and spews the traceback to stderr (in debugging
    mode) before terminating
    """
    def _log_uncaught_exception(exc_type:T.Type[BaseException], exc_val:BaseException, traceback:TracebackType) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_val, traceback)

        else:
            logger.critical(str(exc_val) or exc_type.__name__)
            if __debug__:
                print_tb(traceback)

            sys.exit(1)

    return _log_uncaught_exception

def get_logger() -> logging.Logger:
    """ Initialise the logger and return it """
    if _LOGGER in logging.Logger.manager.loggerDict:
        return logging.getLogger(_LOGGER)

    formatter = logging.Formatter(fmt="%(asctime)s\t%(levelname)s\t%(message)s", datefmt=time.ISO8601)

    handler = logging.StreamHandler()
    handler.setLevel(_LEVEL.value)
    handler.setFormatter(formatter)

    logger = logging.getLogger(_LOGGER)
    logger.setLevel(_LEVEL.value)
    logger.addHandler(handler)

    sys.excepthook = _exception_handler(logger)

    return logger

def log(message:str, level:Level = Level.Info) -> None:
    """ Log a message at an optional level """
    logger = get_logger()
    logger.log(level.value, message)
