import asyncio
import importlib
from datetime import datetime


def _item(message_id):
    return {
        "source": "@source",
        "message_id": message_id,
        "file_uid": f"uid-{message_id}",
        "fingerprint": f"size:{message_id}",
    }


def test_claim_next_due_atomically_claims_oldest_overdue_slot(tmp_path, monkeypatch):
    import config
    import storage

    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "claim.db"))
    importlib.reload(storage)
    storage.init()
    storage.enqueue("2026-08-11", "10:00", _item(10))
    storage.enqueue("2026-08-11", "13:00", _item(13))
    storage.enqueue("2026-08-11", "18:00", _item(18))

    first = storage.claim_next_due("2026-08-11", "13:52")
    second = storage.claim_next_due("2026-08-11", "13:52")

    assert (first["slot"], first["message_id"]) == ("10:00", 10)
    assert (second["slot"], second["message_id"]) == ("13:00", 13)
    assert storage.claim_next_due("2026-08-11", "13:52") is None
    assert storage.list_queue("2026-08-11") == [
        ("10:00", "@source", 10, 0.0, 0, "publishing"),
        ("13:00", "@source", 13, 0.0, 0, "publishing"),
        ("18:00", "@source", 18, 0.0, 0, "pending"),
    ]


def test_init_requeues_interrupted_publication_after_restart(tmp_path, monkeypatch):
    import config
    import storage

    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "restart.db"))
    importlib.reload(storage)
    storage.init()
    storage.enqueue("2026-08-11", "10:00", _item(10))
    claimed = storage.claim_next_due("2026-08-11", "10:00")
    assert claimed["slot"] == "10:00"

    storage.init()

    recovered = storage.claim_next_due("2026-08-11", "10:01")
    assert recovered["id"] == claimed["id"]


def test_skip_can_cancel_a_claimed_moderation_slot(tmp_path, monkeypatch):
    import config
    import storage

    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "skip.db"))
    importlib.reload(storage)
    storage.init()
    storage.enqueue("2026-08-11", "10:00", _item(10))
    claimed = storage.claim_next_due("2026-08-11", "10:00")

    skipped = storage.skip_slot("2026-08-11", "10:00")

    assert skipped["id"] == claimed["id"]
    assert storage.get_status(claimed["id"]) == "skipped"


def test_scheduler_tick_publishes_overdue_pending_without_running_reactions(monkeypatch):
    import config
    import main

    item = {"id": 1, "slot": "10:00", **_item(10)}
    calls = []
    monkeypatch.setattr(main.storage, "get", lambda key: "1" if key == "enabled" else "0")
    monkeypatch.setattr(
        main.storage,
        "claim_next_due",
        lambda day, hhmm: calls.append(("claim", day, hhmm)) or item,
        raising=False,
    )

    async def publish(reader, bot, selected):
        calls.append(("publish", reader, bot, selected))
        return True

    async def reactions_must_not_run(*args, **kwargs):
        raise AssertionError("daily reactions must not run inside the publishing tick")

    monkeypatch.setattr(main.publisher, "publish", publish)
    monkeypatch.setattr(main.reactions, "react_to_day_posts", reactions_must_not_run)
    now = datetime(2026, 8, 11, 13, 52, tzinfo=config.TZ)

    assert asyncio.run(main.run_scheduler_tick("reader", "bot", now)) is True
    assert calls == [
        ("claim", "2026-08-11", "13:52"),
        ("publish", "reader", "bot", item),
    ]


def test_reaction_timeout_is_contained_in_its_own_job(monkeypatch):
    import config
    import main

    async def blocked_reactions(reader, day):
        await asyncio.sleep(1)

    monkeypatch.setattr(config, "REACTION_TIMEOUT_SEC", 0.01, raising=False)
    monkeypatch.setattr(main.reactions, "react_to_day_posts", blocked_reactions)
    now = datetime(2026, 8, 11, 13, 52, tzinfo=config.TZ)

    assert asyncio.run(main.run_reactions_once("reader", now)) is False
