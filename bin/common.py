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

from core import config, typing as T
from api.config import DummyConfig as Config
from api.idm import DummyIdentityManager as IdentityManager


# Executable versioning
class version(T.SimpleNamespace):
    vault   = "0.0.1"
    sandman = "0.0.1"


# Common configuration
_cfg_path = config.utils.path("VAULTRC", T.Path("~/.vaultrc"), T.Path("/etc/vaultrc"))
config = Config(_cfg_path)


# Common identity manager
idm = IdentityManager(config.identity)
