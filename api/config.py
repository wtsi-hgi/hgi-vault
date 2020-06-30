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

from core import config


class DummyConfig(config.base.Config):
    @staticmethod
    def build(source):
        return {
            "identity": {
                "ldap": {
                    "host": "ldap.example.com",
                    "port": 389},
                "users": {
                    "attr": "uid",
                    "dn":   "ou=users,dc=example,dc=com"},
                "groups": {
                    "attr": "cn",
                    "dn":   "ou=groups,dc=example,dc=com"}},

            "persistence": {
                "postgres": {
                    "host": "postgres.example.com",
                    "port": 5432},
                "database": "sandman",
                "user":     "a_db_user",
                "password": "abc123"},

            "email": {
                "smtp": {
                    "host": "mail.example.com",
                    "port": 25},
                "sender": "vault@example.com"},

            "deletion": {
                "threshold": 90,
                "warnings": [240, 72, 24]},

            "archive": {
                "threshold": 1000,
                "handler": "/path/to/executable"}}

    @property
    def is_valid(self):
        return True
