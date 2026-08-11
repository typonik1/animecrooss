"""Owner-only Telegram commands and the button-first control panel."""

import asyncio
import logging
import re
import tempfile
from collections import Counter
from html import escape
from pathlib import Path

from telethon import Button, events, functions, types

import botlogs
import builder
import config
import publisher
import storage
import telegram_ui


log = logging.getLogger("admin")
_now_lock = asyncio.Lock()
_pending_input: dict[int, str] = {}

HELP = (
    "🎛 <b>Управление ботом</b>\n"
    "Нажимай кнопки ниже — основные действия больше не требуют команд.\n\n"
    "Команды остаются для быстрого доступа: /menu /now /queue /logs"
)
SET_USAGE = "Использование: /set параметр значение\nПараметры: " + ", ".join(config.DEFAULTS)


def is_owner(event):
    return event.is_private and event.sender_id in config.OWNER_IDS


def normalize_source(value: str) -> str | None:
    value = value.strip()
    value = re.sub(r"^https?://t\.me/", "", value, flags=re.IGNORECASE).strip("/")
    value = value.lstrip("@")
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{3,31}", value):
        return None
    return "@" + value


def normalize_slot(value: str) -> str | None:
    value = value.strip()
    if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", value):
        return None
    return value


def queue_controls():
    """Compatibility control used by previously sent /queue messages."""
    return Button.inline("🔄 Обновить очередь", b"refresh_queue")


def queue_line(slot, source, message_id, score, is_fallback, status):
    """Compatibility formatter retained for command-level regression tests."""
    label = f"{source}/{message_id}"
    if source.startswith("@"):
        username = source[1:]
        post = f'<a href="https://t.me/{username}/{message_id}">{escape(label)}</a>'
    else:
        post = escape(label)
    return f"{escape(slot)} {'🕓' if is_fallback else '🆕'} {post} · {escape(status)}"


async def _call_view(method, text: str, buttons_factory, **kwargs):
    common = {"parse_mode": "html", "link_preview": False, **kwargs}
    try:
        return await method(text, buttons=buttons_factory(True), **common)
    except Exception:
        log.warning("Premium-кнопки отклонены Telegram; использую Unicode", exc_info=True)
        return await method(text, buttons=buttons_factory(False), **common)


async def send_view(event, text: str, buttons_factory):
    return await _call_view(event.reply, text, buttons_factory)


async def edit_view(event, text: str, buttons_factory):
    return await _call_view(event.edit, text, buttons_factory)


def home_view(*, premium: bool = True):
    rows = storage.list_queue(storage.today())
    counts = Counter(row[5] for row in rows)
    enabled = storage.get("enabled") == "1"
    return (
        telegram_ui.dashboard_text(
            enabled=enabled,
            counts=dict(counts),
            slots=storage.get_list("slots"),
        ),
        telegram_ui.main_buttons(enabled=enabled, premium=premium),
    )


async def show_home(event, *, edit: bool = False):
    method = event.edit if edit else event.reply

    def buttons(premium):
        return home_view(premium=premium)[1]

    text = home_view(premium=False)[0]
    return await _call_view(method, text, buttons)


def sources_text() -> str:
    sources = storage.get_list("sources")
    lines = ["📡 <b>Источники роликов</b>", ""]
    lines.extend(f"{index + 1}. <code>{escape(source)}</code>" for index, source in enumerate(sources))
    if not sources:
        lines.append("Источников пока нет")
    return "\n".join(lines)


def schedule_text() -> str:
    slots = storage.get_list("slots")
    return "🕒 <b>Расписание</b>\n\n" + (" · ".join(f"<b>{escape(slot)}</b>" for slot in slots) or "Слоты не заданы")


def settings_text() -> str:
    enabled = storage.get("enabled") == "1"
    moderation = storage.get("moderation") == "1"
    return "\n".join(
        [
            "⚙️ <b>Настройки</b>",
            "",
            f"Публикации: {'🟢 включены' if enabled else '🔴 приостановлены'}",
            f"Модерация: {'🟢 включена' if moderation else '⚪ выключена'}",
            f"Источников: <b>{len(storage.get_list('sources'))}</b>",
            f"Слотов: <b>{len(storage.get_list('slots'))}</b>",
        ]
    )


