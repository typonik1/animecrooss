# Render Free Web Service Design

## Goal

Run the existing Telethon crossposter as a Render Free Web Service that exposes a health endpoint for an uptime monitor and starts reliably on Render's current Python runtime.

## Architecture

- Construct both Telethon clients inside the running asyncio event loop.
- Bind a small standard-library HTTP server to `0.0.0.0:$PORT`; `GET /health` returns HTTP 200.
- Use a Telethon `StringSession` from `TELEGRAM_SESSION_STRING` on Render, with the existing file session as the local fallback.
- Use an in-memory bot session because bot-token authorization does not need persistent local state.
- Pin Python 3.13 in `.python-version` to avoid untested dependency behavior on Render's Python 3.14 default.

## Data and Failure Behavior

The free Render filesystem is ephemeral. The user authorization survives through `TELEGRAM_SESSION_STRING`; SQLite queue and deduplication state can reset after redeploy. Startup without a user session in a non-interactive environment fails with a clear configuration message instead of waiting for console input.

## Verification

- Regression test proves Telethon clients are constructed with a running event loop.
- Health handler test verifies a valid HTTP 200 response.
- Session-selection tests cover StringSession and local file fallback.
- Full pytest and compile checks run before commit.
