async def get_message_album(client, message):
    grouped_id = getattr(message, "grouped_id", None)
    if not grouped_id:
        return [message]

    peer = getattr(message, "peer_id", None)
    if peer is None:
        return [message]

    try:
        ids = range(max(1, message.id - 10), message.id + 11)
        messages = await client.get_messages(peer, ids=list(ids))
    except Exception:
        return [message]

    album = [
        item for item in messages
        if item and getattr(item, "grouped_id", None) == grouped_id and item.media
    ]
    return sorted(album, key=lambda item: item.id) or [message]