def config_text() -> str:
    lines = ["ℹ️ <b>Текущая конфигурация</b>", ""]
    lines.extend(f"<code>{escape(key)} = {escape(storage.get(key))}</code>" for key in config.DEFAULTS)
    return "\n".join(lines)


async def publish_now(reader, bot):
    items = await builder.collect(reader, 1)
    if not items:
        return None
    return await publisher.publish(reader, bot, items[0])


async def handle_now(event, reader, bot):
    if _now_lock.locked():
        await event.reply("Команда /now уже выполняется")
        return False
    await _now_lock.acquire()
    try:
        await event.reply("Ищу свежий уникальный ролик…")
        try:
            result = await asyncio.wait_for(publish_now(reader, bot), timeout=config.NOW_TIMEOUT_SEC)
        except asyncio.TimeoutError:
            log.error("Команда /now превысила таймаут %.0f сек", config.NOW_TIMEOUT_SEC)
            await event.reply("Время ожидания /now истекло. Попробуй ещё раз.")
            return False
        except Exception:
            log.exception("Ошибка команды /now")
            await event.reply("Ошибка /now: публикация не выполнена")
            return False
        await event.reply(
            "Опубликовано"
            if result is True
            else "Ошибка публикации"
            if result is False
            else "Свежих уникальных роликов не найдено"
        )
        return result
    finally:
        _now_lock.release()


async def refresh_queue(reader):
    day = storage.today()
    pending = storage.pending_count(day)
    replaced = 0
    if pending:
        items = await builder.collect(reader, pending)
        if items:
            replaced = storage.replace_pending(day, items)
    filled = await builder.build_day(reader, day)
    return replaced, replaced + filled


async def _show_queue(event):
    text = telegram_ui.queue_text(storage.list_queue(storage.today()))
    return await edit_view(event, text, lambda premium: telegram_ui.queue_buttons(premium=premium))


async def _show_sources(event):
    sources = storage.get_list("sources")
    return await edit_view(
        event,
        sources_text(),
        lambda premium: telegram_ui.source_buttons(sources, premium=premium),
    )


async def _show_schedule(event):
    slots = storage.get_list("slots")
    return await edit_view(
        event,
        schedule_text(),
        lambda premium: telegram_ui.schedule_buttons(slots, premium=premium),
    )


async def _show_settings(event):
    enabled = storage.get("enabled") == "1"
    moderation = storage.get("moderation") == "1"
    return await edit_view(
        event,
        settings_text(),
        lambda premium: telegram_ui.settings_buttons(
            enabled=enabled, moderation=moderation, premium=premium
        ),
    )


async def _show_logs(event, category: str = "all"):
    return await edit_view(
        event,
        botlogs.BUFFER.render_html(category),
        lambda premium: telegram_ui.log_buttons(premium=premium),
    )


async def _download_logs(event, bot):
    path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", suffix=".txt", prefix="anime-bot-logs-", delete=False
        ) as stream:
            stream.write(botlogs.BUFFER.render_text("all"))
            path = Path(stream.name)
        await bot.send_file(
            event.chat_id,
            str(path),
            caption="📥 Логи бота",
            force_document=True,
        )
    finally:
        if path is not None:
            path.unlink(missing_ok=True)


