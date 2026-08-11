# Telegram Control Panel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an owner-only, button-first Telegram administration panel with Bot API 9.4 colors, premium emoji, editable navigation screens, log browsing/export, and throttled critical-error alerts.

**Architecture:** Upgrade Telethon to 1.44 and keep Telegram interaction on the existing MTProto clients. Add `telegram_ui.py` as a pure presentation/button boundary, `botlogs.py` as a bounded logging/alert boundary, and let `admin.py` route existing business actions into those units. `main.py` owns startup wiring only.

**Tech Stack:** Python 3.10, Telethon 1.44.0, asyncio, stdlib logging/deque/tempfile, SQLite storage, pytest 8.3.3.

## Global Constraints

- Keep all existing slash commands operational.
- Only `config.OWNER_IDS` may view logs or use control-panel actions.
- Default emoji set short name is exactly `ReactionsEmojiVK`.
- Premium emoji failures must retry with Unicode fallback buttons.
- Log buffer capacity is exactly 800 entries.
- Duplicate critical alerts are suppressed for exactly 300 seconds.
- No environment value, bot token, session string, or exception local may be included in a log response.
- Preserve existing `/now` queue isolation, timeout, and concurrency semantics.

---

### Task 1: Styled buttons and premium emoji presentation

**Files:**
- Create: `telegram_ui.py`
- Create: `tests/test_telegram_ui.py`
- Modify: `config.py`
- Modify: `requirements.txt`

**Interfaces:**
- Produces: `async load_emoji_set(reader) -> int`
- Produces: `set_emoji_icons(mapping: dict[str, int]) -> None`
- Produces: `inline_button(label: str, data: bytes, *, style: str | None, emoji: str, premium: bool = True)`
- Produces: `quick_keyboard(*, premium: bool = True) -> list[list[Button]]`
- Produces: `main_buttons(enabled: bool, *, premium: bool = True) -> list[list[Button]]`
- Produces: `queue_buttons(*, premium: bool = True)`, `source_buttons(sources, ...)`, `schedule_buttons(slots, ...)`, `settings_buttons(enabled, moderation, ...)`, `log_buttons(...)`
- Produces: `queue_text(rows: list[tuple]) -> str` and `dashboard_text() -> str`

- [ ] **Step 1: Pin the supported Telethon version and configuration**

Change `requirements.txt` from `telethon==1.36.0` to `telethon==1.44.0`. Add:

```python
UI_EMOJI_SET = os.getenv("UI_EMOJI_SET", "ReactionsEmojiVK")
```

to `config.py`.

- [ ] **Step 2: Write failing styled-button tests**

Create tests that call:

```python
telegram_ui.set_emoji_icons({"🚀": 123456})
button = telegram_ui.inline_button(
    "Сейчас", b"ui:now", style="success", emoji="🚀"
)
assert button.text == "Сейчас"
assert button.data == b"ui:now"
assert button.style.bg_success is True
assert button.style.icon == 123456
```

Also assert that no loaded ID yields text `🚀 Сейчас`, and verify callback grids for `ui:home`, `ui:queue`, `ui:refresh`, `ui:sources`, `ui:times`, `ui:settings`, and `ui:logs`.

- [ ] **Step 3: Run the tests to verify RED**

Run:

```powershell
python -m pytest -q tests/test_telegram_ui.py
```

Expected: collection failure because `telegram_ui` does not exist.

- [ ] **Step 4: Implement emoji loading and button factories**

Use:

```python
from telethon import Button, functions, types

_emoji_icons: dict[str, int] = {}

async def load_emoji_set(reader) -> int:
    sticker_set = await reader(
        functions.messages.GetStickerSetRequest(
            stickerset=types.InputStickerSetShortName(config.UI_EMOJI_SET),
            hash=0,
        )
    )
    mapping = {}
    for document in sticker_set.documents:
        for attribute in document.attributes:
            if isinstance(attribute, types.DocumentAttributeCustomEmoji):
                mapping.setdefault(attribute.alt, document.id)
    set_emoji_icons(mapping)
    return len(mapping)
```

The button factory must pass `style` and `icon` to Telethon 1.44. If no icon is known or `premium=False`, prefix the label with the Unicode fallback.

- [ ] **Step 5: Implement presentation grids and localized queue text**

