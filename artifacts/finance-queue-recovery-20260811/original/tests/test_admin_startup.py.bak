import asyncio
import logging


def test_setup_admin_ui_loads_emoji_commands_and_error_alerts(monkeypatch):
    import main

    calls = []

    async def load(reader):
        calls.append(("emoji", reader))
        return 42

    async def commands(bot):
        calls.append(("commands", bot))

    monkeypatch.setattr(main.telegram_ui, "load_emoji_set", load)
    monkeypatch.setattr(main.admin, "install_commands", commands)
    monkeypatch.setattr(main.botlogs, "install_owner_alerts", lambda bot: calls.append(("alerts", bot)))

    assert asyncio.run(main.setup_admin_ui("reader", "bot")) == 42
    assert calls == [("emoji", "reader"), ("commands", "bot"), ("alerts", "bot")]


def test_setup_admin_ui_keeps_running_when_emoji_set_is_unavailable(monkeypatch):
    import main

    calls = []

    async def broken(_reader):
        raise RuntimeError("sticker set unavailable")

    async def commands(bot):
        calls.append(("commands", bot))

    monkeypatch.setattr(main.telegram_ui, "load_emoji_set", broken)
    monkeypatch.setattr(main.admin, "install_commands", commands)
    monkeypatch.setattr(main.botlogs, "install_owner_alerts", lambda bot: calls.append(("alerts", bot)))

    assert asyncio.run(main.setup_admin_ui("reader", "bot")) == 0
    assert calls == [("commands", "bot"), ("alerts", "bot")]


def test_log_buffer_is_installed_on_root_logger():
    import botlogs
    import main

    assert botlogs.BUFFER in logging.getLogger().handlers


def test_runtime_pins_telethon_with_styled_button_support():
    from pathlib import Path

    assert "telethon==1.44.0" in Path("requirements.txt").read_text(encoding="utf-8")
import asyncio
from types import SimpleNamespace


def test_load_emoji_set_maps_custom_emoji_alt_to_document_id(monkeypatch):
    import telegram_ui
    from telethon import types

    telegram_ui.set_emoji_icons({})
    monkeypatch.setattr(telegram_ui.config, "UI_EMOJI_SET", "ReactionsEmojiVK")
    seen = []

    class Client:
        async def __call__(self, request):
            seen.append(request)
            return SimpleNamespace(
                documents=[
                    SimpleNamespace(
                        id=777,
                        attributes=[
                            types.DocumentAttributeCustomEmoji(
                                alt="🚀", stickerset=types.InputStickerSetEmpty()
                            )
                        ],
                    )
                ]
            )

    assert asyncio.run(telegram_ui.load_emoji_set(Client())) == 1
    button = telegram_ui.inline_button("Сейчас", b"ui:now", style="success", emoji="🚀")
    assert button.style.icon == 777
    assert seen[0].stickerset.short_name == "ReactionsEmojiVK"


def test_install_commands_registers_compact_russian_menu():
    import admin

    class Bot:
        def __init__(self):
            self.requests = []

        async def __call__(self, request):
            self.requests.append(request)
            return True

    bot = Bot()
    assert asyncio.run(admin.install_commands(bot)) is True
    request = bot.requests[0]
    assert request.lang_code == "ru"
    assert [(item.command, item.description) for item in request.commands] == [
        ("start", "Открыть панель управления"),
        ("menu", "Главное меню"),
        ("now", "Опубликовать ролик сейчас"),
        ("queue", "Показать очередь"),
        ("logs", "Показать логи"),
    ]


def test_send_ready_delivers_persistent_keyboard_and_dashboard(monkeypatch):
    import admin

    monkeypatch.setattr(admin.config, "OWNER_IDS", {22, 11})
    monkeypatch.setattr(admin.storage, "today", lambda: "2026-08-11")
    monkeypatch.setattr(admin.storage, "list_queue", lambda day: [])
    monkeypatch.setattr(admin.storage, "get", lambda key: "1" if key == "enabled" else "")
    monkeypatch.setattr(admin.storage, "get_list", lambda key: ["10:00"])

    class Bot:
        def __init__(self):
            self.messages = []

        async def send_message(self, owner_id, text, **kwargs):
            self.messages.append((owner_id, text, kwargs))

    bot = Bot()
    asyncio.run(admin.send_ready(bot))

    assert [owner for owner, _, _ in bot.messages] == [11, 11, 22, 22]
    assert "Бот запущен" in bot.messages[0][1]
    assert bot.messages[0][2]["buttons"]
    assert "Панель управления" in bot.messages[1][1]
    callbacks = {
        button.data
        for row in bot.messages[1][2]["buttons"]
        for button in row
        if hasattr(button, "data")
    }
    assert b"ui:now" in callbacks
    assert b"ui:logs" in callbacks
