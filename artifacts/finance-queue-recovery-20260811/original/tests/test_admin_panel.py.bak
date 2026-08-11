import asyncio
from pathlib import Path
from types import SimpleNamespace


def _callbacks(rows):
    return {button.data for row in rows for button in row if hasattr(button, "data")}


def test_source_and_time_input_normalization_is_strict():
    import admin

    assert admin.normalize_source("https://t.me/AniZedEdits/") == "@AniZedEdits"
    assert admin.normalize_source("AniZedEdits") == "@AniZedEdits"
    assert admin.normalize_source("not valid!") is None
    assert admin.normalize_slot("07:05") == "07:05"
    assert admin.normalize_slot("23:59") == "23:59"
    assert admin.normalize_slot("24:00") is None
    assert admin.normalize_slot("7:05") is None


def test_safe_view_retries_with_unicode_buttons_when_premium_icons_fail():
    import admin

    class Event:
        def __init__(self):
            self.calls = []

        async def reply(self, text, **kwargs):
            self.calls.append((text, kwargs))
            if len(self.calls) == 1:
                raise RuntimeError("CUSTOM_EMOJI_INVALID")
            return "sent"

    premiums = []

    def buttons(premium):
        premiums.append(premium)
        return [[f"premium={premium}"]]

    event = Event()
    result = asyncio.run(admin.send_view(event, "hello", buttons))

    assert result == "sent"
    assert premiums == [True, False]
    assert event.calls[1][1]["buttons"] == [["premium=False"]]


def test_home_view_summarizes_storage_and_has_main_callbacks(monkeypatch):
    import admin

    monkeypatch.setattr(admin.storage, "get", lambda key: "1" if key == "enabled" else "")
    monkeypatch.setattr(admin.storage, "get_list", lambda key: ["10:00", "13:00"])
    monkeypatch.setattr(
        admin.storage,
        "list_queue",
        lambda day: [
            ("10:00", "@one", 1, 0, 0, "posted"),
            ("13:00", "@two", 2, 0, 0, "pending"),
            ("18:00", "@three", 3, 0, 0, "failed"),
        ],
    )
    monkeypatch.setattr(admin.storage, "today", lambda: "2026-08-11")

    text, buttons = admin.home_view(premium=False)

    assert "Бот работает" in text
    assert "Опубликовано: <b>1</b>" in text
    assert "Ожидает: <b>1</b>" in text
    assert "Ошибки: <b>1</b>" in text
    assert b"ui:now" in _callbacks(buttons)
    assert b"ui:logs" in _callbacks(buttons)


def test_queue_callback_edits_one_screen_with_links_and_buttons(monkeypatch):
    import admin

    monkeypatch.setattr(admin.storage, "today", lambda: "2026-08-11")
    monkeypatch.setattr(
        admin.storage,
        "list_queue",
        lambda day: [("10:00", "@one", 7, 0, 0, "pending")],
    )

    class Event:
        data = b"ui:queue"
        sender_id = 1
        is_private = True

        def __init__(self):
            self.edits = []
            self.answers = []

        async def edit(self, text, **kwargs):
            self.edits.append((text, kwargs))

        async def answer(self, text="", **kwargs):
            self.answers.append((text, kwargs))

    event = Event()
    asyncio.run(admin.handle_ui_callback(event, "reader", "bot"))

    assert 'href="https://t.me/one/7"' in event.edits[-1][0]
    assert b"ui:refresh" in _callbacks(event.edits[-1][1]["buttons"])


def test_settings_callbacks_toggle_enabled_and_moderation(monkeypatch):
    import admin

    values = {"enabled": "1", "moderation": "0", "slots": "10:00", "sources": "@one"}
    monkeypatch.setattr(admin.storage, "get", lambda key: values[key])
    monkeypatch.setattr(admin.storage, "set_value", lambda key, value: values.__setitem__(key, value))

    class Event:
        sender_id = 1
        is_private = True

        def __init__(self, data):
            self.data = data
            self.edits = []

        async def edit(self, text, **kwargs):
            self.edits.append((text, kwargs))

        async def answer(self, *args, **kwargs):
            pass

    event = Event(b"ui:toggle_enabled")
    asyncio.run(admin.handle_ui_callback(event, "reader", "bot"))
    assert values["enabled"] == "0"
    assert "приостановлен" in event.edits[-1][0]

    event = Event(b"ui:toggle_moderation")
    asyncio.run(admin.handle_ui_callback(event, "reader", "bot"))
    assert values["moderation"] == "1"
    assert "включена" in event.edits[-1][0]


def test_log_download_is_sent_to_owner_and_temp_file_is_removed(monkeypatch):
    import admin

    monkeypatch.setattr(admin.botlogs.BUFFER, "render_text", lambda category: "line one\nline two")

    class Event:
        chat_id = 44
        sender_id = 44
        is_private = True
        data = b"ui:logs:download"

        async def answer(self, *args, **kwargs):
            pass

        async def edit(self, *args, **kwargs):
            pass

    class Bot:
        def __init__(self):
            self.path = None
            self.contents = None

        async def send_file(self, chat_id, path, **kwargs):
            self.path = Path(path)
            self.contents = self.path.read_text(encoding="utf-8")
            assert chat_id == 44

    bot = Bot()
    asyncio.run(admin.handle_ui_callback(Event(), "reader", bot))

    assert bot.contents == "line one\nline two"
    assert bot.path is not None
    assert not bot.path.exists()


def test_next_message_adds_valid_schedule_time(monkeypatch):
    import admin

    values = {"slots": "10:00,13:00"}
    monkeypatch.setattr(admin.storage, "get_list", lambda key: values[key].split(","))
    monkeypatch.setattr(admin.storage, "set_value", lambda key, value: values.__setitem__(key, value))
    admin._pending_input.clear()
    admin._pending_input[7] = "time_add"

    class Event:
        sender_id = 7
        is_private = True
        raw_text = "18:00"

        def __init__(self):
            self.replies = []

        async def reply(self, text, **kwargs):
            self.replies.append((text, kwargs))

    handled = asyncio.run(admin.handle_pending_input(Event(), "reader"))

    assert handled is True
    assert values["slots"] == "10:00,13:00,18:00"
    assert 7 not in admin._pending_input

def test_quick_navigation_cancels_pending_text_input():
    import admin

    admin._pending_input.clear()
    admin._pending_input[9] = "source_add"

    class Event:
        sender_id = 9
        raw_text = "🏠 Меню"

    import asyncio
    assert asyncio.run(admin.handle_pending_input(Event(), "reader")) is False
    assert 9 not in admin._pending_input
