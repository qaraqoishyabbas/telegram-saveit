import os
import unittest
from unittest.mock import patch

from saveit.config import Settings


class SettingsTests(unittest.TestCase):
    @patch('saveit.config.load_dotenv')
    def test_loads_credentials_and_defaults(self, load_dotenv):
        with patch.dict(os.environ, {'API_ID': '123', 'API_HASH': 'hash'}, clear=True):
            settings = Settings.from_env()
        self.assertEqual(settings.api_id, '123')
        self.assertEqual(settings.api_hash, 'hash')
        self.assertEqual(settings.download_path, '.downloads/')
        self.assertEqual(settings.reaction, '🔥')

    @patch('saveit.config.load_dotenv')
    def test_respects_account_environment(self, load_dotenv):
        environment = {
            'API_ID': '456', 'API_HASH': 'other', 'SESSION_NAME': '/session/account2',
            'DOWNLOAD_PATH': '/downloads/', 'LOGIN_MODE': 'QR',
            'HANDLER': '.download', 'REACTION': '👍',
        }
        with patch.dict(os.environ, environment, clear=True):
            settings = Settings.from_env()
        self.assertEqual(settings.session_name, '/session/account2')
        self.assertEqual(settings.download_path, '/downloads/')
        self.assertEqual(settings.login_mode, 'qr')
        self.assertEqual(settings.handler, '.download')
        self.assertEqual(settings.reaction, '👍')
