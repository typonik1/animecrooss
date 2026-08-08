import asyncio
from types import SimpleNamespace

import admin
import config
import main


def test_parse_owner_ids_supports_list_and_legacy_value():
    assert config.parse_owner_ids("111, 222", "333") == {111, 222, 333}


def test_admin_authorizes_any_configured_owner(monkeypatch):
    monkeypatch.setattr(config, "OWNER_IDS", {111, 222})
    assert admin.is_owner(SimpleNamespace(is_private=True, sender_id=222))
    assert not admin.is_owner(SimpleNamespace(is_private=True, sender_id=999))
    assert not admin.is_owner(SimpleNamespace(is_private=False, sender_id=222))


def test_reader_account_is_added_to_owner_set(monkeypatch):
    monkeypatch.setattr(config, "OWNER_IDS", {111})

    class Reader:
        async def get_me(self):
            return SimpleNamespace(id=222)

    asyncio.run(main.add_reader_owner(Reader()))
    assert config.OWNER_IDS == {111, 222}


def test_notify_sends_to_every_owner_and_survives_one_failure(monkeypatch):
    monkeypatch.setattr(config, "OWNER_IDS", {111, 222})

    class Bot:
        def __init__(self):
            self.sent = []

        async def send_message(self, owner_id, text, **kwargs):
            self.sent.append(owner_id)
            if owner_id == 111:
                raise RuntimeError("blocked")

    bot = Bot()
    asyncio.run(main.notify(bot, "test"))
    assert set(bot.sent) == {111, 222}
