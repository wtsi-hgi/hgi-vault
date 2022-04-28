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

import sys
import unittest
from unittest.mock import MagicMock, patch

from core import logging


_mock_logger = MagicMock()


class _DummyLogger(logging.base.LoggableMixin):
    _logger = "test"
    _level = logging.Level.Debug
    _formatter = logging.formats.default

    @property
    def logger(self):
        return _mock_logger


class TestLogger(unittest.TestCase):
    def setUp(self):
        _mock_logger.reset_mock()

    def test_interface(self):
        _DummyLogger().log("Hello")
        _mock_logger.log.assert_called_once_with(
            logging.Level.Info.value, "Hello")

    def test_debug(self):
        _DummyLogger().log.debug("Hello")
        _mock_logger.log.assert_called_once_with(
            logging.Level.Debug.value, "Hello")

    def test_info(self):
        _DummyLogger().log.info("Hello")
        _mock_logger.log.assert_called_once_with(
            logging.Level.Info.value, "Hello")

    def test_warning(self):
        _DummyLogger().log.warning("Hello")
        _mock_logger.log.assert_called_once_with(
            logging.Level.Warning.value, "Hello")

    def test_error(self):
        _DummyLogger().log.error("Hello")
        _mock_logger.log.assert_called_once_with(
            logging.Level.Error.value, "Hello")

    def test_critical(self):
        _DummyLogger().log.critical("Hello")
        _mock_logger.log.assert_called_once_with(
            logging.Level.Critical.value, "Hello")

    def test_debug(self):
        _DummyLogger().log.debug("Hello")
        _mock_logger.log.assert_called_once_with(
            logging.Level.Debug.value, "Hello")

    @patch("sys.exit")
    def test_unhandled_exception(self, mock_exit):
        logging.utils.set_exception_handler(_DummyLogger)
        sys.excepthook(Exception, Exception("Oh no!"), None)
        _mock_logger.log.assert_called_once_with(
            logging.Level.Critical.value, "Oh no!")
        mock_exit.assert_called_once_with(1)


if __name__ == "__main__":
    unittest.main()
