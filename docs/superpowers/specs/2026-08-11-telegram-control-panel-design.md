# Telegram Control Panel Design

## Goal

Replace command-first administration with an owner-only Telegram control panel built from persistent quick buttons and editable inline screens. Preserve every existing slash command as a compatibility path. Add styled buttons, premium custom emoji, manual log browsing/export, and throttled critical-error alerts.

## Chosen Approach

### Options considered

1. **Keep Telethon 1.36 and add Unicode-only buttons.** This is the smallest change, but it cannot provide the Bot API 9.4 button styles and custom emoji requested by the owner.
2. **Send styled menus through the HTTP Bot API while receiving updates through Telethon.** This exposes Bot API 9.4 immediately, but creates two Telegram transports for one bot and makes message editing/error handling needlessly fragile.
3. **Upgrade to Telethon 1.44 and use its native styled button support.** Telethon 1.44 exposes `Button.inline(..., style=..., icon=...)` and `Button.text(..., style=..., icon=...)`. This keeps one connection model, existing callback handling, and full color/custom-emoji support.

Option 3 is selected.

## Owner Experience

`/start`, `/menu`, or the persistent `🏠 Меню` button opens a compact dashboard. The first welcome response installs a persistent quick keyboard; the dashboard itself is an inline message that is edited in place so the chat does not fill with navigation messages.

### Persistent quick keyboard

```text
[ 🚀 Сейчас ]  [ 📋 Очередь ]
[ 🏠 Меню   ]  [ 📜 Логи    ]
```

### Main inline dashboard

```text
🎛 Управление публикациями

Статус: 🟢 работает / 🔴 на паузе
Сегодня: posted N · pending N · failed N · publishing N
Слоты: 10:00, 13:00, 18:00, 21:00

[ Сейчас ]      [ Очередь ]
[ Обновить ]    [ Собрать ]
[ Источники ]   [ Расписание ]
[ Настройки ]   [ Логи ]
[ Пауза / Запустить ]
```

Button styles:

- `success` (green): publish now, build, resume, confirmation actions;
- `primary` (blue): queue, refresh, navigation, sources, schedule, settings, logs;
- `danger` (red): pause, remove source, remove time slot;
- default: back/home and non-mutating secondary actions.

## Premium Emoji

At startup the reader loads the custom emoji set named by `UI_EMOJI_SET`, defaulting to `ReactionsEmojiVK`. Documents are indexed by the Unicode `alt` value from `DocumentAttributeCustomEmoji`. Each inline button asks for an icon matching its fallback emoji.

If the set cannot be fetched, an emoji is missing, or Telegram rejects a custom icon, the menu is rebuilt with ordinary Unicode emoji in its button labels. Navigation and actions must remain fully usable without Premium.

Telegram limits custom button emoji to eligible bots/owners. The owner account is expected to have Telegram Premium; the fallback prevents this requirement from becoming an availability dependency.

## Screens and Actions

### Queue

Shows direct source-post links and localized states:

- `ожидает` for `pending`;
- `публикуется` for `publishing`;
- `опубликован` for `posted`;
- `ошибка` for `failed`;
- `пропущен` for `skipped`.

Buttons: `🔄 Обновить очередь`, `🧱 Собрать недостающее`, `🏠 Главное меню`.

Long-running actions acknowledge the callback immediately, display an in-progress state, execute the existing business function, and then render the resulting screen.

### Sources

Displays the configured source channels. Buttons:

- `➕ Добавить источник` starts a one-message input flow accepting `@channel` or `https://t.me/channel`;
- one red remove button per source;
- `⬅️ Назад`.

The input flow validates the channel through the reader before changing storage. `/cancel` and `❌ Отмена` clear pending input state.

### Schedule

Displays current Moscow-time slots. Buttons:

- `➕ Добавить время` starts a one-message `HH:MM` input flow;
- one red remove button per existing slot;
- `♻️ По умолчанию` restores `10:00,13:00,18:00,21:00`;
- `⬅️ Назад`.

Input is strictly validated as a real 24-hour time. Slots remain sorted and unique.

### Settings

Contains owner-facing toggles rather than raw `/set` syntax:

- scheduler enabled/paused;
- moderation enabled/disabled;
- compact read-only configuration summary;
- `⬅️ Назад`.

Advanced `/set` remains available, but common operation does not depend on it.

### Logs

The process installs a bounded in-memory logging handler with 800 entries. Entries contain Moscow timestamp, level, logger name, and rendered message. The log screen never exposes environment variables, bot tokens, session strings, or exception locals.

Buttons:

- `❌ Ошибки` — `ERROR` and `CRITICAL`;
- `📤 Публикации` — `publisher`, queue-build and urgent-publication messages;
- `⏰ Планировщик` — scheduler/reaction messages;
- `📜 Все` — most recent entries;
- `📄 Скачать TXT` — full current ring buffer as a temporary UTF-8 file;
- `🔄 Обновить` and `🏠 Главное меню`.

Telegram messages are capped before the platform limit and HTML-escaped. TXT files are removed after sending.

## Critical Alerts

`ERROR` and `CRITICAL` records are sent automatically to every configured owner after the bot client is ready. The alert includes time, subsystem, concise message, and an `📜 Открыть логи` button.

Identical alerts are throttled for five minutes using `(logger, level, message)` as the key. Failures while sending an alert are swallowed inside the alert handler to prevent recursive logging loops. Warnings such as a successfully recovered Telethon reconnect do not trigger owner alerts.

## Architecture

### `telegram_ui.py`

- premium emoji-set loading and lookup;
- styled/fallback button factory;
- persistent keyboard;
- inline screen button grids;
- localized queue states;
- safe menu reply/edit helpers that retry without premium icons.

### `botlogs.py`

- bounded `logging.Handler`;
- filtering and Telegram-safe rendering;
- TXT export;
- owner alert binding and duplicate throttling.

### `admin.py`

- keeps existing command-compatible business actions;
- handles `ui:*` callback routing;
- owns pending one-message input state for sources and times;
- maps persistent button text to the same action functions;
- sets a small Telegram command list for `/start`, `/menu`, `/now`, `/queue`, and `/logs`.

### `main.py`

- installs the memory log handler immediately after base logging configuration;
- loads premium emoji after the reader starts;
- binds critical alert delivery after the bot starts.

## Error Handling

- Every callback is acknowledged immediately.
- Invalid owner input returns a precise correction and keeps the input flow active.
- Telegram edit failures caused by an unchanged message are ignored; other premium-button failures retry with fallback buttons.
- Long operations reuse the existing `/now`, queue refresh, queue build, publisher, and scheduler timeouts.
- Only configured owners can open panels, download logs, or mutate settings.

## Testing

1. Button factory produces green/blue/red `KeyboardButtonStyle` and uses loaded custom emoji IDs.
2. Missing emoji IDs produce ordinary Unicode fallback labels.
3. Main, queue, sources, schedule, settings, and logs screens expose the expected callback data.
4. Time input rejects invalid values and stores sorted unique valid values.
5. Source input normalizes links and validates through the reader.
6. Log buffer is bounded, filters correctly, HTML-escapes output, and exports UTF-8 text.
7. Critical alerts are owner-only and duplicate-throttled; warnings do not alert.
8. Existing slash-command, scheduler, queue, urgent-publication, reaction, and dedup tests remain green.

## Deployment

Pin `telethon==1.44.0`, run the full test suite and compile check, push to `main`, verify the remote SHA and Render `/health`, then verify `/start` displays the persistent keyboard and styled dashboard in the owner chat.