Callback data must stay below 64 bytes. Removal callbacks use source indexes and compact `HHMM` time values. Keep all presentation functions deterministic and side-effect free.

- [ ] **Step 6: Run Task 1 tests**

Run:

```powershell
python -m pytest -q tests/test_telegram_ui.py tests/test_urgent_controls.py
```

Expected: PASS.

- [ ] **Step 7: Commit Task 1**

```powershell
git add requirements.txt config.py telegram_ui.py tests/test_telegram_ui.py
git commit -m "feat: add styled Telegram control panel buttons"
```

---

### Task 2: Bounded log buffer, exports, and critical alerts

**Files:**
- Create: `botlogs.py`
- Create: `tests/test_botlogs.py`

**Interfaces:**
- Produces: `install(capacity: int = 800) -> LogBufferHandler`
- Produces: `bind_alerts(bot, loop=None) -> None`
- Produces: `recent(kind: str = "all", limit: int = 40) -> list[LogEntry]`
- Produces: `render(kind: str = "all", limit: int = 40) -> str`
- Produces: `export_text() -> str`
- Consumes lazily: `telegram_ui.log_alert_buttons()` when sending an alert.

- [ ] **Step 1: Write failing log-buffer tests**

Cover a three-entry handler with four emitted records and assert only the last three remain. Assert:

```python
assert [entry.message for entry in botlogs.recent("errors")] == ["upload failed"]
assert "&lt;token-like-text&gt;" in botlogs.render("all")
assert "upload failed" in botlogs.export_text()
```

Add an async fake bot test proving one `ERROR` alerts all configured owners once, the identical error inside 300 seconds is suppressed, and a `WARNING` produces no alert.

- [ ] **Step 2: Run tests to verify RED**

```powershell
python -m pytest -q tests/test_botlogs.py
```

Expected: collection failure because `botlogs` does not exist.

- [ ] **Step 3: Implement `LogEntry` and `LogBufferHandler`**

Use an immutable dataclass and `collections.deque(maxlen=capacity)`. Store only `record.getMessage()`, not `record.__dict__`, arguments, or exception locals. Format exceptions through the configured formatter and cap any individual rendered message to 1200 characters.

- [ ] **Step 4: Implement filters and Telegram rendering**

Filters are:

```python
errors = entry.levelno >= logging.ERROR
publisher = entry.logger in {"publisher", "builder", "admin"}
scheduler = entry.logger in {"main", "reactions"}
```

Escape every rendered line with `html.escape` and keep the final Telegram text below 3800 characters.

- [ ] **Step 5: Implement throttled owner alerts**

Bind the running loop after bot startup. The handler schedules an alert only for `ERROR`/`CRITICAL`. Use `(logger, levelno, message)` and `time.monotonic()` for the 300-second duplicate window. The internal send coroutine catches exceptions without logging them.

- [ ] **Step 6: Run Task 2 tests**

```powershell
python -m pytest -q tests/test_botlogs.py
```

Expected: PASS.

- [ ] **Step 7: Commit Task 2**

```powershell
git add botlogs.py tests/test_botlogs.py
git commit -m "feat: add owner log delivery and critical alerts"
```

---

### Task 3: Button-first admin workflows

**Files:**
- Modify: `admin.py`
- Create: `tests/test_admin_panel.py`
- Modify: `tests/test_urgent_controls.py`

**Interfaces:**
- Consumes: all presentation factories from `telegram_ui.py`
- Consumes: `botlogs.render()` and `botlogs.export_text()`
- Produces: `normalize_source(value: str) -> str`
- Produces: `normalize_time(value: str) -> str | None`
- Produces: `async show_home(event, *, edit: bool = False) -> None`
- Produces: `async handle_panel_action(event, reader, bot) -> None`
- Produces: `async handle_pending_input(event, reader) -> bool`

- [ ] **Step 1: Write failing validation and routing tests**

Assert:

```python
assert admin.normalize_source("https://t.me/Anitik_edits") == "@Anitik_edits"
assert admin.normalize_time("09:05") == "09:05"
assert admin.normalize_time("25:61") is None
```

Use fake callback events to verify `ui:queue`, `ui:sources`, `ui:times`, `ui:settings`, and `ui:logs` edit the message with the correct button grids. Verify non-owners produce no panel data.

