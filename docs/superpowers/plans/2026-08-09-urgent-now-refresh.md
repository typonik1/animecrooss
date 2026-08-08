# Urgent Now and Queue Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish urgent fresh videos without touching scheduled slots and refresh only pending daily queue entries from Telegram.

**Architecture:** The builder returns an in-memory urgent candidate, while the publisher accepts an optional queue identifier. Storage deletes only pending daily entries before a normal schedule rebuild. An owner-only inline callback invokes the refresh flow.

**Tech Stack:** Python, Telethon, SQLite, pytest.

## Global Constraints

- `/now` must never read, consume, insert, or replace a scheduled queue slot.
- Manual and scheduled publication both mark a successful source video as posted.
- Refresh must not alter `posted`, `skipped`, or `failed` queue rows.
- Selection remains fresh-only, duplicate-safe, and source-balanced.

---

### Task 1: Queue-independent urgent publishing

**Files:**
- Modify: `publisher.py`
- Modify: `admin.py`
- Test: `tests/test_urgent_controls.py`

**Interfaces:**
- Consumes: `builder.collect(reader, 1) -> list[dict]`
- Produces: `publisher.publish(reader, bot, item, queue_id: int | None = None) -> bool`

- [ ] **Step 1: Write failing tests**

```python
async def test_now_publishes_selected_item_without_queue_id():
    item = {"source": "@a", "message_id": 1, "file_uid": "u", "fingerprint": "fp"}
    assert await publisher.publish(reader, bot, item) is True
    assert statuses == []
    assert posted == [("@a", 1, "u", "fp")]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m pytest tests/test_urgent_controls.py::test_publisher_does_not_update_queue_for_urgent_item -q`

Expected: FAIL because `publisher.publish` requires a queue identifier from `item["id"]`.

- [ ] **Step 3: Implement minimal optional queue-status handling**

```python
async def publish(reader, bot, item, queue_id=None):
    queue_id = queue_id if queue_id is not None else item.get("id")
    # Call storage.set_status only when queue_id is not None.
```

- [ ] **Step 4: Run urgent publishing tests**

Run: `python3 -m pytest tests/test_urgent_controls.py -q`

Expected: PASS.

### Task 2: Pending-only refresh storage operation

**Files:**
- Modify: `storage.py`
- Test: `tests/test_urgent_controls.py`

**Interfaces:**
- Produces: `storage.clear_pending(day: str) -> int`
- Consumes: the existing `queue` statuses.

- [ ] **Step 1: Write failing test**

```python
def test_clear_pending_keeps_queue_history(tmp_path, monkeypatch):
    # Insert one pending and one posted row for the same day.
    assert storage.clear_pending("2026-08-09") == 1
    assert remaining_statuses() == ["posted"]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m pytest tests/test_urgent_controls.py::test_clear_pending_keeps_published_queue_history -q`

Expected: FAIL because `clear_pending` is undefined.

- [ ] **Step 3: Implement targeted deletion**

```python
def clear_pending(day):
    with _db() as db:
        result = db.execute("DELETE FROM queue WHERE day=? AND status='pending'", (day,))
        db.commit()
    return result.rowcount
```

- [ ] **Step 4: Run the storage test**

Run: `python3 -m pytest tests/test_urgent_controls.py::test_clear_pending_keeps_published_queue_history -q`

Expected: PASS.

### Task 3: Owner-only `/now` and inline refresh button

**Files:**
- Modify: `admin.py`
- Test: `tests/test_urgent_controls.py`

**Interfaces:**
- Consumes: `builder.collect(reader, 1)`, `storage.clear_pending(storage.today())`, and `builder.build_day(reader)`.
- Produces: `/now` reply text and `🔄 Обновить очередь` callback behavior.

- [ ] **Step 1: Write failing tests**

```python
async def test_now_collects_when_schedule_has_no_pending(monkeypatch):
    monkeypatch.setattr(builder, "collect", selected_one)
    # Dispatch an owner /now event.
    assert published_item == selected_item

async def test_refresh_callback_clears_pending_then_builds(monkeypatch):
    # Dispatch owner callback data 'refresh_queue'.
    assert calls == ["clear", "build"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_urgent_controls.py::test_now_selects_and_publishes_without_queue tests/test_urgent_controls.py::test_refresh_only_clears_pending_then_rebuilds -q`

Expected: FAIL because no callback handler exists and `/now` reads only scheduled queue rows.

- [ ] **Step 3: Implement commands and button**

```python
@bot.on(events.NewMessage(pattern=r"^/now"))
async def now(event):
    items = await builder.collect(reader, 1)
    if not items:
        await event.reply("Свежих уникальных роликов не найдено")
        return
    await event.reply("Опубликовано" if await publisher.publish(reader, bot, items[0]) else "Ошибка публикации")

@bot.on(events.CallbackQuery(data=b"refresh_queue"))
async def refresh_queue(event):
    storage.clear_pending(storage.today())
    await builder.build_day(reader)
```

- [ ] **Step 4: Run command tests**

Run: `python3 -m pytest tests/test_urgent_controls.py -q`

Expected: PASS.

### Task 4: Help text and release verification

**Files:**
- Modify: `admin.py`
- Test: `tests/test_urgent_controls.py`

- [ ] **Step 1: Add the visible refresh command and button guidance to help**

```python
HELP = "... /queue /refresh /now ..."
```

- [ ] **Step 2: Run complete verification**

Run: `python3 -m pytest -q && python3 -m compileall -q . && git diff --check`

Expected: all tests pass, compilation succeeds, and the diff has no whitespace errors.

- [ ] **Step 3: Commit and push**

```bash
git add admin.py publisher.py storage.py tests docs/superpowers
git commit -m "feat: add urgent posting and queue refresh"
git push origin main
```
