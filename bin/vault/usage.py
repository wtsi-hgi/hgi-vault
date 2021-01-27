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

import argparse
from dataclasses import dataclass

from core import typing as T
from bin.common import version


@dataclass
class _ActionText:
    help:str
    view_help:T.Optional[str] = None

_actions = {
    "keep":    _ActionText("file retention operations",
                           "view files annotated for retention"),

    "archive": _ActionText("file archival operations",
                           "view files annotated for archival"),

    "remove":  _ActionText("remove files from their vault"),

    "recover": _ActionText("file recovery from recycle bin operations", "view files currently in the recycle bin")
}

def _parser_factory():
    """ Build an argument parser meeting requirements """
    top_level = argparse.ArgumentParser("vault")
    top_level.add_argument("--version", action="version", version=f"%(prog)s {version.vault}")

    sub_level = top_level.add_subparsers(
        description="Operations on files against their respective vault",
        required=True,
        dest="action",
        metavar="ACTION")

    action_level = {}
    for action, text in _actions.items():
        action_level[action] = sub_level.add_parser(action, help=text.help)

        # We can't have a mutually exclusive group containing a --view
        # argument or at least one positional argument, so we have to
        # roll our own with a bit of downstream processing
        file_nargs = "+"
        if text.view_help is not None:
            file_nargs = "*"
            action_level[action].usage = "%(prog)s [-h] (--view | FILE [FILE...])"
            action_level[action].add_argument(
                "--view",
                action="store_true",
                help=text.view_help)

        action_level[action].add_argument(
            "files",
            nargs=file_nargs,
            type=T.Path,
            help=f"file to {action} (at most 10)",
            metavar="FILE")

    action_level["recover"].add_argument("--all", action="store_true", help="recover all files in the current recycle bin")


    def parser(args:T.List[str]) -> argparse.Namespace:
        # Parse the given arguments and ensure mutual exclusivity
        parsed = top_level.parse_args(args)

        text = _actions[parsed.action]
        if text.view_help is not None:
            if parsed.view || parsed.all:
                # Nullify file arguments if asked to view
                del parsed.files
            else:
                if not parsed.files:
                    # Must have either --view or FILEs
                    action_level[parsed.action].error("one of the arguments --view or FILE is required")

                if len(parsed.files) > 10:
                    # Limit number of files to at most 10
                    action_level[parsed.action].error("too many FILEs; you may specify no more than 10")

                # Resolve all paths
                parsed.files = [path.resolve() for path in parsed.files]

        return parsed

    return parser


parse_args = _parser_factory()
