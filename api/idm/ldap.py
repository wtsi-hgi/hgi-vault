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

from abc import ABCMeta, abstractmethod
from enum import Enum, auto

import ldap3

from core import config, typing as T


# NOTE This is a quick-and-dirty LDAP interface and implementation to
# provide the functionality we specifically need. It is not meant for
# general-purpose use.


class NoResultsFound(Exception):
    """ Raised upon no matching search results """


class Scope(Enum):
    """ LDAP search scope enumeration """
    Base     = auto()
    OneLevel = auto()
    SubTree  = auto()


_EntryT = T.Dict[str, T.List[T.Any]]

class _BaseLDAP(metaclass=ABCMeta):
    """ Quick-and-dirty abstract base class for LDAP searching """
    @abstractmethod
    def search(self, dn:str, query:str, scope:Scope = Scope.SubTree) -> T.Iterator[_EntryT]:
        """
        Search the base DN at the given scope with the specified query
        and return the results, or raise NoResultsFound if no matches
        are found

        @param   dn     Base DN
        @param   query  LDAP filter
        @param   scope  Search scope
        @return  Iterator of matching entries
        """


_scope_map = {
    Scope.Base:     ldap3.BASE,
    Scope.OneLevel: ldap3.LEVEL,
    Scope.SubTree:  ldap3.SUBTREE
}

class LDAP(_BaseLDAP):
    """ ldap3 implementation of _BaseLDAP """
    _server:ldap3.Server
    _connection:ldap3.Connection

    def __init__(self, config:config.base.Config) -> None:
        self._server = ldap3.Server(host=config.host, port=config.port)
        self._connection = ldap3.Connection(self._server, authentication=ldap3.ANONYMOUS,
                                                          read_only=True,
                                                          lazy=True)

    def search(self, dn:str, query:str, scope:Scope = Scope.SubTree) -> T.Iterator[_EntryT]:
        with self._connection as ldap:
            if not ldap.search(search_base=dn,
                               search_filter=query,
                               search_scope=_scope_map[scope],
                               attributes=ldap3.ALL_ATTRIBUTES):
                raise NoResultsFound(f"No entries found under DN {dn} matching filter {query}")

            return (entry.entry_attributes_as_dict for entry in ldap.entries)
