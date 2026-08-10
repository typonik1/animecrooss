import asyncio
import logging
from datetime import date, datetime, time, timedelta, timezone

from telethon.tl.functions.messages import SendReactionRequest
from telethon.tl.types import ReactionEmoji

import config

log = logging.getLogger("reactions")


def _normalized_emoji(value: str) -> str:
    return value.replace("\ufe0f", "")


def has_own_reaction(message, emoji: str) -> bool:
    reactions = getattr(message, "reactions", None)
    for result in getattr(reactions, "results", None) or []:
        reaction = getattr(result, "reaction", None)
        if (
            getattr(result, "chosen_order", None) is not None
            and _normalized_emoji(getattr(reaction, "emoticon", "")) == _normalized_emoji(emoji)
        ):
            return True
    return False


def due_reaction_day(now: datetime) -> date:
    reaction_time = datetime.strptime(config.REACTION_AT, "%H:%M").time()
    return now.date() if now.time() >= reaction_time else now.date() - timedelta(days=1)


async def react_to_day_posts(reader, day: date, delay: float = 0.4) -> dict[str, int]:
    """Put the configured reaction on every ordinary target-channel post for a Moscow day."""
    start = datetime.combine(day, time.min, tzinfo=config.TZ).astimezone(timezone.utc)
    end = start + timedelta(days=1)
    peer = await reader.get_input_entity(config.TARGET_CHANNEL)
    stats = {"found": 0, "reacted": 0, "skipped": 0, "failed": 0}

    async for message in reader.iter_messages(config.TARGET_CHANNEL, offset_date=end):
        if not message.date or message.date >= end:
            continue
        if message.date < start:
            break
        if getattr(message, "action", None) is not None:
            continue
        stats["found"] += 1
        if has_own_reaction(message, config.REACTION_EMOJI):
            stats["skipped"] += 1
            continue
        try:
            await reader(
                SendReactionRequest(
                    peer=peer,
                    msg_id=message.id,
                    reaction=[ReactionEmoji(emoticon=config.REACTION_EMOJI)],
                )
            )
            stats["reacted"] += 1
            if delay:
                await asyncio.sleep(delay)
        except Exception as exc:
            stats["failed"] += 1
            log.error("Не удалось поставить реакцию сообщению %s: %s", message.id, exc)

    return stats
