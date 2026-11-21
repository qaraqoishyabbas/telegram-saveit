import logging

from telethon.tl.functions.messages import SendReactionRequest

from .reaction_utils import (
    get_peer_id,
    get_update_reaction_context,
    is_my_trigger_reaction,
)


class ReactionHandler:
    def __init__(self, client, user_id, trigger, save_media):
        self.client = client
        self.user_id = user_id
        self.trigger = trigger
        self.save_media = save_media
        self.processed_reactions = set()

    async def __call__(self, event):
        update = getattr(event, "original_update", event)
        update_name = update.__class__.__name__

        if "Reaction" not in update_name and "Reactions" not in update_name and update_name not in ("UpdateEditMessage", "UpdateEditChannelMessage"):
            return

        peer, msg_id, reactions, message = get_update_reaction_context(update)
        peer_id = get_peer_id(peer)
        logging.info('Reaction update: type=%s peer=%s message=%s candidate_count=%s',
                     update_name, peer_id, msg_id, len(reactions))

        if peer is None or msg_id is None:
            return

        if not reactions:
            return

        should_save = False

        for recent_reaction in reactions:
            sender_peer = getattr(recent_reaction, "peer_id", None)
            sender_id = get_peer_id(sender_peer)
            if is_my_trigger_reaction(recent_reaction, sender_id, self.user_id, self.trigger):
                should_save = True

        processed_key = (peer_id, msg_id, self.trigger)
        if not should_save:
            logging.info('Reaction skipped: no matching own reaction, message=%s', msg_id)
            return

        if processed_key in self.processed_reactions:
            logging.info('Reaction skipped: already processed, message=%s', msg_id)
            return

        self.processed_reactions.add(processed_key)

        try:
            await self.client(SendReactionRequest(peer=peer, msg_id=msg_id, reaction=[]))
        except Exception as err:
            logging.warning("Не удалось снять реакцию с сообщения %s: %s", msg_id, err)

        if message is None:
            try:
                entity = await self.client.get_entity(peer)
                message = await self.client.get_messages(entity, ids=msg_id)
            except Exception:
                logging.exception('Cannot fetch reacted message=%s', msg_id)
                return

        if not message:
            logging.info('Reaction skipped: message not found, message=%s', msg_id)
            return

        if not message.media:
            logging.info('Reaction skipped: message has no media, message=%s', msg_id)
            return

        logging.info('Saving reacted media: message=%s type=%s', msg_id, type(message.media).__name__)
        status_message = await self.client.send_message("me", "Готовлю скачивание...")
        await self.save_media(message, status_message)
