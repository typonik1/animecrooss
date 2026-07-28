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
