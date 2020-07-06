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

from api.logging import log
from api.vault import Branch, Vault
from core import file, typing as T
from . import usage
from ..common import idm


def view(branch:Branch) -> None:
    """ List the contents of the given branch """
    vault = Vault(file.cwd(), idm=idm)
    for path in vault.list(branch):
        log.info(path)


def add(branch:Branch, files:T.List[T.Path]) -> None:
    """ Add the given files to the appropriate branch """
    for f in files:
        vault = Vault(f, idm=idm)
        vault.add(branch, f)


def remove(files:T.List[T.Path]) -> None:
    """ Remove the given files """
    for f in files:
        vault = Vault(f, idm=idm)
        if (branch := vault.branch(f)) is not None:
            vault.remove(branch, f)


# Mapping of actions to branch enumeration
_action_to_branch = {
    "keep":    Branch.Keep,
    "archive": Branch.Archive
}

def main(argv:T.List[str] = sys.argv):
    args = usage.parse_args(argv[1:])

    if args.action in ["keep", "archive"]:
        branch = _action_to_branch[args.action]

        if args.view:
            view(branch)
        else:
            add(branch, args.files)

    else:
        remove(args.files)


if __name__ == "__main__":
    main()
