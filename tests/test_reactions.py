import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from telethon.tl import types
from telethon.tl.functions.messages import SendReactionRequest


from saveit.reactions import ReactionHandler


class ReactionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.rpc = AsyncMock()
        self.client = self.rpc
        self.client.get_entity = AsyncMock(return_value=types.PeerUser(20))
        self.client.get_messages = AsyncMock(return_value=SimpleNamespace(media=True))
        self.client.send_message = AsyncMock()
        self.save_media = AsyncMock()
        self.handler = ReactionHandler(self.client, 10, '🔥', self.save_media)

    def event(self, user=10, emoji='🔥'):
        return types.UpdateMessageReactions(
            peer=types.PeerUser(20), msg_id=42,
            reactions=types.MessageReactions(results=[], recent_reactions=[
                types.MessagePeerReaction(
                    peer_id=types.PeerUser(user), date=None,
                    reaction=types.ReactionEmoji(emoji),
                ),
            ]),
        )

    async def test_removes_reaction_before_fetching_media(self):
        async def fetch(*args, **kwargs):
            self.assertEqual(self.rpc.await_count, 1)
            return SimpleNamespace(media=True)

        self.client.get_messages.side_effect = fetch
        await self.handler(self.event())

        self.assertEqual(self.rpc.await_count, 1)
        request = self.rpc.await_args.args[0]
        self.assertIsInstance(request, SendReactionRequest)
        self.assertEqual(request.peer, types.PeerUser(20))
        self.assertEqual(request.msg_id, 42)
        self.assertEqual(request.reaction, [])
        self.save_media.assert_awaited_once()

    async def test_does_not_remove_other_users_reactions(self):
        await self.handler(self.event(user=30))
        self.rpc.assert_not_awaited()
        self.save_media.assert_not_awaited()

    async def test_does_not_remove_unrelated_reaction(self):
        await self.handler(self.event(emoji='👍'))
        self.rpc.assert_not_awaited()
        self.save_media.assert_not_awaited()

    async def test_wildcard_saves_any_own_emoji(self):
        self.handler.trigger = '*'
        await self.handler(self.event(emoji='👍'))
        self.save_media.assert_awaited_once()
        self.assertEqual(self.rpc.await_args.args[0].reaction, [])

    async def test_wildcard_saves_own_custom_emoji(self):
        self.handler.trigger = '*'
        event = self.event()
        event.reactions.recent_reactions[0].reaction = types.ReactionCustomEmoji(123)
        await self.handler(event)
        self.save_media.assert_awaited_once()

    async def test_wildcard_ignores_other_users_reactions(self):
        self.handler.trigger = '*'
        await self.handler(self.event(user=30, emoji='👍'))
        self.rpc.assert_not_awaited()
        self.save_media.assert_not_awaited()

    async def test_duplicate_update_does_not_repeat_removal_or_download(self):
        await self.handler(self.event())
        await self.handler(self.event())
        self.assertEqual(self.rpc.await_count, 1)
        self.save_media.assert_awaited_once()

    async def test_removal_failure_does_not_prevent_saving(self):
        self.rpc.side_effect = RuntimeError('Telegram unavailable')
        with self.assertLogs(level='WARNING'):
            await self.handler(self.event())
        self.save_media.assert_awaited_once()

    def channel_event(self, chosen_order=0, emoji='👍'):
        return types.UpdateMessageReactions(
            peer=types.PeerChannel(20), msg_id=42,
            reactions=types.MessageReactions(results=[
                types.ReactionCount(types.ReactionEmoji(emoji), count=5,
                                    chosen_order=chosen_order),
            ]),
        )

    async def test_saves_own_channel_reaction_without_recent_reactors(self):
        self.handler.trigger = '*'
        await self.handler(self.channel_event())
        self.save_media.assert_awaited_once()
        self.assertEqual(self.rpc.await_args.args[0].peer, types.PeerChannel(20))

    async def test_ignores_channel_reaction_not_chosen_by_me(self):
        self.handler.trigger = '*'
        await self.handler(self.channel_event(chosen_order=None))
        self.rpc.assert_not_awaited()
        self.save_media.assert_not_awaited()

    async def test_channel_reaction_still_respects_specific_trigger(self):
        await self.handler(self.channel_event())
        self.save_media.assert_not_awaited()

    async def test_saves_reaction_in_edited_channel_message(self):
        self.handler.trigger = '*'
        event = self.channel_event()
        message = SimpleNamespace(peer_id=event.peer, id=42, reactions=event.reactions, media=True)
        await self.handler(types.UpdateEditChannelMessage(message, pts=1, pts_count=1))
        self.save_media.assert_awaited_once()
