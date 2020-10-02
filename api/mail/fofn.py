"""
Copyright (c) 2019 Genome Research Limited

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

import io
from gzip import GzipFile

from core import mail, typing as T


class GZippedFOFN(mail.base.Attachment):
    """ Attachment representing a gzipped FOFN """
    def __init__(self, filename:str, files:T.Collection[T.Path]) -> None:
        self.filename = filename
        self.data = io.BytesIO()

        # Write gzipped data (\n-delimited paths) to buffer
        with GzipFile(fileobj=self.data, mode="wb") as gzip:
            for path in files:
                gzip.write(bytes(path))
                gzip.write(b"\n")

        # Rewind buffer
        self.data.seek(0)
