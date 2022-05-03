"""
Copyright (c) 2020, 2022 Genome Research Limited

Authors:
    - Christopher Harrison <ch12@sanger.ac.uk>
    - Michael Grace <mg38@sanger.ac.uk>

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

from core import idm, typing as T


class exception(T.SimpleNamespace):
    """ Namespace of exceptions to make importing easier """
    class EMailFailure(Exception):
        """ Raised when an e-mail could not be sent """


@dataclass
class _BaseAttachment:
    """ Base class for attachments """
    filename: str
    mime_type: str
    data: T.BinaryIO = field(default_factory=io.BytesIO)


@dataclass
class _BaseMessage:
    """ Base class for messages """
    subject: str
    body: str
    attachments: T.Collection[_BaseAttachment] = field(default_factory=list)


class _BasePostman(metaclass=ABCMeta):
    """ Abstract base class for sending mail """

    def __init__(self, *args, **kwargs) -> None:
        ...

    def send(self, message: _BaseMessage, *addressee: idm.base.User,
             addresser: T.Optional[idm.base.User] = None) -> None:
        """
        Send the supplied e-mail message to the appropriate recipients

        @param  message    Message
        @param  addressee  Addressee(s)
        @param  addresser  Addresser (optional)
        """
        assert len(addressee) > 0
        recipients = [user.email for user in addressee]
        sender = self.addresser if addresser is None else addresser.email

        self._deliver(message, recipients, sender)

    @property
    @abstractmethod
    def addresser(self) -> str:
        """ Get the default sender's e-mail address """

    @abstractmethod
    def _deliver(self, message: _BaseMessage,
                 recipients: T.Collection[str], sender: str) -> None:
        """ Deliver the message """


class base(T.SimpleNamespace):
    """ Namespace of base classes to make importing easier """
    Attachment = _BaseAttachment
    Message = _BaseMessage
    Postman = _BasePostman
