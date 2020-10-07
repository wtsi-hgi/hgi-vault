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

from core import config, mail, typing as T


class Postman(mail.base.Postman):
    """ MUA implementation """
    _config:config.base.Config

    def __init__(self, config:config.base.Config) -> None:
        self._config = config

    @property
    def addresser(self) -> str:
        return self._config.sender

    def _deliver(self, message:mail.base.Message, recipients:T.Collection[str], sender:str) -> None:
        # TODO
        # * Assemble the e-mail from our abstraction
        # * Send it
        pass
