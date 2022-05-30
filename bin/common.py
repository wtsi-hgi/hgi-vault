"""
Copyright (c) 2020, 2022 Genome Research Limited

Authors:
    - Christopher Harrison <ch12@sanger.ac.uk>
    - Michael Grace <mg38@sanger.ac.uk>

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

import getpass
import os

from api.config import Config, ExecutableNamespace
from api.idm import IdentityManager
from api.logging import log
from core import typing as T
from core.config import exception as ConfigException
from core.config import utils

Executable = ExecutableNamespace.Executable


class version(T.SimpleNamespace):
    # Executable versioning
    vault = "0.0.9"
    sandman = "0.0.7"


_configs: T.Dict[Executable, Config] = {}


# this is used when SANDMAN_FARM_TEST is set to 1
# so developers can use custom databases
# developers using their own postgres versions, or travis,
# can use the eg/.sandmanrc file values
_HGI_FARM_SANDMAN_CONFIG_LOCATION = "/software/hgi/installs/vault/etc"
_SANDMAN_ENV_CONFIG_LOC = T.Path(
    f"{_HGI_FARM_SANDMAN_CONFIG_LOCATION}/sandmanrc.{getpass.getuser()}" 
    if os.getenv("SANDMAN_FARM_TEST") == "1" 
    else os.environ["SANDMANRC"]
)

def clear_config_cache():
    global _configs
    _configs = {}


def generate_config(
        executable: Executable) -> T.Tuple[Config, IdentityManager]:

    if (_cfg := _configs.get(executable)):
        return _cfg, IdentityManager(_cfg.identity)

    try:
        _cfg_path = utils.envpath("VAULTRC", T.Path(
            "~/.vaultrc"), T.Path("/etc/vaultrc"))

        # Vault Only Config
        if executable == Executable.VAULT:
            _cfg = Config(_cfg_path, executables={executable})

        # Sandman Config (includes Vault Config)
        elif executable == Executable.SANDMAN:
            _cfg = Config(
                _cfg_path,
                utils.path(
                    _SANDMAN_ENV_CONFIG_LOC,
                    T.Path("~/.sandmanrc"),
                    T.Path("/etc/sandmanrc")
                ),
                executables={Executable.SANDMAN, Executable.VAULT}
            )

        else:
            raise ExecutableNamespace.InvalidExecutable

        _configs[executable] = _cfg
        return _cfg, IdentityManager(_cfg.identity)

    except (ConfigException.ConfigurationNotFound,
            ConfigException.InvalidConfiguration) as e:
        log.critical(e)
        sys.exit(1)
