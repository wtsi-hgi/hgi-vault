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

import os
import smtplib
from email.message import EmailMessage

from core import config, mail, typing as T


# Get SMTP timeout from environment, if available
_SMTP_TIMEOUT = int(os.getenv("SMTP_TIMEOUT", "1"))


class Postman(mail.base.Postman):
    """ MUA implementation """
    _config: config.base.Config
    _smtp: T.Type[smtplib.SMTP]

    def __init__(self, config: config.base.Config) -> None:
        self._config = config
        self._smtp = smtplib.SMTP_SSL if config.smtp.tls else smtplib.SMTP

    @property
    def addresser(self) -> str:
        return self._config.sender

    def _deliver(self, message: mail.base.Message, recipients: T.Collection[str], sender: str) -> None:
        config = self._config

        msg = EmailMessage()
        msg.set_content(message.body)

        msg["Subject"] = message.subject
        msg["To"] = ", ".join(recipients)
        msg["From"] = sender

        # Add attachments
        for attachment in message.attachments:
            maintype, subtype = attachment.mime_type.split("/", 1)
            msg.add_attachment(attachment.data.read(),
                               maintype=maintype,
                               subtype=subtype,
                               filename=attachment.filename)

        try:
            with self._smtp(host=config.smtp.host, port=config.smtp.port, timeout=_SMTP_TIMEOUT) as postman:
                # Each message gets its own connection
                postman.send_message(msg)

        except smtplib.SMTPException as e:
            raise mail.exception.EMailFailure(f"Could not send e-mail: {e}")
