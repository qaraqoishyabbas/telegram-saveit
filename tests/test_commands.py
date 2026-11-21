import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from saveit.commands import download_by_command


class CommandTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.status = SimpleNamespace(delete=AsyncMock())
        self.message = SimpleNamespace(media=True)
        self.event = SimpleNamespace(
            sender_id=10, reply_to_msg_id=42,
            client=SimpleNamespace(send_message=AsyncMock(return_value=self.status)),
            get_reply_message=AsyncMock(return_value=self.message), reply=AsyncMock(),
        )
        self.save = AsyncMock()

    async def test_saves_replied_message_for_owner(self):
        await download_by_command(10, self.save, self.event)
        self.save.assert_awaited_once_with(self.message, self.status)

    async def test_ignores_other_users(self):
        await download_by_command(30, self.save, self.event)
        self.event.client.send_message.assert_not_awaited()
        self.save.assert_not_awaited()

    async def test_command_without_reply_removes_status(self):
        self.event.reply_to_msg_id = None
        await download_by_command(10, self.save, self.event)
        self.status.delete.assert_awaited_once()
        self.event.reply.assert_awaited_once()
        self.save.assert_not_awaited()
