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

from jinja2 import Environment, FileSystemLoader

from core import typing as T, utils


def render(template: str, context: T.Any) -> str:
    """
    Render the Jinja2 template with the given context

    @param   template  Jinja2 template
    @param   context   Template context
    @return  Rendered template
    """
    # This inefficiently recompiles the template on each call...but it's
    # fast enough for it not to be a problem
    env = Environment(trim_blocks=True,
                      loader=FileSystemLoader([template.parent.absolute()]))
    env.filters["human_size"] = utils.human_size
    env.filters["human_time"] = utils.human_time

    with open(template, "r") as f:
        template_data = f.read()

    return env.from_string(template_data).render(context)
