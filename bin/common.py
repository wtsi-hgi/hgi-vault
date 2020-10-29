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

import sys

from core import config, typing as T
from api.config import Config
from api.idm import IdentityManager
from api.logging import log


# Executable versioning
class version(T.SimpleNamespace):
    vault   = "0.0.3"
    sandman = "0.0.1"


# Common configuration
try:
    _cfg_path = config.utils.path("VAULTRC", T.Path("~/.vaultrc"), T.Path("/etc/vaultrc"))
    config = Config(_cfg_path)
except (config.exception.ConfigurationNotFound,
        config.exception.InvalidConfiguration) as e:
    log.critical(e)
    sys.exit(1)


# Common identity manager
# NOTE This is mutable global state...which is not cool, but "should be
# fine"™ provided we maintain serial execution
idm = IdentityManager(config.identity)
