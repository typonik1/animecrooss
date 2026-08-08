import asyncio
import importlib
from types import SimpleNamespace


def test_clear_pending_keeps_published_queue_history(tmp_path, monkeypatch):
    import config

    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "test.db"))
    import storage

    importlib.reload(storage)
    storage.init()
    item = {"source": "@source", "message_id": 1, "file_uid": "uid", "fingerprint": "fp"}
    storage.enqueue("2026-08-09", "10:00", item)
    storage.enqueue("2026-08-09", "13:00", {**item, "message_id": 2})
    posted = storage.take_slot("2026-08-09", "13:00")
    storage.set_status(posted["id"], "posted")

    assert storage.clear_pending("2026-08-09") == 1
    assert storage.list_queue("2026-08-09") == [("13:00", "@source", 2, 0.0, 0, "posted")]


def test_now_selects_and_publishes_without_queue(monkeypatch):
    import admin

    item = {"source": "@source", "message_id": 7}
    calls = []

    async def collect(reader, need):
        calls.append(("collect", reader, need))
        return [item]

    async def publish(reader, bot, selected):
        calls.append(("publish", reader, bot, selected))
        return True

    monkeypatch.setattr(admin.builder, "collect", collect)
    monkeypatch.setattr(admin.publisher, "publish", publish)

    assert asyncio.run(admin.publish_now("reader", "bot")) is True
    assert calls == [("collect", "reader", 1), ("publish", "reader", "bot", item)]


def test_publisher_does_not_update_queue_for_urgent_item(tmp_path, monkeypatch):
    import publisher

    message = SimpleNamespace(id=7, message="")
    video_path = tmp_path / "video.mp4"
    video_path.write_bytes(b"video")

    class Reader:
        async def get_messages(self, source, ids):
            return message

        async def download_media(self, msg, file):
            return str(video_path)

    class Bot:
        async def send_file(self, *args, **kwargs):
            return None

    monkeypatch.setattr(publisher.filters, "get_video", lambda msg: object())
    monkeypatch.setattr(publisher.filters, "file_name_of", lambda msg: "")
    monkeypatch.setattr(publisher.filters, "looks_like_ad", lambda msg: False)
    async def parse_caption(text, filename):
        return {"anime": "", "track": "", "ad": False}
    monkeypatch.setattr(publisher.enrich, "parse_caption", parse_caption)
    monkeypatch.setattr(publisher.enrich, "build_caption", lambda anime, track: "caption")
    statuses = []
    posted = []
    monkeypatch.setattr(publisher.storage, "set_status", lambda *args: statuses.append(args))
    monkeypatch.setattr(publisher.storage, "mark_posted", lambda *args: posted.append(args))

    item = {"source": "@source", "message_id": 7, "file_uid": "uid", "fingerprint": "fp"}
    assert asyncio.run(publisher.publish(Reader(), Bot(), item)) is True
    assert statuses == []
    assert posted == [("@source", 7, "uid", "fp")]


def test_now_returns_none_when_no_fresh_video_exists(monkeypatch):
    import admin

    async def collect(reader, need):
        return []

    monkeypatch.setattr(admin.builder, "collect", collect)
    assert asyncio.run(admin.publish_now("reader", "bot")) is None


def test_refresh_replaces_pending_only_after_new_items_are_collected(monkeypatch):
    import admin

    calls = []
    monkeypatch.setattr(admin.storage, "today", lambda: "2026-08-09")
    monkeypatch.setattr(admin.storage, "pending_count", lambda day: calls.append(("count", day)) or 2)

    async def collect(reader, need):
        calls.append(("collect", reader, need))
        return [{"message_id": 1}, {"message_id": 2}]

    monkeypatch.setattr(admin.builder, "collect", collect)
    monkeypatch.setattr(
        admin.storage,
        "replace_pending",
        lambda day, items: calls.append(("replace", day, items)) or len(items),
    )
    assert asyncio.run(admin.refresh_queue("reader")) == (2, 2)
    assert calls == [
        ("count", "2026-08-09"),
        ("collect", "reader", 2),
        ("replace", "2026-08-09", [{"message_id": 1}, {"message_id": 2}]),
    ]


def test_refresh_keeps_pending_when_no_replacements_exist(monkeypatch):
    import admin

    monkeypatch.setattr(admin.storage, "today", lambda: "2026-08-09")
    monkeypatch.setattr(admin.storage, "pending_count", lambda day: 2)

    async def collect(reader, need):
        return []

    monkeypatch.setattr(admin.builder, "collect", collect)
    replaced = []
    monkeypatch.setattr(admin.storage, "replace_pending", lambda *args: replaced.append(args))

    assert asyncio.run(admin.refresh_queue("reader")) == (0, 0)
    assert replaced == []


def test_replace_pending_keeps_unreplaced_slots_and_history(tmp_path, monkeypatch):
    import config

    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "replace.db"))
    import storage

    importlib.reload(storage)
    storage.init()
    original = {"source": "@old", "file_uid": "", "fingerprint": ""}
    storage.enqueue("2026-08-09", "10:00", {**original, "message_id": 1})
    storage.enqueue("2026-08-09", "13:00", {**original, "message_id": 2})
    storage.enqueue("2026-08-09", "18:00", {**original, "message_id": 3})
    posted = storage.take_slot("2026-08-09", "18:00")
    storage.set_status(posted["id"], "posted")

    replacement = {
        "source": "@new", "message_id": 9, "file_uid": "uid-9",
        "fingerprint": "fp-9", "score": 99, "is_fallback": 0,
    }
    assert storage.replace_pending("2026-08-09", [replacement]) == 1
    assert storage.list_queue("2026-08-09") == [
        ("10:00", "@new", 9, 99.0, 0, "pending"),
        ("13:00", "@old", 2, 0.0, 0, "pending"),
        ("18:00", "@old", 3, 0.0, 0, "posted"),
    ]


def test_queue_controls_have_refresh_button():
    import admin

    button = admin.queue_controls()
    assert button.text == "🔄 Обновить очередь"
    assert button.data == b"refresh_queue"


def test_queue_line_links_directly_to_source_message():
    import admin

    line = admin.queue_line("10:00", "@Anitik_edits", 22931, 123, 0, "pending")

    assert line == (
        '10:00 🆕 <a href="https://t.me/Anitik_edits/22931">'
        '@Anitik_edits/22931</a> · pending'
    )
