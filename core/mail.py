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

import io
from abc import ABCMeta, abstractmethod
from dataclasses import dataclass, field

from core import typing as T


@dataclass
class _BaseAttachment:
    """ Base class for attachments """
    filename:str
    mime_type:str
    data:T.BinaryIO = field(default_factory=io.BytesIO)


@dataclass
class _BaseMessage:
    """ Base class for messages """
    addressees:T.Collection[str]
    subject:str
    body:str
    attachments:T.Collection[_BaseAttachment] = field(default_factory=list)


class _BasePostman(metaclass=ABCMeta):
    """ Abstract base class for sending mail """
    # TODO Do we need to manage a session with a context manager?
    addresser:str

    @abstractmethod
    def send(self, message:_BaseMessage) -> None:
        """ Send the supplied e-mail message """


class base(T.SimpleNamespace):
    """ Namespace of base classes to make importing easier """
    Attachment = _BaseAttachment
    Message    = _BaseMessage
    Postman    = _BasePostman
