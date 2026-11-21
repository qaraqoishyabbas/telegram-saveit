async def download_by_command(user_id, save_media, event):
    if event.sender_id != user_id:
        return

    status_message = await event.client.send_message(user_id, "Готовлю скачивание...")

    if event.reply_to_msg_id:
        message = await event.get_reply_message()
    else:
        await status_message.delete()
        return await event.reply("Reply to a message with media to save it.")

    await save_media(message, status_message)
