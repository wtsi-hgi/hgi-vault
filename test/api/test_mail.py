"""
Copyright (c) 2020 Genome Research Limited

Author: Piyush Ahuja <pa11@sanger.ac.uk>

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

import unittest
from unittest.mock import patch, MagicMock
from email.message import EmailMessage

from core import typing as T, idm as IdM, mail
import api
from api.config import Config
from api.mail import Postman

_EXAMPLE_CONFIG = Config(T.Path("eg/.vaultrc")).email

# New line is appended automatically by EmailMessage if the body does not contain one. 
# To make tests pass, we add it to our dummy
_DUMMY_MESSAGE = mail.base.Message("Test Subject", "Test body\n")

class _DummyUser(IdM.base.User):

    def __init__(self, uid, email):
        self._id = uid
        self._email = email


    @property
    def name(self):
        raise NotImplementedError

    @property
    def email(self):
        return self._email

_Dummy_Addressees = [_DummyUser("123", "recipient123@example.com"), _DummyUser("234", "recipient234@example.com")]


class TestMail(unittest.TestCase):
     
    @patch('api.mail.postman.smtplib.SMTP', autospec=True)
    def test_postman_without_sender(self, mocked_smtp):
        mocked_smtp_connection = MagicMock()
        mocked_smtp.return_value.__enter__.return_value = mocked_smtp_connection 
        postman = Postman(_EXAMPLE_CONFIG)
        postman.send(_DUMMY_MESSAGE, *_Dummy_Addressees)
        mocked_smtp_connection.send_message.assert_called_once()
        sent_email = mocked_smtp_connection.send_message.call_args.args[0]

        self.assertEqual(sent_email['subject'], _DUMMY_MESSAGE.subject )
        self.assertEqual(sent_email.get_content(), _DUMMY_MESSAGE.body )
        self.assertEqual(sent_email['from'], "vault@example.com" )

        recipients = ", ".join([user.email for user in _Dummy_Addressees])
        self.assertEqual(sent_email['to'], recipients )

    @patch('api.mail.postman.smtplib.SMTP', autospec=True)
    def test_postman_with_sender(self, mocked_smtp):
        mocked_smtp_connection = MagicMock()
        mocked_smtp.return_value.__enter__.return_value = mocked_smtp_connection 
       
        postman = Postman(_EXAMPLE_CONFIG)
        _Dummy_Addresser = _DummyUser("012", "sender@example.com")
        postman.send(_DUMMY_MESSAGE, *_Dummy_Addressees, addresser=_Dummy_Addresser)
        mocked_smtp_connection.send_message.assert_called_once()
        sent_email = mocked_smtp_connection.send_message.call_args.args[0]

        self.assertEqual(sent_email['subject'], _DUMMY_MESSAGE.subject )
        self.assertEqual(sent_email.get_content(), _DUMMY_MESSAGE.body )
        self.assertEqual(sent_email['from'], "sender@example.com" )

        recipients = ", ".join([user.email for user in _Dummy_Addressees])
        self.assertEqual(sent_email['to'], recipients )
       

if __name__ == "__main__":
    unittest.main()