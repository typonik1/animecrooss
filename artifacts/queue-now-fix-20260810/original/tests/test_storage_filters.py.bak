import importlib
from types import SimpleNamespace
def test_settings_and_dedup(tmp_path, monkeypatch):
    import config
    monkeypatch.setattr(config,"DB_PATH",str(tmp_path/"test.db")); import storage; importlib.reload(storage); storage.init()
    assert storage.get("enabled")=="1"; assert not storage.is_used("@x",1,"u","f")
    storage.mark_posted("@x",1,"u","f"); assert storage.is_used("@x",2,"u","")
def test_ad_detection():
    import filters
    assert filters.looks_like_ad(SimpleNamespace(message="Реклама, промокод https://x", fwd_from=None, reply_markup=None))
    assert not filters.looks_like_ad(SimpleNamespace(message="Блич", fwd_from=None, reply_markup=None))

def test_fingerprint_survives_telegram_video_metadata_changes(monkeypatch):
    import filters

    source = (SimpleNamespace(id=10, size=17_391_033), SimpleNamespace(duration=9.877, w=1080, h=1400))
    uploaded = (SimpleNamespace(id=20, size=17_391_033), SimpleNamespace(duration=0, w=1, h=1))

    monkeypatch.setattr(filters, "get_video", lambda message: source if message == "source" else uploaded)

    source_uid, source_fingerprint = filters.fingerprint("source")
    uploaded_uid, uploaded_fingerprint = filters.fingerprint("uploaded")
    assert source_uid != uploaded_uid
    assert source_fingerprint == uploaded_fingerprint == "size:17391033"

def test_upload_attributes_preserve_source_video_metadata(monkeypatch):
    import filters

    video = SimpleNamespace(duration=9.877, w=1080, h=1400)
    monkeypatch.setattr(filters, "get_video", lambda message: (SimpleNamespace(), video))
    monkeypatch.setattr(filters, "file_name_of", lambda message: "source.mp4")

    attributes = filters.upload_attributes(object())

    assert attributes[0].duration == 9.877
    assert attributes[0].w == 1080
    assert attributes[0].h == 1400
    assert attributes[0].supports_streaming is True
    assert attributes[1].file_name == "source.mp4"

def test_init_migrates_old_fingerprints_and_clears_posted_pending(tmp_path, monkeypatch):
    import config
    import storage

    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "migration.db"))
    importlib.reload(storage)
    storage.init()
    storage.enqueue(
        "2026-08-09",
        "10:00",
        {
            "source": "@AnWordX", "message_id": 7395, "file_uid": "source-doc",
            "fingerprint": "17391033:9:1080x1400",
        },
    )
    storage.mark_posted("__target__", 2621, "", "17391033:0:1x1")

    storage.init()

    assert storage.is_used("@AnWordX", 7395, "source-doc", "size:17391033")
    assert storage.clear_used_pending() == 1
    assert storage.list_queue("2026-08-09") == []
