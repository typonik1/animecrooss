import asyncio
import time


def _item():
    return {
        "id": 41,
        "source": "@source",
        "message_id": 7,
        "file_uid": "uid-7",
        "fingerprint": "size:7",
    }


def test_publish_converts_source_rpc_exception_to_failed_status(monkeypatch):
    import publisher

    class Reader:
        async def get_messages(self, source, ids):
            raise ConnectionError("source disconnected")

    statuses = []
    monkeypatch.setattr(publisher.storage, "set_status", lambda *args: statuses.append(args))

    assert asyncio.run(publisher.publish(Reader(), object(), _item())) is False
    assert statuses == [(41, "failed")]


def test_publish_times_out_a_stalled_source_rpc(monkeypatch):
    import config
    import publisher

    class Reader:
        async def get_messages(self, source, ids):
            await asyncio.sleep(0.1)
            return None

    statuses = []
    monkeypatch.setattr(config, "PUBLISH_TIMEOUT_SEC", 0.01, raising=False)
    monkeypatch.setattr(publisher.storage, "set_status", lambda *args: statuses.append(args))

    started = time.monotonic()
    assert asyncio.run(publisher.publish(Reader(), object(), _item())) is False
    elapsed = time.monotonic() - started

    assert elapsed < 0.08
    assert statuses == [(41, "failed")]
