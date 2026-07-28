import config
def test_default_slots_are_moscow_schedule():
    assert config.TZ.key == "Europe/Moscow"
    assert config.DEFAULTS["slots"] == "10:00,13:00,18:00,21:00"