async def handle_ui_callback(event, reader, bot):
    data = bytes(event.data).decode("utf-8")
    if data == "ui:home":
        return await show_home(event, edit=True)
    if data == "ui:queue":
        return await _show_queue(event)
    if data == "ui:now":
        await event.answer("Запускаю срочную публикацию…")
        return await handle_now(event, reader, bot)
    if data == "ui:refresh":
        await event.answer("Обновляю очередь…")
        removed, added = await asyncio.wait_for(
            refresh_queue(reader), timeout=config.BUILD_TIMEOUT_SEC
        )
        text = (
            f"🔄 <b>Очередь обновлена</b>\n"
            f"Заменено: <b>{removed}</b> · добавлено: <b>{added}</b>\n\n"
            + telegram_ui.queue_text(storage.list_queue(storage.today()))
        )
        return await edit_view(event, text, lambda premium: telegram_ui.queue_buttons(premium=premium))
    if data == "ui:build":
        await event.answer("Собираю очередь…")
        added = await asyncio.wait_for(builder.build_day(reader), timeout=config.BUILD_TIMEOUT_SEC)
        text = f"🧩 <b>Сборка завершена</b> · добавлено: <b>{added}</b>\n\n" + telegram_ui.queue_text(storage.list_queue(storage.today()))
        return await edit_view(event, text, lambda premium: telegram_ui.queue_buttons(premium=premium))
    if data == "ui:sources":
        return await _show_sources(event)
    if data == "ui:source:add":
        _pending_input[event.sender_id] = "source_add"
        return await edit_view(
            event,
            "➕ <b>Новый источник</b>\n\nОтправь следующим сообщением <code>@channel</code> или ссылку <code>https://t.me/channel</code>.",
            lambda premium: [[telegram_ui.home_button(premium=premium)]],
        )
    if data.startswith("ui:source:del:"):
        index = int(data.rsplit(":", 1)[1])
        sources = storage.get_list("sources")
        if 0 <= index < len(sources):
            removed = sources.pop(index)
            storage.set_value("sources", ",".join(sources))
            await event.answer(f"Удалён {removed}")
        return await _show_sources(event)
    if data == "ui:times":
        return await _show_schedule(event)
    if data == "ui:time:add":
        _pending_input[event.sender_id] = "time_add"
        return await edit_view(
            event,
            "➕ <b>Новый слот</b>\n\nОтправь следующим сообщением время в формате <code>HH:MM</code>, например <code>18:00</code>.",
            lambda premium: [[telegram_ui.home_button(premium=premium)]],
        )
    if data.startswith("ui:time:del:"):
        raw = data.rsplit(":", 1)[1]
        slot = f"{raw[:2]}:{raw[2:]}"
        slots = [item for item in storage.get_list("slots") if item != slot]
        storage.set_value("slots", ",".join(slots))
        await event.answer(f"Удалён слот {slot}")
        return await _show_schedule(event)
    if data == "ui:time:default":
        storage.set_value("slots", config.DEFAULTS["slots"])
        await event.answer("Расписание восстановлено")
        return await _show_schedule(event)
    if data == "ui:settings":
        return await _show_settings(event)
    if data == "ui:toggle_enabled":
        value = "0" if storage.get("enabled") == "1" else "1"
        storage.set_value("enabled", value)
        await event.answer("Публикации включены" if value == "1" else "Публикации приостановлены")
        return await _show_settings(event)
    if data == "ui:toggle_moderation":
        value = "0" if storage.get("moderation") == "1" else "1"
        storage.set_value("moderation", value)
        await event.answer("Модерация включена" if value == "1" else "Модерация выключена")
        return await _show_settings(event)
    if data == "ui:config":
        return await edit_view(
            event,
            config_text(),
            lambda premium: [[telegram_ui.home_button(premium=premium)]],
        )
    if data in {"ui:logs", "ui:logs:all"}:
        return await _show_logs(event, "all")
    if data == "ui:logs:errors":
        return await _show_logs(event, "errors")
    if data == "ui:logs:publisher":
        return await _show_logs(event, "publisher")
    if data == "ui:logs:scheduler":
        return await _show_logs(event, "scheduler")
    if data == "ui:logs:download":
        await event.answer("Готовлю TXT…")
        return await _download_logs(event, bot)
    await event.answer("Неизвестная кнопка", alert=False)
    return None


async def handle_pending_input(event, reader):
    action = _pending_input.get(event.sender_id)
    if not action:
        return False
    if event.raw_text.strip() in {
        "Меню", "🏠 Меню", "Сейчас", "🚀 Сейчас",
        "Очередь", "📋 Очередь", "Логи", "📜 Логи",
    }:
        _pending_input.pop(event.sender_id, None)
        return False
    if action == "source_add":
        source = normalize_source(event.raw_text)
        if source is None:
            await event.reply("❌ Нужен username канала: <code>@channel</code>", parse_mode="html")
            return True
        try:
            await reader.get_entity(source)
        except Exception:
            await event.reply("❌ Аккаунт-читатель не видит этот канал. Сначала подпиши его на канал.")
            return True
        sources = storage.get_list("sources")
        if source not in sources:
            sources.append(source)
            storage.set_value("sources", ",".join(sources))
        _pending_input.pop(event.sender_id, None)
        await send_view(
            event,
            f"✅ Источник <code>{escape(source)}</code> добавлен",
            lambda premium: telegram_ui.source_buttons(sources, premium=premium),
        )
        return True
    if action == "time_add":
        slot = normalize_slot(event.raw_text)
        if slot is None:
            await event.reply("❌ Время должно быть в формате <code>HH:MM</code>, например <code>18:00</code>.", parse_mode="html")
            return True
        slots = sorted(set(storage.get_list("slots") + [slot]))
        storage.set_value("slots", ",".join(slots))
        _pending_input.pop(event.sender_id, None)
        await send_view(
            event,
            f"✅ Слот <b>{slot}</b> добавлен",
            lambda premium: telegram_ui.schedule_buttons(slots, premium=premium),
        )
        return True
    return False


