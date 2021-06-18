import unittest
from unittest.mock import patch, MagicMock
from email.message import EmailMessage


from core import typing as T, idm as IdM, mail
import api
from api.config import Config

from api.mail import Postman



_EXAMPLE_CONFIG = Config(T.Path("eg/.vaultrc")).email


# New line is appended automatically by EmailMessage if the body of Message does not contain one. To make tests pass, we add it to our dymmy

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
       
     
      
if __name__ == "__main__":
    unittest.main()






