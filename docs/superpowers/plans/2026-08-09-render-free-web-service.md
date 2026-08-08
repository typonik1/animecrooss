# Render Free Web Service Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Telegram crossposter boot reliably as a Render Free Web Service and expose a health endpoint for uptime monitoring.

**Architecture:** Telethon clients are constructed inside the active asyncio loop. A standard-library HTTP server binds `$PORT`, and the reader uses an environment-backed StringSession on Render with a local SQLite session fallback.

**Tech Stack:** Python 3.13, asyncio, Telethon 1.36, pytest, Render Web Service.

## Global Constraints

- Never commit or print Telegram credentials or session strings.
- `GET /health` must return HTTP 200 while the process is alive.
- Local file sessions remain supported for development.
- Render startup must not prompt for a phone number.

---

### Task 1: Async client lifecycle regression

**Files:**
- Modify: `main.py`
- Test: `tests/test_render_runtime.py`

**Interfaces:**
- Produces: `create_clients() -> tuple[TelegramClient, TelegramClient]`

- [ ] Write a test whose fake client calls `asyncio.get_running_loop()` during construction.
- [ ] Run the test and confirm it fails because `create_clients` does not exist.
- [ ] Move client construction into async `create_clients` and pass clients into scheduler/notify.
- [ ] Run the regression and full tests.

### Task 2: Render health server

**Files:**
- Create: `health.py`
- Modify: `main.py`, `config.py`
- Test: `tests/test_render_runtime.py`

**Interfaces:**
- Produces: `health.handle_connection(reader, writer)` and `health.start(port)`.

- [ ] Write a failing test that expects an HTTP 200 response containing `ok`.
- [ ] Implement a minimal asyncio HTTP server bound to `0.0.0.0:$PORT`.
- [ ] Start it alongside the Telegram scheduler and bot update loop.
- [ ] Run the regression and full tests.

### Task 3: Persistent authorization and deployment config

**Files:**
- Modify: `config.py`, `.env.example`, `README.md`
- Create: `.python-version`, `render.yaml`
- Test: `tests/test_render_runtime.py`

**Interfaces:**
- Consumes: `TELEGRAM_SESSION_STRING`, `PORT`.
- Produces: `reader_session()` returning `StringSession` or the local session name.

- [ ] Write failing tests for StringSession selection and local fallback.
- [ ] Implement session selection without exposing its value.
- [ ] Pin Python 3.13 and define Render build/start/health settings.
- [ ] Document session export, Render environment variables, and UptimeRobot URL.
- [ ] Run compile, full pytest, secret scan, commit, and push `main`.
