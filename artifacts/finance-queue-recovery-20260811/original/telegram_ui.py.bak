"""Telegram control-panel presentation helpers.

The module keeps button construction in one place so commands and callback
menus have the same labels, colours and premium-emoji fallback behaviour.
"""

from html import escape

from telethon import Button, functions, types

import config


_emoji_icons: dict[str, int] = {}


def set_emoji_icons(mapping: dict[str, int]) -> None:
    """Replace the runtime mapping of Unicode alternatives to custom emoji IDs."""
    global _emoji_icons
    _emoji_icons = dict(mapping)


async def load_emoji_set(client) -> int:
    """Load custom emoji IDs from the configured Telegram emoji set."""
    result = await client(
        functions.messages.GetStickerSetRequest(
            stickerset=types.InputStickerSetShortName(config.UI_EMOJI_SET), hash=0
        )
    )
    mapping: dict[str, int] = {}
    for document in result.documents:
        for attribute in document.attributes:
            if isinstance(attribute, types.DocumentAttributeCustomEmoji):
                mapping.setdefault(attribute.alt, document.id)
    set_emoji_icons(mapping)
    return len(mapping)


def _caption(label: str, emoji: str, icon: int | None) -> str:
    return label if icon else f"{emoji} {label}".strip()


def inline_button(
    label: str,
    data: bytes,
    *,
    style: str | None = None,
    emoji: str = "",
    premium: bool = True,
):
    icon = _emoji_icons.get(emoji) if premium else None
    return Button.inline(
        _caption(label, emoji, icon), data, style=style, icon=icon
    )


def text_button(
    label: str,
    *,
    style: str | None = None,
    emoji: str = "",
    premium: bool = True,
):
    icon = _emoji_icons.get(emoji) if premium else None
    return Button.text(
        _caption(label, emoji, icon), resize=True, style=style, icon=icon
    )


def quick_keyboard(*, premium: bool = True):
    return [
        [
            text_button("Сейчас", style="success", emoji="🚀", premium=premium),
            text_button("Очередь", style="primary", emoji="📋", premium=premium),
        ],
        [
            text_button("Меню", style="primary", emoji="🏠", premium=premium),
            text_button("Логи", style="primary", emoji="📜", premium=premium),
        ],
    ]


def main_buttons(*, enabled: bool, premium: bool = True):
    toggle_label = "Приостановить" if enabled else "Запустить"
    toggle_style = "danger" if enabled else "success"
    toggle_emoji = "⏸" if enabled else "▶️"
    return [
        [
            inline_button("Сейчас", b"ui:now", style="success", emoji="🚀", premium=premium),
            inline_button("Очередь", b"ui:queue", style="primary", emoji="📋", premium=premium),
        ],
        [
            inline_button("Обновить", b"ui:refresh", style="primary", emoji="🔄", premium=premium),
            inline_button("Собрать", b"ui:build", style="success", emoji="🧩", premium=premium),
        ],
        [
            inline_button("Источники", b"ui:sources", style="primary", emoji="📡", premium=premium),
            inline_button("Расписание", b"ui:times", style="primary", emoji="🕒", premium=premium),
        ],
        [
            inline_button("Настройки", b"ui:settings", style="primary", emoji="⚙️", premium=premium),
            inline_button("Логи", b"ui:logs", style="primary", emoji="📜", premium=premium),
        ],
        [inline_button(toggle_label, b"ui:toggle_enabled", style=toggle_style, emoji=toggle_emoji, premium=premium)],
    ]


def home_button(*, premium: bool = True):
    return inline_button("В меню", b"ui:home", style="primary", emoji="🏠", premium=premium)


def queue_buttons(*, premium: bool = True):
    return [
        [
            inline_button("Обновить очередь", b"ui:refresh", style="primary", emoji="🔄", premium=premium),
            inline_button("Собрать", b"ui:build", style="success", emoji="🧩", premium=premium),
        ],
        [home_button(premium=premium)],
    ]


