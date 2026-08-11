"""In-memory, owner-visible logging with bounded automatic error alerts."""

import asyncio
import logging
import re
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from html import escape
from typing import Awaitable, Callable, Iterable

import config


_SECRET_PATTERNS = (
    re.compile(r"(?i)\b(BOT_TOKEN|API_HASH|ROUTERAI_API_KEY|GEMINI_API_KEY|TELEGRAM_SESSION_STRING)\s*[=:]\s*\S+"),
    re.compile(r"\b\d{5,}:[A-Za-z0-9_-]{12,}\b"),
)


def redact(value: str) -> str:
    result = str(value)
    for pattern in _SECRET_PATTERNS:
        result = pattern.sub("[скрыто]", result)
    return result


@dataclass(frozen=True)
class LogEntry:
    timestamp: datetime
    levelno: int
    levelname: str
    logger: str
    message: str


class LogBuffer(logging.Handler):
    """A logging handler that retains only a safe, finite recent history."""

    def __init__(
        self,
        max_entries: int = 800,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        super().__init__(level=logging.INFO)
        self._entries: deque[LogEntry] = deque(maxlen=max_entries)
        self._now = now or (lambda: datetime.now(config.TZ))

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = redact(record.getMessage())
            if record.exc_info:
                formatted = logging.Formatter().formatException(record.exc_info)
                message = f"{message}\n{redact(formatted)}"
            self._entries.append(
                LogEntry(
                    timestamp=self._now(),
                    levelno=record.levelno,
                    levelname=record.levelname,
                    logger=record.name,
                    message=message,
                )
            )
        except Exception:
            # Logging must never take the application down.
            pass

    def snapshot(self) -> list[LogEntry]:
        return list(self._entries)

    def filtered(self, category: str) -> list[LogEntry]:
        entries = self.snapshot()
        if category == "errors":
            return [entry for entry in entries if entry.levelno >= logging.ERROR]
        if category == "publisher":
            return [entry for entry in entries if entry.logger.split(".", 1)[0] in {"publisher", "builder"}]
        if category == "scheduler":
            return [entry for entry in entries if entry.logger.split(".", 1)[0] in {"main", "reactions"}]
        return entries

    def _lines(self, category: str) -> list[str]:
        return [
            f"{entry.timestamp:%d.%m %H:%M:%S} | {entry.levelname} | {entry.logger} | {entry.message}"
            for entry in self.filtered(category)
        ]

    def render_text(self, category: str = "all") -> str:
        lines = self._lines(category)
        return "\n".join(lines) if lines else "Записей пока нет"

    def render_html(self, category: str = "all", limit: int = 3900) -> str:
        lines = [escape(line) for line in self._lines(category)]
        if not lines:
            return "📭 <b>Записей пока нет</b>"
        header = "📜 <b>Последние события</b>\n<pre>"
        footer = "</pre>"
        selected: deque[str] = deque()
        size = len(header) + len(footer)
        for line in reversed(lines):
            extra = len(line) + (1 if selected else 0)
            if size + extra > limit:
                if not selected:
                    available = max(0, limit - size)
                    if available:
                        selected.appendleft(
                            line[: max(0, available - 1)] + ("…" if len(line) > available else "")
                        )
                break
            selected.appendleft(line)
            size += extra
        return header + "\n".join(selected) + footer


class OwnerAlertHandler(logging.Handler):
    """Deliver ERROR/CRITICAL records once per dedupe window to every owner."""

    def __init__(
        self,
        *,
        send: Callable[[int, str], Awaitable[object]],
        owner_ids: Callable[[], Iterable[int]],
        dedupe_sec: float = 300,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        super().__init__(level=logging.ERROR)
        self._send = send
        self._owner_ids = owner_ids
        self._dedupe_sec = dedupe_sec
        self._monotonic = monotonic
        self._last_sent: dict[tuple[str, int, str], float] = {}

    async def _deliver(self, owner_ids: list[int], text: str) -> None:
        for owner_id in owner_ids:
            try:
                await self._send(owner_id, text)
            except Exception:
                # Do not log this error: that would recursively create alerts.
                pass

    def emit(self, record: logging.LogRecord) -> None:
        if record.levelno < logging.ERROR:
            return
        try:
            message = redact(record.getMessage())
            key = (record.name, record.levelno, message)
            now = self._monotonic()
            previous = self._last_sent.get(key)
            if previous is not None and now - previous < self._dedupe_sec:
                return
            self._last_sent[key] = now
            expired_before = now - self._dedupe_sec
            self._last_sent = {item: sent for item, sent in self._last_sent.items() if sent >= expired_before}
            owners = sorted(set(self._owner_ids()))
            if not owners:
                return
            text = (
                "🚨 <b>Ошибка бота</b>\n"
                f"<b>{escape(record.name)}</b> · {escape(record.levelname)}\n"
                f"<code>{escape(message[:3000])}</code>"
            )
            asyncio.get_running_loop().create_task(self._deliver(owners, text))
        except Exception:
            pass


BUFFER = LogBuffer()


def install_buffer(root: logging.Logger | None = None) -> LogBuffer:
    root = root or logging.getLogger()
    if BUFFER not in root.handlers:
        root.addHandler(BUFFER)
    return BUFFER


def install_owner_alerts(bot, root: logging.Logger | None = None) -> OwnerAlertHandler:
    root = root or logging.getLogger()

    async def send(owner_id: int, text: str):
        return await bot.send_message(owner_id, text, parse_mode="html", link_preview=False)

    handler = OwnerAlertHandler(send=send, owner_ids=lambda: config.OWNER_IDS)
    root.addHandler(handler)
    return handler
