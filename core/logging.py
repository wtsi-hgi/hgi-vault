"""
Copyright (c) 2019, 2020 Genome Research Limited

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
from functools import partial
from getpass import getuser
from traceback import print_tb
from types import TracebackType

from . import typing as T, time


class Level(Enum):
    """ Convenience enumeration for logging levels """
    Debug = logging.DEBUG
    Info = logging.INFO
    Warning = logging.WARNING
    Error = logging.ERROR
    Critical = logging.CRITICAL


def _equal_stream_handlers(lhs: logging.StreamHandler,
                           rhs: logging.StreamHandler) -> bool:
    """
    Check two stream handlers (n.b., file handlers are stream handlers)
    are equal, by virtue of having the same stream name, level and
    formatter. (This approach is easier than subclassing StreamHandler
    then monkey patching FileHandler, but leaves a lot to be desired!)

    @param   lhs  Stream handler
    @param   rhs  Stream handler
    @return  Equality
    """
    return lhs.stream.name == rhs.stream.name \
        and lhs.level == rhs.level \
        and lhs.formatter == rhs.formatter


class _LoggableMixin:
    """ Base mixin class for logging interface """
    # NOTE The following can be either class or instance variables
    # NOTE _logger refers to a named logger with a set level; specifying
    # a different _level will change that value for that logger, but not
    # any handlers that have already been defined. This is a bit messy,
    # but it's to facilitate the easy definition of downstream mixins
    _logger: str
    _level: Level
    _formatter: logging.Formatter

    @property
    def logger(self) -> logging.Logger:
        # NOTE setLevel is called explicitly on each invocation to avoid
        # having downstream classes call it in their constructors
        logger = logging.getLogger(self._logger)
        logger.setLevel(self._level.value)
        return logger

    @property
    def log(self) -> object:
        """ End-user logging functions exposed as log.* """
        parent = self

        class _wrapper:
            def __call__(self, message: str,
                         level: Level = Level.Info) -> None:
                """ Log a message at an optional level """
                parent.logger.log(level.value, message)

            def debug(self, message: str) -> None:
                # Convenience alias
                self(message, Level.Debug)

            def info(self, message: str) -> None:
                # Convenience alias
                self(message, Level.Info)

            def warning(self, message: str) -> None:
                # Convenience alias
                self(message, Level.Warning)

            def error(self, message: str) -> None:
                # Convenience alias
                self(message, Level.Error)

            def critical(self, message: str) -> None:
                # Convenience alias
                self(message, Level.Critical)

            @property
            def _streams(self) -> T.Iterator[logging.StreamHandler]:
                """ Iterator of StreamHandlers on the logger """
                yield from filter(lambda h: isinstance(h, logging.StreamHandler), parent.logger.handlers)

            def _to_stream(self, handler: logging.StreamHandler,
                           formatter: T.Optional[logging.Formatter] = None, level: T.Optional[Level] = None) -> None:
                """ Add a new stream handler to the logger """
                handler.setFormatter(formatter or parent._formatter)
                handler.setLevel((level or parent._level).value)

                if not any(_equal_stream_handlers(handler, stream)
                           for stream in self._streams):
                    parent.logger.addHandler(handler)

            def to_tty(self, formatter: T.Optional[logging.Formatter]
                       = None, level: T.Optional[Level] = None) -> None:
                # Convenience alias
                self._to_stream(logging.StreamHandler(), formatter, level)

            def to_file(self, filename: T.Path,
                        formatter: T.Optional[logging.Formatter] = None, level: T.Optional[Level] = None) -> None:
                # Convenience alias
                self._to_stream(logging.FileHandler(
                    filename), formatter, level)

        return _wrapper()


def _set_exception_handler(loggable: T.Type[_LoggableMixin]) -> None:
    """
    Create an exception handler that logs uncaught exceptions (except
    keyboard interrupts) and spews the traceback to stderr (in debugging
    mode) before terminating

    @param   loggable  Loggable mixin class
    """
    def _log_uncaught_exception(
            exc_type: T.Type[Exception], exc_val: Exception, traceback: TracebackType) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_val, traceback)

        else:
            loggable().log.critical(str(exc_val) or exc_type.__name__)
            if __debug__:
                print_tb(traceback)

            sys.exit(1)

    sys.excepthook = _log_uncaught_exception


def _to_tty(loggable: T.Type[_LoggableMixin]) -> None:
    """
    Add a stream handler to the specified loggable mixin

    @param   loggable  Loggable mixin class
    """
    loggable().log.to_tty()


class base(T.SimpleNamespace):
    """ Namespace of base classes to make importing easier """
    LoggableMixin = _LoggableMixin


class utils(T.SimpleNamespace):
    """ Namespace of utilities to make importing easier """
    make_format = partial(logging.Formatter, datefmt=time.ISO8601)
    set_exception_handler = _set_exception_handler
    to_tty = _to_tty


class formats(T.SimpleNamespace):
    """ Namespace of formatters to make importing easier """
    default = utils.make_format("%(asctime)s\t%(levelname)s\t%(message)s")
    with_username = utils.make_format(
        f"%(asctime)s\t%(levelname)s\t{getuser()}\t%(message)s")


class levels(T.SimpleNamespace):
    """ Namespace of levels to make importing easier """
    default = Level.Debug if __debug__ else Level.Info
