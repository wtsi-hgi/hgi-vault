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

import os
import sys

from api.config import Config, Executable
from api.idm import IdentityManager
from api.logging import log
from core import typing as T
from core.config import exception as ConfigException
from core.config import utils


# Executable versioning
class version(T.SimpleNamespace):
    vault = "0.0.9"
    sandman = "0.0.7"


_configs: T.Dict[Executable, Config] = {}


def generate_config(
        executable: Executable) -> T.Tuple[Config, IdentityManager]:

    if (_cfg := _configs.get(executable)):
        return _cfg, IdentityManager(_cfg.identity)

    try:
        if 'unittest' in sys.modules:
            os.environ["VAULTRC"] = "eg/.vaultrc"
            os.environ["SANDMANRC"] = "eg/.sandmanrc"

        _cfg_path = utils.path("VAULTRC", T.Path(
            "~/.vaultrc"), T.Path("/etc/vaultrc"))

        # Vault Only Config
        if executable == Executable.VAULT:
            _cfg = Config(_cfg_path, executables={executable})

        # Sandman Config (includes Vault Config)
        elif executable == Executable.SANDMAN:
            _cfg = Config(
                _cfg_path,
                utils.path(
                    "SANDMANRC",
                    T.Path("~/.sandmanrc"),
                    T.Path("/etc/sandmanrc")
                ),
                executables={Executable.SANDMAN, Executable.VAULT}
            )

        else:
            raise Executable.InvalidExecutable

        _configs[executable] = _cfg
        return _cfg, IdentityManager(_cfg.identity)

    except (ConfigException.ConfigurationNotFound,
            ConfigException.InvalidConfiguration) as e:
        log.critical(e)
        sys.exit(1)
