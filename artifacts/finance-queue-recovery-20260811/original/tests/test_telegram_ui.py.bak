from types import SimpleNamespace


def _flat(rows):
    return [button for row in rows for button in row]


def _callbacks(rows):
    return {button.data for button in _flat(rows) if hasattr(button, "data")}


def test_inline_button_uses_style_and_loaded_premium_icon():
    import telegram_ui

    telegram_ui.set_emoji_icons({"🚀": 123456})
    button = telegram_ui.inline_button(
        "Сейчас", b"ui:now", style="success", emoji="🚀"
    )

    assert button.text == "Сейчас"
    assert button.data == b"ui:now"
    assert button.style.bg_success is True
    assert button.style.icon == 123456


def test_inline_button_uses_unicode_fallback_without_loaded_icon():
    import telegram_ui

    telegram_ui.set_emoji_icons({})
    button = telegram_ui.inline_button(
        "Сейчас", b"ui:now", style="success", emoji="🚀"
    )

    assert button.text == "🚀 Сейчас"
    assert button.style.bg_success is True
    assert button.style.icon is None


def test_main_buttons_cover_common_actions_with_semantic_colors():
    import telegram_ui

    telegram_ui.set_emoji_icons({})
    buttons = telegram_ui.main_buttons(enabled=True)
    by_data = {button.data: button for button in _flat(buttons)}

    assert set(by_data) == {
        b"ui:now", b"ui:queue", b"ui:refresh", b"ui:build",
        b"ui:sources", b"ui:times", b"ui:settings", b"ui:logs",
        b"ui:toggle_enabled",
    }
    assert by_data[b"ui:now"].style.bg_success is True
    assert by_data[b"ui:queue"].style.bg_primary is True
    assert by_data[b"ui:toggle_enabled"].style.bg_danger is True

    resumed = {button.data: button for button in _flat(telegram_ui.main_buttons(enabled=False))}
    assert resumed[b"ui:toggle_enabled"].style.bg_success is True
    assert "Запустить" in resumed[b"ui:toggle_enabled"].text


def test_submenu_buttons_have_navigation_and_mutation_callbacks():
    import telegram_ui

    telegram_ui.set_emoji_icons({})

    assert _callbacks(telegram_ui.queue_buttons()) == {
        b"ui:refresh", b"ui:build", b"ui:home"
    }
    assert _callbacks(telegram_ui.source_buttons(["@one", "@two"])) == {
        b"ui:source:add", b"ui:source:del:0", b"ui:source:del:1", b"ui:home"
    }
    assert _callbacks(telegram_ui.schedule_buttons(["10:00", "13:00"])) == {
        b"ui:time:add", b"ui:time:del:1000", b"ui:time:del:1300",
        b"ui:time:default", b"ui:home",
    }
    assert _callbacks(telegram_ui.settings_buttons(enabled=True, moderation=False)) == {
        b"ui:toggle_enabled", b"ui:toggle_moderation", b"ui:config", b"ui:home"
    }
    assert _callbacks(telegram_ui.log_buttons()) == {
        b"ui:logs:errors", b"ui:logs:publisher", b"ui:logs:scheduler",
        b"ui:logs:all", b"ui:logs:download", b"ui:logs", b"ui:home",
    }


def test_queue_text_localizes_statuses_and_keeps_clickable_source_links():
    import telegram_ui

    rows = [
        ("10:00", "@Anitik_edits", 22931, 10.0, 0, "pending"),
        ("13:00", "@AnWordX", 7396, 9.0, 0, "publishing"),
        ("18:00", "@AniZedEdits", 8932, 8.0, 0, "failed"),
    ]

    text = telegram_ui.queue_text(rows)

    assert '<a href="https://t.me/Anitik_edits/22931">@Anitik_edits/22931</a>' in text
    assert "⏳ ожидает" in text
    assert "📤 публикуется" in text
    assert "❌ ошибка" in text


def test_dashboard_text_summarizes_state_counts_and_slots():
    import telegram_ui

    text = telegram_ui.dashboard_text(
        enabled=True,
        counts={"posted": 2, "pending": 1, "failed": 1, "publishing": 0},
        slots=["10:00", "13:00", "18:00", "21:00"],
    )

    assert "🟢 <b>Бот работает</b>" in text
    assert "Опубликовано: <b>2</b>" in text
    assert "Ожидает: <b>1</b>" in text
    assert "Ошибки: <b>1</b>" in text
    assert "10:00 · 13:00 · 18:00 · 21:00" in text
