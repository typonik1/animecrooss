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


def test_refresh_only_clears_pending_then_rebuilds(monkeypatch):
    import admin

    calls = []
    monkeypatch.setattr(admin.storage, "today", lambda: "2026-08-09")
    monkeypatch.setattr(admin.storage, "clear_pending", lambda day: calls.append(("clear", day)) or 2)

    async def build_day(reader):
        calls.append(("build", reader))
        return 2

    monkeypatch.setattr(admin.builder, "build_day", build_day)
    assert asyncio.run(admin.refresh_queue("reader")) == (2, 2)
    assert calls == [("clear", "2026-08-09"), ("build", "reader")]


def test_queue_controls_have_refresh_button():
    import admin

    button = admin.queue_controls()
    assert button.text == "🔄 Обновить очередь"
    assert button.data == b"refresh_queue"
