import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo


def _record(name, level, message):
    return logging.LogRecord(name, level, __file__, 1, message, (), None)


def test_buffer_keeps_newest_entries_and_escapes_html():
    import botlogs

    buffer = botlogs.LogBuffer(max_entries=2, now=lambda: datetime(2026, 8, 11, 15, 30, tzinfo=ZoneInfo("Europe/Moscow")))
    buffer.emit(_record("publisher", logging.INFO, "one"))
    buffer.emit(_record("scheduler", logging.WARNING, "two <unsafe>"))
    buffer.emit(_record("admin", logging.ERROR, "three & bad"))

    assert [entry.message for entry in buffer.snapshot()] == ["two <unsafe>", "three & bad"]
    html = buffer.render_html("all")
    assert "15:30" in html
    assert "two &lt;unsafe&gt;" in html
    assert "three &amp; bad" in html
    assert len(html) <= 3900


def test_filters_select_errors_publications_and_scheduler():
    import botlogs

    buffer = botlogs.LogBuffer(max_entries=10)
    buffer.emit(_record("publisher", logging.INFO, "posted"))
    buffer.emit(_record("builder", logging.INFO, "built"))
    buffer.emit(_record("main", logging.INFO, "scheduler tick"))
    buffer.emit(_record("reactions", logging.INFO, "reacted"))
    buffer.emit(_record("admin", logging.ERROR, "now failed"))

    assert [e.message for e in buffer.filtered("errors")] == ["now failed"]
    assert [e.message for e in buffer.filtered("publisher")] == ["posted", "built"]
    assert [e.message for e in buffer.filtered("scheduler")] == ["scheduler tick", "reacted"]


def test_sensitive_values_are_redacted_from_buffer():
    import botlogs

    buffer = botlogs.LogBuffer(max_entries=10)
    buffer.emit(_record("admin", logging.ERROR, "BOT_TOKEN=12345:secret TELEGRAM_SESSION_STRING=abc"))

    text = buffer.render_text("all")
    assert "12345:secret" not in text
    assert "TELEGRAM_SESSION_STRING=abc" not in text
    assert "[скрыто]" in text


def test_error_alerts_are_deduplicated_and_warnings_do_not_alert():
    import botlogs

    sent = []

    async def scenario():
        async def send(owner_id, text):
            sent.append((owner_id, text))

        now = [100.0]
        handler = botlogs.OwnerAlertHandler(
            send=send,
            owner_ids=lambda: {22, 11},
            dedupe_sec=300,
            monotonic=lambda: now[0],
        )
        handler.emit(_record("telethon.network", logging.WARNING, "reconnected"))
        handler.emit(_record("publisher", logging.ERROR, "upload failed"))
        handler.emit(_record("publisher", logging.ERROR, "upload failed"))
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        assert [owner for owner, _ in sent] == [11, 22]
        assert all("upload failed" in text for _, text in sent)

        now[0] += 301
        handler.emit(_record("publisher", logging.ERROR, "upload failed"))
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        assert [owner for owner, _ in sent] == [11, 22, 11, 22]

    asyncio.run(scenario())


def test_alert_send_failure_does_not_raise_or_log_recursively():
    import botlogs

    async def scenario():
        async def send(_owner_id, _text):
            raise RuntimeError("telegram down")

        handler = botlogs.OwnerAlertHandler(send=send, owner_ids=lambda: {1})
        handler.emit(_record("main", logging.CRITICAL, "fatal"))
        await asyncio.sleep(0)
        await asyncio.sleep(0)

    asyncio.run(scenario())

def test_single_oversized_log_entry_is_truncated_but_still_visible():
    import logging
    import botlogs

    buffer = botlogs.LogBuffer(max_entries=2)
    buffer.emit(_record("publisher", logging.ERROR, "BEGIN-" + "x" * 10000))

    html = buffer.render_html("errors")
    assert "BEGIN-" in html
    assert "…" in html
    assert len(html) <= 3900
