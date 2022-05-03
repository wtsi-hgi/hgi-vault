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

from pathlib import Path
from core import mail, typing as T

# If you are working with Sandman, you can save sending emails by temporarily
# replacing the postman in the sweeper with this class. It writes any "emails"
# to /tmp/mail


class MockMailer(mail.base.Postman):

    """
    Provides a class for "sending" emails
    without actually sending them
    """

    file_path: T.Path = Path("/tmp/mail")

    @property
    def addresser(self) -> str:
        return "fake-emailer@sanger.ac.uk"

    def _deliver(self, message: mail.base.Message,
                 recipients: T.Collection[str], sender: str) -> None:
        with open(self.__class__.file_path, "w") as f:
            f.write(f"Subject: {message.subject}\n")
            f.write(f"To: {', '.join(recipients)}\n")
            f.write(f"From: {sender}\n")
            f.write("\n")
            f.write(message.body)
