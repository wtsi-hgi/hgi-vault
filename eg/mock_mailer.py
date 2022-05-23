"""
Copyright (c) 2021 Genome Research Limited

Authors:
* Michael Grace <mg38@sanger.ac.uk>

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

import gzip
import os
from dataclasses import dataclass
from math import prod
from pathlib import Path

from core import mail
from core import typing as T

# If you are working with Sandman, you can save sending emails by temporarily
# replacing the postman in the sweeper with this class. It writes any "emails"
# to /tmp/mail


@dataclass
class _MockEmail:
    subject: str
    to: T.Set[str]
    sender: str
    body: str
    attachments: T.Optional[T.Set[str]] = None

    def __hash__(self) -> int:
        _attach_hash = prod(hash(x)
                            for x in self.attachments) if self.attachments else 1
        return prod(hash(x) for x in self.to) * hash(self.body) * _attach_hash


class MockMailer(mail.base.Postman):

    """
    Provides a class for "sending" emails
    without actually sending them
    """

    file_path: T.Path = Path("/tmp/mail")
    sent_mail: T.Set[_MockEmail] = set()

    @classmethod
    def clean(cls) -> None:
        try:
            os.remove(cls.file_path)
        except FileNotFoundError:
            pass

        cls.sent_mail = set()

    @property
    def addresser(self) -> str:
        return "fake-emailer@sanger.ac.uk"

    def _deliver(self, message: mail.base.Message,
                 recipients: T.Collection[str], sender: str) -> None:

        self.__class__.sent_mail.add(_MockEmail(
            subject=message.subject,
            to=set(recipients),
            sender=sender,
            body=message.body,
            attachments=set(gzip.decompress(attachment.data.read()).decode(
                "utf-8") for attachment in message.attachments)  # NOTE: assumes it is a gzipped attachment
        ))

        with open(self.__class__.file_path, "a") as f:
            f.write(f"Subject: {message.subject}\n")
            f.write(f"To: {', '.join(recipients)}\n")
            f.write(f"From: {sender}\n")
            f.write("\n")
            f.write(message.body)
            f.write("\nAttachments:\n")
            for attachment in message.attachments:
                f.write(attachment.filename)
                # NOTE: This assumes it is a gzipped attachment
                f.write(str(gzip.decompress(attachment.data.read())))
            f.write("\n===\n")

    @classmethod
    def get_sent_mail(
            cls, subject: T.Optional[str] = None) -> T.Set[_MockEmail]:
        emails = cls.sent_mail

        if subject:
            emails = {x for x in emails if x.subject == subject}

        return emails