def source_buttons(sources: list[str], *, premium: bool = True):
    rows = [
        [inline_button("Добавить источник", b"ui:source:add", style="success", emoji="➕", premium=premium)]
    ]
    rows.extend(
        [inline_button(f"Удалить {source}", f"ui:source:del:{index}".encode(), style="danger", emoji="🗑", premium=premium)]
        for index, source in enumerate(sources)
    )
    rows.append([home_button(premium=premium)])
    return rows


def schedule_buttons(slots: list[str], *, premium: bool = True):
    rows = [
        [inline_button("Добавить время", b"ui:time:add", style="success", emoji="➕", premium=premium)]
    ]
    rows.extend(
        [inline_button(f"Удалить {slot}", f"ui:time:del:{slot.replace(':', '')}".encode(), style="danger", emoji="🗑", premium=premium)]
        for slot in slots
    )
    rows.append(
        [inline_button("По умолчанию", b"ui:time:default", style="primary", emoji="♻️", premium=premium)]
    )
    rows.append([home_button(premium=premium)])
    return rows


def settings_buttons(*, enabled: bool, moderation: bool, premium: bool = True):
    enabled_label = "Остановить публикации" if enabled else "Запустить публикации"
    enabled_style = "danger" if enabled else "success"
    moderation_label = "Выключить модерацию" if moderation else "Включить модерацию"
    moderation_style = "danger" if moderation else "success"
    return [
        [inline_button(enabled_label, b"ui:toggle_enabled", style=enabled_style, emoji="⏯", premium=premium)],
        [inline_button(moderation_label, b"ui:toggle_moderation", style=moderation_style, emoji="🛡", premium=premium)],
        [inline_button("Конфигурация", b"ui:config", style="primary", emoji="ℹ️", premium=premium)],
        [home_button(premium=premium)],
    ]


def log_buttons(*, premium: bool = True):
    return [
        [
            inline_button("Ошибки", b"ui:logs:errors", style="danger", emoji="🚨", premium=premium),
            inline_button("Публикации", b"ui:logs:publisher", style="primary", emoji="📤", premium=premium),
        ],
        [
            inline_button("Планировщик", b"ui:logs:scheduler", style="primary", emoji="🕒", premium=premium),
            inline_button("Все", b"ui:logs:all", style="primary", emoji="📚", premium=premium),
        ],
        [inline_button("Скачать TXT", b"ui:logs:download", style="success", emoji="📥", premium=premium)],
        [
            inline_button("Обновить", b"ui:logs", style="primary", emoji="🔄", premium=premium),
            home_button(premium=premium),
        ],
    ]


_STATUS_LABELS = {
    "pending": "⏳ ожидает",
    "publishing": "📤 публикуется",
    "posted": "✅ опубликован",
    "failed": "❌ ошибка",
    "skipped": "⏭ пропущен",
}


def queue_text(rows) -> str:
    if not rows:
        return "📭 <b>Очередь пуста</b>"
    lines = ["📋 <b>Очередь публикаций</b>", ""]
    for slot, source, message_id, _score, _is_fallback, status in rows:
        safe_source = escape(str(source))
        username = str(source).lstrip("@")
        link = f"https://t.me/{escape(username, quote=True)}/{int(message_id)}"
        state = _STATUS_LABELS.get(status, escape(str(status)))
        lines.append(f"🕒 <b>{escape(slot)}</b> · <a href=\"{link}\">{safe_source}/{int(message_id)}</a> · {state}")
    return "\n".join(lines)


def dashboard_text(*, enabled: bool, counts: dict[str, int], slots: list[str]) -> str:
    state = "🟢 <b>Бот работает</b>" if enabled else "🔴 <b>Бот приостановлен</b>"
    schedule = " · ".join(escape(slot) for slot in slots) or "не задано"
    return "\n".join(
        [
            "🎛 <b>Панель управления</b>",
            state,
            "",
            f"✅ Опубликовано: <b>{counts.get('posted', 0)}</b>",
            f"⏳ Ожидает: <b>{counts.get('pending', 0)}</b>",
            f"📤 Публикуется: <b>{counts.get('publishing', 0)}</b>",
            f"❌ Ошибки: <b>{counts.get('failed', 0)}</b>",
            "",
            f"🕒 Расписание: <b>{schedule}</b>",
        ]
    )
