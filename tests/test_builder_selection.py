import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import builder


def item(source, score, message_id):
    return {"source": source, "score": score, "message_id": message_id}


def test_balanced_select_rotates_sources_and_keeps_activity_order():
    groups = {
        "@a": [item("@a", 10, 1), item("@a", 100, 2)],
        "@b": [item("@b", 20, 3), item("@b", 90, 4)],
        "@c": [item("@c", 80, 5)],
    }
    selected = builder.balanced_select(groups, 5)
    assert [(x["source"], x["score"]) for x in selected] == [
        ("@a", 100), ("@b", 90), ("@c", 80), ("@a", 10), ("@b", 20)
    ]


def test_collect_never_requests_archive_scan(monkeypatch):
    monkeypatch.setattr(builder.storage, "get_list", lambda key: ["@a", "@b"])
    monkeypatch.setattr(builder.storage, "get_int", lambda key: 120)
    calls = []

    async def scan(reader, source, limit, since, fresh):
        calls.append((source, fresh))
        return []

    monkeypatch.setattr(builder, "_scan", scan)
    assert asyncio.run(builder.collect(object(), 4)) == []
    assert calls == [("@a", True), ("@b", True)]


def test_target_history_imports_video_fingerprints(monkeypatch):
    messages = [SimpleNamespace(id=11), SimpleNamespace(id=12)]

    class Reader:
        async def get_messages(self, target, limit):
            assert target == "@target"
            assert limit == 500
            return messages

    monkeypatch.setattr(builder.config, "TARGET_CHANNEL", "@target")
    monkeypatch.setattr(builder.filters, "get_video", lambda msg: object() if msg.id == 11 else None)
    monkeypatch.setattr(builder.filters, "fingerprint", lambda msg: ("ignored", "fp-11"))
    marked = []
    monkeypatch.setattr(builder.storage, "mark_posted", lambda source, mid, uid, fp: marked.append((source, mid, uid, fp)))

    count = asyncio.run(builder.sync_target_history(Reader(), limit=500))
    assert count == 1
    assert marked == [("__target__", 11, "", "fp-11")]


def test_scan_activity_threshold_ignores_old_popular_posts(monkeypatch):
    now = datetime.now(timezone.utc)
    old = [SimpleNamespace(id=i, date=now - timedelta(days=30), views=10_000) for i in range(5)]
    fresh = [
        SimpleNamespace(id=100 + i, date=now - timedelta(days=1), views=views)
        for i, views in enumerate([100, 200, 300, 400, 500])
    ]

    class Reader:
        async def get_messages(self, source, limit):
            return old + fresh

    monkeypatch.setattr(builder.filters, "is_good_video", lambda msg: True)
    monkeypatch.setattr(builder.filters, "looks_like_ad", lambda msg: False)
    monkeypatch.setattr(builder.filters, "fingerprint", lambda msg: (f"uid-{msg.id}", f"fp-{msg.id}"))
    monkeypatch.setattr(builder.filters, "activity_score", lambda msg: msg.views)
    monkeypatch.setattr(builder.storage, "get_int", lambda key: 90)
    monkeypatch.setattr(builder.storage, "get_float", lambda key: 1.3)
    monkeypatch.setattr(builder.storage, "is_used", lambda *args: False)

    result = asyncio.run(
        builder._scan(Reader(), "@source", 120, now - timedelta(days=7), True)
    )

    assert [item["message_id"] for item in result] == [103, 104]