async def install_commands(bot):
    commands = [
        types.BotCommand("start", "Открыть панель управления"),
        types.BotCommand("menu", "Главное меню"),
        types.BotCommand("now", "Опубликовать ролик сейчас"),
        types.BotCommand("queue", "Показать очередь"),
        types.BotCommand("logs", "Показать логи"),
    ]
    return await bot(
        functions.bots.SetBotCommandsRequest(
            scope=types.BotCommandScopeDefault(), lang_code="ru", commands=commands
        )
    )


async def send_ready(bot):
    """Show every owner the persistent keyboard and fresh inline dashboard."""
    for owner_id in sorted(config.OWNER_IDS):
        views = (
            (
                "✅ <b>Бот запущен</b>\nПанель управления готова.",
                lambda premium: telegram_ui.quick_keyboard(premium=premium),
            ),
            (
                home_view(premium=False)[0],
                lambda premium: home_view(premium=premium)[1],
            ),
        )
        for text, buttons_factory in views:
            try:
                await bot.send_message(
                    owner_id,
                    text,
                    buttons=buttons_factory(True),
                    parse_mode="html",
                    link_preview=False,
                )
            except Exception:
                try:
                    await bot.send_message(
                        owner_id,
                        text,
                        buttons=buttons_factory(False),
                        parse_mode="html",
                        link_preview=False,
                    )
                except Exception:
                    log.warning("Не удалось отправить стартовую панель владельцу %s", owner_id)


