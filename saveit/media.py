import os
import logging
from pathlib import Path
from uuid import uuid4

from telethon import utils
from telethon.tl import types

from .albums import get_message_album
from .formatting import pluralize_files


async def save_media(client, download_path, message, status_message=None):
    if not message:
        if status_message:
            await status_message.edit("No media found in the message.")
        return

    messages = await get_message_album(client, message)
    media_messages = [item for item in messages if item and item.media]

    if not media_messages:
        if status_message:
            await status_message.edit("No media found in the message.")
        return

    media_count = len(media_messages)
    if status_message:
        if media_count == 1:
            await status_message.edit("Скачиваю 1 файл из сообщения...")
        else:
            await status_message.edit(f"Скачиваю {media_count} {pluralize_files(media_count)} из альбома...")

    if not os.path.exists(download_path):
        os.makedirs(download_path)

    file_paths = []

    try:
        for item in media_messages:
            if isinstance(item.media, types.MessageMediaPaidMedia):
                for extended in item.media.extended_media:
                    logging.info('Paid media entry: message=%s type=%s thumb=%s',
                                 item.id, type(extended).__name__,
                                 type(getattr(extended, 'thumb', None)).__name__)
                    if not isinstance(extended, types.MessageExtendedMediaPreview):
                        continue
                    thumb = extended.thumb
                    if isinstance(thumb, types.PhotoStrippedSize):
                        if len(thumb.bytes) < 3 or thumb.bytes[0] != 1:
                            continue
                        data = utils.stripped_photo_to_jpg(thumb.bytes)
                    elif isinstance(thumb, types.PhotoCachedSize):
                        data = thumb.bytes
                    else:
                        continue
                    if not data:
                        continue
                    file_path = str(Path(download_path) / f'paid_preview_{uuid4().hex}.jpg')
                    Path(file_path).write_bytes(data)
                    file_paths.append((item, file_path, True))
            elif hasattr(item.media, "document") or hasattr(item.media, "photo"):
                file_path = await client.download_media(item, file=download_path)
                if file_path:
                    file_paths.append((item, file_path, False))
    except Exception as err:
        logging.exception('Media download failed: message=%s', message.id)
        if status_message:
            await status_message.edit(f"Failed to download file: {str(err)}")
        return

    if not file_paths:
        logging.warning('No downloadable media or preview: message=%s media_type=%s',
                        message.id, type(message.media).__name__)
        if status_message:
            if any(isinstance(item.media, types.MessageMediaPaidMedia) for item in media_messages):
                await status_message.edit("Telegram не предоставил доступное превью платного медиа.")
            else:
                await status_message.edit("No supported media found in the message.")
        return

    try:
        file_count = len(file_paths)
        for index, (item, file_path, is_preview) in enumerate(file_paths, start=1):
            if is_preview:
                caption = f"Превью платного медиа от {item.sender_id} ({index}/{file_count})"
            elif file_count == 1:
                caption = f"Сохранено из сообщения от {item.sender_id}"
            else:
                caption = f"Сохранено из альбома от {item.sender_id} ({index}/{file_count})"

            await client.send_file(
                "me",
                file_path,
                caption=caption,
                force_document=True
            )
    except Exception as err:
        logging.exception('Sending saved media failed: message=%s', message.id)
        if status_message:
            await status_message.edit(f"Failed to send file to Saved Messages: {str(err)}")
        return

    if status_message:
        await status_message.delete()
    logging.info('Saved media: message=%s files=%s', message.id, len(file_paths))
