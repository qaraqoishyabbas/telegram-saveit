import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

from telethon.tl import types

from saveit.media import save_media


class MediaTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.client = SimpleNamespace(
            get_messages=AsyncMock(), download_media=AsyncMock(), send_file=AsyncMock(),
        )
        self.status = SimpleNamespace(edit=AsyncMock(), delete=AsyncMock())

    def message(self, message_id=42, grouped_id=None):
        return SimpleNamespace(
            id=message_id, grouped_id=grouped_id, peer_id=20,
            sender_id=10, media=SimpleNamespace(photo=True),
        )

    async def test_downloads_and_sends_original_file(self):
        message = self.message()
        self.client.download_media.return_value = '/tmp/photo.jpg'
        await save_media(self.client, self.directory.name, message, self.status)

        self.client.download_media.assert_awaited_once_with(
            message, file=self.directory.name,
        )
        self.client.send_file.assert_awaited_once_with(
            'me', '/tmp/photo.jpg', caption='Сохранено из сообщения от 10',
            force_document=True,
        )
        self.status.delete.assert_awaited_once()

    async def test_saves_entire_album_in_message_order(self):
        first, second = self.message(41, 123), self.message(42, 123)
        self.client.get_messages.return_value = [second, self.message(40, 456), first]
        self.client.download_media.side_effect = ['first.jpg', 'second.jpg']
        await save_media(self.client, self.directory.name, second, self.status)

        self.assertEqual(
            [call.args[0].id for call in self.client.download_media.await_args_list],
            [41, 42],
        )
        self.assertEqual(
            [call.args[1] for call in self.client.send_file.await_args_list],
            ['first.jpg', 'second.jpg'],
        )
        self.status.delete.assert_awaited_once()

    async def test_message_without_media_does_not_download(self):
        message = self.message()
        message.media = None
        await save_media(self.client, self.directory.name, message, self.status)
        self.client.download_media.assert_not_awaited()
        self.client.send_file.assert_not_awaited()
        self.status.delete.assert_not_awaited()

    async def test_download_error_keeps_error_status(self):
        self.client.download_media.side_effect = OSError('disk full')
        await save_media(self.client, self.directory.name, self.message(), self.status)
        self.client.send_file.assert_not_awaited()
        self.status.delete.assert_not_awaited()
        self.assertIn('disk full', self.status.edit.await_args.args[0])

    def paid_message(self, thumbs):
        message = self.message()
        message.media = types.MessageMediaPaidMedia(
            stars_amount=100,
            extended_media=[types.MessageExtendedMediaPreview(thumb=thumb) for thumb in thumbs],
        )
        return message

    async def test_saves_all_available_paid_previews_as_files(self):
        message = self.paid_message([
            types.PhotoCachedSize(type='s', w=1, h=1, bytes=b'first-preview'),
            types.PhotoCachedSize(type='s', w=1, h=1, bytes=b'second-preview'),
        ])
        await save_media(self.client, self.directory.name, message, self.status)

        calls = self.client.send_file.await_args_list
        self.assertEqual(len(calls), 2)
        self.assertEqual([Path(call.args[1]).read_bytes() for call in calls],
                         [b'first-preview', b'second-preview'])
        self.assertTrue(all('Превью платного медиа' in call.kwargs['caption'] for call in calls))
        self.client.download_media.assert_not_awaited()
        self.status.delete.assert_awaited_once()

    async def test_reconstructs_stripped_preview_as_jpeg(self):
        message = self.paid_message([
            types.PhotoStrippedSize(type='i', bytes=b'\x01\x02\x03\x11\x22'),
        ])
        await save_media(self.client, self.directory.name, message, self.status)

        self.assertEqual(self.client.send_file.await_count, 1)
        data = Path(self.client.send_file.await_args.args[1]).read_bytes()
        self.assertTrue(data.startswith(b'\xff\xd8'))
        self.assertTrue(data.endswith(b'\x11\x22\xff\xd9'))
        self.client.download_media.assert_not_awaited()

    async def test_paid_media_without_available_thumbnail_explains_result(self):
        await save_media(self.client, self.directory.name,
                         self.paid_message([None, types.PhotoSizeEmpty(type='s')]), self.status)
        self.client.send_file.assert_not_awaited()
        self.assertIn('Telegram не предоставил доступное превью', self.status.edit.await_args.args[0])
        self.status.delete.assert_not_awaited()