def register(bot, reader):
    def owner(event):
        return is_owner(event)

    @bot.on(events.NewMessage(pattern=r"^/(start|help)$"))
    async def start_cmd(event):
        if is_owner(event):
            await send_view(event, HELP, lambda premium: telegram_ui.quick_keyboard(premium=premium))
            await show_home(event)
        elif event.is_private:
            await event.reply(f"Ваш id: <code>{event.sender_id}</code>", parse_mode="html")

    @bot.on(events.NewMessage(pattern=r"^/menu$|^(?:🏠\s*)?Меню$"))
    async def menu_cmd(event):
        if owner(event):
            await show_home(event)

    @bot.on(events.NewMessage(pattern=r"^/id$"))
    async def id_cmd(event):
        await event.reply(f"<code>{event.sender_id}</code>", parse_mode="html")

    @bot.on(events.NewMessage(pattern=r"^/sources$"))
    async def sources_cmd(event):
        if owner(event):
            await send_view(
                event,
                sources_text(),
                lambda premium: telegram_ui.source_buttons(storage.get_list("sources"), premium=premium),
            )

    @bot.on(events.NewMessage(pattern=r"^/add\s+(\S+)$"))
    async def add_cmd(event):
        if not owner(event):
            return
        source = normalize_source(event.pattern_match.group(1))
        if source is None:
            await event.reply("Неверный username канала")
            return
        try:
            await reader.get_entity(source)
        except Exception:
            await event.reply("Не могу открыть канал: аккаунт-читатель должен быть на него подписан.")
            return
        sources = storage.get_list("sources")
        if source not in sources:
            storage.set_value("sources", ",".join(sources + [source]))
        await event.reply(f"Добавлен {source}")

    @bot.on(events.NewMessage(pattern=r"^/del\s+(\S+)$"))
    async def delete_cmd(event):
        if owner(event):
            source = normalize_source(event.pattern_match.group(1))
            storage.set_value(
                "sources",
                ",".join(item for item in storage.get_list("sources") if item.lower() != (source or "").lower()),
            )
            await event.reply("Удалено")

    @bot.on(events.NewMessage(pattern=r"^/times(?:\s+(.+))?$"))
    async def times_cmd(event):
        if not owner(event):
            return
        arg = event.pattern_match.group(1)
        if arg:
            slots = [normalize_slot(item) for item in arg.split(",")]
            if any(slot is None for slot in slots):
                await event.reply("Неверное время. Формат: /times 10:00,13:00")
                return
            storage.set_value("slots", ",".join(sorted(set(slots))))
        await event.reply("Слоты: " + storage.get("slots"))

    @bot.on(events.NewMessage(pattern=r"^/queue$|^(?:📋\s*)?Очередь$"))
    async def queue_cmd(event):
        if owner(event):
            await send_view(
                event,
                telegram_ui.queue_text(storage.list_queue(storage.today())),
                lambda premium: telegram_ui.queue_buttons(premium=premium),
            )

    @bot.on(events.NewMessage(pattern=r"^/build$"))
    async def build_cmd(event):
        if owner(event):
            await event.reply(f"Добавлено: {await builder.build_day(reader)}")

    @bot.on(events.NewMessage(pattern=r"^/skip\s+(\S+)$"))
    async def skip_cmd(event):
        if not owner(event):
            return
        item = storage.skip_slot(storage.today(), event.pattern_match.group(1))
        if item:
            storage.mark_posted(item["source"], item["message_id"], item["file_uid"], item["fingerprint"])
            await builder.build_day(reader)
        await event.reply("Готово")

    @bot.on(events.NewMessage(pattern=r"^/now$|^(?:🚀\s*)?Сейчас$"))
    async def now_cmd(event):
        if owner(event):
            await handle_now(event, reader, bot)

    @bot.on(events.NewMessage(pattern=r"^/logs$|^(?:📜\s*)?Логи$"))
    async def logs_cmd(event):
        if owner(event):
            await send_view(
                event,
                botlogs.BUFFER.render_html("all"),
                lambda premium: telegram_ui.log_buttons(premium=premium),
            )

    @bot.on(events.CallbackQuery(pattern=rb"^ui:"))
    async def ui_callback(event):
        if not is_owner(event):
            await event.answer("Нет доступа", alert=True)
            return
        try:
            await handle_ui_callback(event, reader, bot)
        except asyncio.TimeoutError:
            log.error("Таймаут действия панели: %r", event.data)
            await event.answer("Операция превысила время ожидания", alert=True)
        except Exception:
            log.exception("Ошибка действия панели: %r", event.data)
            await event.answer("Ошибка выполнения. Подробности в логах.", alert=True)

    @bot.on(events.CallbackQuery(data=b"refresh_queue"))
    async def legacy_refresh(event):
        if not is_owner(event):
            return
        removed, added = await refresh_queue(reader)
        await event.answer("Очередь обновлена", alert=False)
        await event.edit(
            f"Очередь обновлена: удалено {removed}, добавлено {added}",
            buttons=queue_controls(),
        )

    @bot.on(events.NewMessage(pattern=r"^/set(?:\s+(\w+)(?:\s+(.+))?)?$"))
    async def setting_cmd(event):
        if not owner(event):
            return
        key, value = event.pattern_match.group(1), event.pattern_match.group(2)
        if not key or value is None:
            await event.reply(SET_USAGE)
        elif key in config.DEFAULTS:
            value = value.strip()
            storage.set_value(key, value)
            await event.reply(f"{key} = {value}")
        else:
            await event.reply("Неизвестный параметр\n" + SET_USAGE)

    @bot.on(events.NewMessage(pattern=r"^/config$"))
    async def config_cmd(event):
        if owner(event):
            await event.reply(config_text(), parse_mode="html")

    @bot.on(events.NewMessage(pattern=r"^/(pause|resume)$"))
    async def enabled_cmd(event):
        if owner(event):
            storage.set_value("enabled", "0" if event.pattern_match.group(1) == "pause" else "1")
            await event.reply("Готово")

    @bot.on(events.NewMessage())
    async def pending_input(event):
        if owner(event) and not event.raw_text.startswith("/"):
            await handle_pending_input(event, reader)