- [ ] **Step 2: Run tests to verify RED**

```powershell
python -m pytest -q tests/test_admin_panel.py
```

Expected: failures because the normalization and panel-routing functions do not exist.

- [ ] **Step 3: Implement persistent keyboard and home panel**

`/start` and `/menu` send the quick keyboard followed by the inline dashboard. Add exact-text handlers for `🚀 Сейчас`, `📋 Очередь`, `🏠 Меню`, and `📜 Логи`. Each handler calls the same function as the equivalent callback or slash command.

- [ ] **Step 4: Implement single callback router**

Register one `events.CallbackQuery(pattern=b"^ui:")` handler. Call `event.answer()` before every long action. For premium-button send/edit exceptions, retry the same presentation with `premium=False`.

- [ ] **Step 5: Implement source and time input flows**

Keep `_pending_inputs: dict[int, str]`. `ui:source:add` and `ui:time:add` set a state and prompt for one message. A private owner `NewMessage` handler validates the next message, mutates storage, clears state on success, and reopens the relevant screen. `/cancel` clears state.

- [ ] **Step 6: Implement logs and TXT download**

Log callbacks edit the current screen using `botlogs.render`. Download writes `botlogs.export_text()` to a named UTF-8 temporary file, sends it to `event.sender_id`, and removes it in `finally`.

- [ ] **Step 7: Set concise Telegram bot commands**

At registration/startup, call the MTProto bot-command setter with `/start`, `/menu`, `/now`, `/queue`, and `/logs`, using Russian descriptions. Failure is logged as a warning and does not stop startup.

- [ ] **Step 8: Run Task 3 tests**

```powershell
python -m pytest -q tests/test_admin_panel.py tests/test_urgent_controls.py
```

Expected: PASS.

- [ ] **Step 9: Commit Task 3**

```powershell
git add admin.py tests/test_admin_panel.py tests/test_urgent_controls.py
git commit -m "feat: add button-first Telegram admin workflows"
```

---

### Task 4: Startup integration and full verification

**Files:**
- Modify: `main.py`
- Modify: `tests/test_render_runtime.py`
- Test: all `tests/`

**Interfaces:**
- Consumes: `botlogs.install()`, `botlogs.bind_alerts(bot, loop)`
- Consumes: `telegram_ui.load_emoji_set(reader)`

- [ ] **Step 1: Write the failing startup integration test**

Patch the integration functions and assert startup ordering is:

```text
logging configured → log handler installed → reader started → emoji set loaded
→ bot started → admin registered → alerts bound → background tasks gathered
```

Also assert `requirements.txt` pins `telethon==1.44.0`.

- [ ] **Step 2: Run the integration test to verify RED**

```powershell
python -m pytest -q tests/test_render_runtime.py
```

Expected: FAIL because startup does not install logs/load emoji/bind alerts.

- [ ] **Step 3: Wire startup**

Install `botlogs` immediately after `logging.basicConfig`. After `reader.start()`, load the emoji set with a bounded timeout and warning-only fallback. After `bot.start()`, bind alerts to `asyncio.get_running_loop()` before the startup notification.

- [ ] **Step 4: Run focused tests**

```powershell
python -m pytest -q tests/test_telegram_ui.py tests/test_botlogs.py tests/test_admin_panel.py tests/test_render_runtime.py tests/test_urgent_controls.py
```

Expected: PASS.

- [ ] **Step 5: Run complete verification**

```powershell
python -m pytest -q
python -m py_compile main.py admin.py telegram_ui.py botlogs.py publisher.py storage.py config.py
git diff --check
```

Expected: every command exits `0`.

- [ ] **Step 6: Run rollback verification on a separate copy**

Run the generated `ROLLBACK.sh` against a separate modified clone, assert `git diff --exit-code` succeeds there, and rerun the original baseline test suite.

- [ ] **Step 7: Commit and push integration**

```powershell
git add main.py tests/test_render_runtime.py
git commit -m "feat: activate Telegram control panel"
git push origin main
```

- [ ] **Step 8: Verify deployment**

Assert local and remote `main` SHAs match, `https://animecrooss.onrender.com/health` returns `200 {"ok":true}`, and the owner chat shows the persistent keyboard plus styled inline dashboard after `/start`.
