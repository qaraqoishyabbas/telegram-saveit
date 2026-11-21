import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from saveit.app import run
from saveit.config import Settings
from saveit.reactions import ReactionHandler


class AppTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.client = SimpleNamespace(
            connect=AsyncMock(), disconnect=AsyncMock(), start=AsyncMock(),
            is_user_authorized=AsyncMock(return_value=True),
            get_me=AsyncMock(return_value=SimpleNamespace(id=10, username='tester')),
            add_event_handler=MagicMock(), run_until_disconnected=AsyncMock(),
        )
        self.constructor = patch('saveit.app.TelegramClient', return_value=self.client)
        self.constructor.start()
        self.addCleanup(self.constructor.stop)

    async def test_registers_handlers_and_disconnects_after_running(self):
        await run(Settings('123', 'hash'))
        reaction, command = self.client.add_event_handler.call_args_list
        self.assertIsInstance(reaction.args[0], ReactionHandler)
        self.assertEqual(reaction.args[0].user_id, 10)
        self.assertTrue(command.args[1].pattern('.saveit'))
        self.assertFalse(command.args[1].pattern('xsaveit'))
        self.client.run_until_disconnected.assert_awaited_once()
        self.client.disconnect.assert_awaited_once()

    async def test_uses_qr_for_unauthorized_account(self):
        self.client.is_user_authorized.return_value = False
        with patch('saveit.app.authorize_with_qr', new_callable=AsyncMock) as authorize:
            await run(Settings('123', 'hash', login_mode='qr'))
        authorize.assert_awaited_once_with(self.client)
        self.client.start.assert_not_awaited()

    async def test_disconnects_on_runtime_error(self):
        self.client.run_until_disconnected.side_effect = RuntimeError('disconnected')
        with self.assertRaises(RuntimeError):
            await run(Settings('123', 'hash'))
        self.client.disconnect.assert_awaited_once()
