from telethon import utils


def get_peer_id(peer):
    if peer is None:
        return "unknown"

    try:
        return utils.get_peer_id(peer)
    except Exception:
        return "unknown"


def get_reaction_value(reaction):
    if reaction is None:
        return "unknown"

    emoticon = getattr(reaction, "emoticon", None)
    if emoticon:
        return emoticon

    document_id = getattr(reaction, "document_id", None)
    if document_id:
        return f"custom_emoji:{document_id}"

    return reaction.__class__.__name__


def get_update_reaction_context(update):
    peer = getattr(update, "peer", None)
    msg_id = getattr(update, "msg_id", None)
    message = getattr(update, "message", None)
    message_reactions = getattr(update, "reactions", None)

    if message is not None:
        peer = getattr(message, "peer_id", peer)
        msg_id = getattr(message, "id", msg_id)
        message_reactions = getattr(message, "reactions", message_reactions)

    reactions = list(getattr(message_reactions, "recent_reactions", None) or [])
    reactions.extend(
        result for result in (getattr(message_reactions, "results", None) or [])
        if getattr(result, "chosen_order", None) is not None
    )
    return peer, msg_id, reactions, message


def is_my_trigger_reaction(recent_reaction, sender_id, user_id, trigger):
    reaction = get_reaction_value(getattr(recent_reaction, "reaction", None))
    is_mine = (
        sender_id == user_id or getattr(recent_reaction, "my", False)
        or getattr(recent_reaction, "chosen_order", None) is not None
    )
    return is_mine and (trigger == '*' or reaction == trigger)
