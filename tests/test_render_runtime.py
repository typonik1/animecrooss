import ast
import asyncio
from pathlib import Path
from types import SimpleNamespace


def test_main_does_not_construct_telegram_clients_at_import_time():
    tree = ast.parse(Path("main.py").read_text())
    calls = []
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            value = node.value
            if isinstance(value, ast.Call) and isinstance(value.func, ast.Name):
                if value.func.id == "TelegramClient":
                    calls.append(value)
    assert calls == []


def test_health_handler_returns_http_200():
    import health

    class Writer:
        def __init__(self):
            self.data = b""
            self.closed = False

        def write(self, data):
            self.data += data

        async def drain(self):
            pass

        def close(self):
            self.closed = True

        async def wait_closed(self):
            pass

    async def check():
        reader = asyncio.StreamReader()
        reader.feed_data(b"GET /health HTTP/1.1\r\nHost: test\r\n\r\n")
        reader.feed_eof()
        writer = Writer()
        await health.handle_connection(reader, writer)
        assert writer.data.startswith(b"HTTP/1.1 200 OK")
        assert b'"ok":true' in writer.data
        assert writer.closed

    asyncio.run(check())


def test_reader_session_uses_string_session(monkeypatch):
    import main

    monkeypatch.setattr(main.config, "TELEGRAM_SESSION_STRING", "secret-session")
    sentinel = SimpleNamespace(kind="string")
    monkeypatch.setattr(main, "StringSession", lambda value: sentinel if value == "secret-session" else None)
    assert main.reader_session() is sentinel


def test_reader_session_falls_back_to_local_name(monkeypatch):
    import main

    monkeypatch.setattr(main.config, "TELEGRAM_SESSION_STRING", "")
    monkeypatch.setattr(main.config, "SESSION_NAME", "anime_reader")
    assert main.reader_session() == "anime_reader"
