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

import ldap3

from core import config, typing as T


class NoResultsFound(Exception):
    """ Raised on no matching search results """


_EntryT = T.Dict[str, T.List[T.Any]]

class _BaseLDAP(metaclass=ABCMeta):
    """ Quick-and-dirty abstract base class for LDAP searching """
    @abstractmethod
    def search(self, dn:str, query:str) -> T.Iterator[_EntryT]:
        """
        Search the full subtree of the given base DN with the specified
        query and return the results, or raise _NoResultsFound if no
        matches are found

        @param   dn     Base DN
        @param   query  LDAP filter
        @return  Iterator of matching entries
        """


class LDAP(_BaseLDAP):
    """ ldap3 implementation of _BaseLDAP """
    _server:ldap3.Server
    _connection:ldap3.Connection

    def __init__(self, config:config.base.Config) -> None:
        self._server = ldap3.Server(host=config.host, port=config.port)
        self._connection = ldap3.Connection(self._server, authentication=ldap3.ANONYMOUS,
                                                          read_only=True,
                                                          lazy=True)

    def search(self, dn:str, query:str) -> T.Iterator[_EntryT]:
        with self._connection as ldap:
            if not ldap.search(search_base=dn, search_filter=query, search_scope=ldap3.SUBTREE, attributes=ldap3.ALL_ATTRIBUTES):
                raise NoResultsFound()

            return (entry.entry_attributes_as_dict for entry in ldap.entries)
