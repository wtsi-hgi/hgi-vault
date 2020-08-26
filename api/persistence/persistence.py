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

# NOTE Without the PostgreSQL rule to automatically refresh file records
# that have changed, it will need to be done manually

# NOTE If a file is deleted manually after being warned, then those
# warnings will need to be cleaned up


from core import config, idm, persistence, typing as T
from . import models
from .postgres import PostgreSQL


_StateT = T.Union[models.Deleted, models.Staged, models.Warned]
_FileCollectionT = T.Union[models.UserFileCollection, models.StagedQueueFileCollection]

class Persistence(persistence.base.Persistence):
    """ PostgreSQL-backed persistence implementation """
    _pg:PostgreSQL
    _idm:idm.base.IdentityManager

    def __init__(self, config:config.base.Config, idm:idm.base.IdentityManager) -> None:
        self._pg = PostgreSQL(host     = config.postgres.host,
                              port     = config.postgres.port,
                              database = config.database,
                              user     = config.user,
                              password = config.password)
        self._idm = idm

    def persist(self, file:models.File, state:_StateT) -> None:
        raise NotImplementedError

    @property
    def stakeholders(self) -> T.Iterator[idm.base.User]:
        raise NotImplementedError

    def files(self, criteria:persistence.Filter) -> _FileCollectionT:
        raise NotImplementedError

    def clean(self, criteria:persistence.Filter) -> None:
        raise NotImplementedError
