"""
Copyright (c) 2020, 2021 Genome Research Limited

Author: 
Christopher Harrison <ch12@sanger.ac.uk>
Piyush Ahuja <pa11@sanger.ac.uk>

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
    usage: T.Optional[str] = None
    args_error: T.Optional[str] = None

_actions = {
    "keep":    _ActionText("file retention operations",
                           "view files annotated for retention",
                           "%(prog)s [-h] (--view | FILE [FILE...])",
                           "one of the arguments --view or FILE is required"),

    "archive": _ActionText("file archival operations",
                           "view files annotated for archival",
                           "%(prog)s [-h] (--view | FILE [FILE...])",
                           "one of the arguments --view or FILE is required"),

    "remove":  _ActionText("remove files from their vault"),

    "recover": _ActionText("file recovery operations", 
                            "view recoverable files",
                            "%(prog)s [-h] (--view | --all | FILE [FILE...])",
                            "one of the arguments --view or --all or FILE is required")
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

    action = "keep"
    sub_parser = sub_level.add_parser(action, help= _actions[action].help)
    sub_parser.usage = _actions[action].usage
    sub_parser.add_argument(
                "--view",
                action="store_true",
                help=_actions[action].view_help)
    sub_parser.add_argument(
            "files",    
            nargs="*",
            type=T.Path,
            help=f"file to keep (at most 10)",
            metavar="FILE")


    action = "archive"
    sub_parser = sub_level.add_parser(action, help= _actions[action].help)
    sub_parser.usage = _actions[action].usage
    sub_parser.add_argument(
                "--view",
                action="store_true",
                help=_actions[action].view_help)
    sub_parser.add_argument(
            "files",    
            nargs="*",
            type=T.Path,
            help=f"file to archive (at most 10)",
            metavar="FILE")


    action = "remove"
    sub_parser = sub_level.add_parser(action, help= _actions[action].help)
    sub_parser.add_argument(
            "files",    
            nargs="+",
            type=T.Path,
            help=f"file to remove",
            metavar="FILE")


    action = "recover"
    sub_parser = sub_level.add_parser(action, help= _actions[action].help)
    sub_parser.usage = _actions[action].usage
    sub_parser.add_argument(
                "--view",
                action="store_true",
                help=_actions[action].view_help)

    sub_parser.add_argument(
                "--all",
                action="store_true",
                help="recover all recoverable files")

    sub_parser.add_argument(
            "files",    
            nargs="*",
            type=T.Path,
            help=f"file to recover",
            metavar="FILE")



    def parser(args:T.List[str]) -> argparse.Namespace:
        # Parse the given arguments and ensure mutual exclusivity
        parsed = top_level.parse_args(args)
        text = _actions[parsed.action]
        
        if parsed.action == "keep":
            if parsed.view:
                del parsed.files
            else:
                if not parsed.files:
                    action_level[parsed.action].error(_actions[parsed.action].args_error)
                elif len(parsed.files) > 10:
                    # Limit number of files to at most 10
                    action_level[parsed.action].error("too many FILEs; you may specify no more than 10")

        if parsed.action == "archive":
            if parsed.view:
                del parsed.files
            else:
                if not parsed.files:
                    action_level[parsed.action].error(_actions[parsed.action].args_error)
                elif len(parsed.files) > 10:
                    # Limit number of files to at most 10
                    action_level[parsed.action].error("too many FILEs; you may specify no more than 10")

        if parsed.action == "recover":
            if parsed.view or parsed.all:
                del parsed.files 
                if parsed.view and parsed.all:
                    action_level[parsed.action].error("cannot accept arguments --view and --all simultaenously")
            else:
                if not parsed.files:
                    action_level[parsed.action].error(_actions[parsed.action].args_error)     
           
        if parsed.action == "remove":
            pass

        if "files" in parsed:
        # Resolve all paths
            parsed.files = [path.resolve() for path in parsed.files]
        return parsed

    return parser


parse_args = _parser_factory()
