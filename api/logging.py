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

from core.logging import base, utils, levels, formats


class Loggable(base.LoggableMixin):
    # Default/base loggable mixin
    _logger = "vault"
    _level = levels.default
    _formatter = formats.default


utils.to_tty(Loggable)
utils.set_exception_handler(Loggable)

# Convenience function for module/function-based logging
log = Loggable().log
