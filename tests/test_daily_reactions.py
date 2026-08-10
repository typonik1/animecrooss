import asyncio
from datetime import date, datetime, timezone
from types import SimpleNamespace

from telethon.tl.types import ReactionCount, ReactionEmoji

import config
import reactions


def message(message_id, timestamp, chosen=False, action=None):
    results = []
    if chosen:
        results.append(ReactionCount(ReactionEmoji("❤"), 1, chosen_order=0))
    return SimpleNamespace(
        id=message_id,
        date=timestamp,
        action=action,
        reactions=SimpleNamespace(results=results),
    )


def test_due_reaction_day_uses_today_after_cutoff_and_yesterday_before(monkeypatch):
    monkeypatch.setattr(config, "REACTION_AT", "23:55")

    assert reactions.due_reaction_day(datetime(2026, 8, 10, 23, 55)) == date(2026, 8, 10)
    assert reactions.due_reaction_day(datetime(2026, 8, 10, 8, 0)) == date(2026, 8, 9)


def test_react_to_day_posts_reacts_once_and_uses_moscow_boundaries(monkeypatch):
    monkeypatch.setattr(config, "TARGET_CHANNEL", "@target")
    monkeypatch.setattr(config, "REACTION_EMOJI", "❤")
    messages = [
        message(4, datetime(2026, 8, 9, 21, 1, tzinfo=timezone.utc)),  # 00:01 next day MSK
        message(3, datetime(2026, 8, 9, 20, 30, tzinfo=timezone.utc), chosen=True),
        message(2, datetime(2026, 8, 9, 12, 0, tzinfo=timezone.utc)),
        message(1, datetime(2026, 8, 8, 20, 59, tzinfo=timezone.utc)),
    ]

    class Reader:
        def __init__(self):
            self.requests = []

        async def get_input_entity(self, target):
            assert target == "@target"
            return "peer"

        async def __call__(self, request):
            self.requests.append(request)

        async def iter_messages(self, target, offset_date):
            assert target == "@target"
            for item in messages:
                yield item

    reader = Reader()
    stats = asyncio.run(reactions.react_to_day_posts(reader, date(2026, 8, 9), delay=0))

    assert stats == {"found": 2, "reacted": 1, "skipped": 1, "failed": 0}
    assert len(reader.requests) == 1
    assert reader.requests[0].msg_id == 2
    assert reader.requests[0].reaction[0].emoticon == "❤"
