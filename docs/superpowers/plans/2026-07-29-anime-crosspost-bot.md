# Anime Crosspost Bot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Telegram anime-edit crossposter that reads donor channels with a user session, enriches captions through RouterAI, and publishes automatically on a configurable Moscow-time schedule.

**Architecture:** A Telethon user client scans and downloads source videos; a separate Bot API client publishes to the target channel and handles owner-only commands. SQLite stores settings, queue state, and idempotency fingerprints. A 20-second scheduler builds the daily queue and publishes due slots.

**Tech Stack:** Python 3.11+, Telethon 1.36, python-dotenv, openai-compatible RouterAI API, SQLite, pytest.

## Global Constraints

- Secrets live only in local `.env`; never commit or print API credentials.
- Timezone is `Europe/Moscow`; default slots are `10:00,13:00,18:00,21:00`.
- Preserve fallback parsing and publishing when the AI provider is unavailable.
- Filter ads, non-video media, duration/size limits, and duplicate files/messages.
- Automatic publishing is enabled by default; `/pause` and `/resume` remain available.

### Task 1: Project scaffolding and configuration

**Files:**
- Create: `.gitignore`, `.env.example`, `requirements.txt`, `README.md`, `config.py`

- [ ] Add dependency pins and ignore local sessions, database, downloads, and secrets.
- [ ] Implement environment parsing for Telegram, target channel, owner, RouterAI base URL/model/key, database and download paths.
- [ ] Document first-run login, bot admin permissions, `/id`, source subscription, and scheduled operation.

### Task 2: Storage and filtering primitives

**Files:**
- Create: `storage.py`, `filters.py`
- Test: `tests/test_storage_filters.py`

- [ ] Write tests for settings defaults, duplicate detection by message/file/fingerprint, ad detection, and video constraints.
- [ ] Implement SQLite schema, settings accessors, queue operations, and posted idempotency records.
- [ ] Implement Telegram document-video detection, activity scoring, fingerprints, and conservative ad filters.

### Task 3: AI enrichment, candidate builder, and publisher

**Files:**
- Create: `enrich.py`, `builder.py`, `publisher.py`
- Test: `tests/test_enrich.py`

- [ ] Test deterministic anime emoji selection, fallback caption parsing, and caption formatting without AI.
- [ ] Implement RouterAI-compatible async JSON extraction with timeout/error fallback and configurable model/base URL.
- [ ] Implement fresh-then-archive candidate collection and safe media download/send/cleanup.

### Task 4: Admin commands and scheduler

**Files:**
- Create: `admin.py`, `main.py`
- Test: `tests/test_scheduler_helpers.py`

- [ ] Test slot parsing and due-slot selection helpers without connecting to Telegram.
- [ ] Implement owner-only private commands for sources, schedule, queue, build, skip, now, settings, pause/resume, and id.
- [ ] Implement startup, daily queue build, scheduled publication, notifications, fallback replacement, and reconnect-friendly loop.

### Task 5: Verification and operational handoff

**Files:**
- Modify: `README.md`

- [ ] Run `python -m compileall`, `pytest`, and a no-network storage/enrichment smoke test using a temporary DB.
- [ ] Check the repository contains no secret values and report exact run commands plus Telegram setup steps.
- [ ] Commit the implementation as one coherent local commit after verification.
