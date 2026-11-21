import asyncio
import logging
import re
from functools import partial

from telethon import TelegramClient, events

from .auth import authorize_with_qr
from .commands import download_by_command
from .config import Settings
from .media import save_media
from .reactions import ReactionHandler


async def run(settings):
    client = TelegramClient(settings.session_name, settings.api_id, settings.api_hash)
    await client.connect()
    try:
        if not await client.is_user_authorized():
            if settings.login_mode == 'qr':
                await authorize_with_qr(client)
            else:
                await client.start()

        me = await client.get_me()
        save = partial(save_media, client, settings.download_path)
        client.add_event_handler(
            ReactionHandler(client, me.id, settings.reaction, save), events.Raw(),
        )
        client.add_event_handler(
            partial(download_by_command, me.id, save),
            events.NewMessage(pattern=re.escape(settings.handler)),
        )
        print(f"Bot is running as user: {me.username} (ID: {me.id})")
        await client.run_until_disconnected()
    finally:
        await client.disconnect()


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
    logging.getLogger('telethon').setLevel(logging.WARNING)
    asyncio.run(run(Settings.from_env()))
