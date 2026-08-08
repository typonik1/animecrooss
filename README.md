# Anime crosspost bot

Автопостинг видео-эдитов из Telegram-каналов в заданные слоты по московскому времени. Читатель — личный Telegram-аккаунт Bianca, публикация — отдельный бот. Очередь, настройки и дедупликация хранятся в SQLite.

## Запуск

1. Скопируй `.env.example` в `.env` и заполни значения локально. Секреты не публикуй и не коммить.
2. Установи Python 3.11+: `python -m venv venv && source venv/bin/activate && pip install -r requirements.txt`.
3. Добавь бота администратором целевого канала с правом публикации.
4. Подпиши личный аккаунт на каналы-доноры и запусти `python main.py`.
5. При первом запуске введи номер и код Telegram для reader-сессии. Напиши боту `/id`, впиши ID в `.env`, перезапусти.

По умолчанию публикация автоматическая в `10:00,13:00,18:00,21:00` (Europe/Moscow). Управление: `/sources`, `/add`, `/del`, `/times`, `/queue`, `/build`, `/skip`, `/now`, `/set`, `/config`, `/pause`, `/resume`.

RouterAI подключается через OpenAI-совместимый API (`ROUTERAI_API_KEY`, `ROUTERAI_MODEL`, `ROUTERAI_BASE_URL`). Если API недоступен, используется локальный разбор подписей.

Чужие эдиты могут быть защищены авторским правом — сохраняй кредит автора и публикуй только контент, на который есть разрешение.

## Render Free Web Service

Render запускает проект как Web Service с `python3 main.py`; `/health` используется для health check и внешнего uptime-монитора. Python закреплён на версии 3.13.

Сначала на локальном компьютере, где уже авторизован аккаунт-читатель, получи переносимую сессию:

```bash
python3 -c "from telethon.sessions import SQLiteSession,StringSession; print(StringSession.save(SQLiteSession('anime_reader')))"
```

Вывод этой команды — секрет уровня пароля. Добавь его в Render → Environment под именем `TELEGRAM_SESSION_STRING`, не публикуй в Git и чатах. Также добавь `API_ID`, `API_HASH`, `BOT_TOKEN`, `ROUTERAI_API_KEY`.

Дополнительных владельцев укажи в `OWNER_IDS` через запятую. Аккаунт-читатель добавляется владельцем автоматически:

```text
OWNER_IDS=123456789,987654321
```

Настройки сервиса:

```text
Build Command: pip install -r requirements.txt
Start Command: python3 main.py
Health Check Path: /health
```

В UptimeRobot создай HTTP(S)-монитор для `https://<имя-сервиса>.onrender.com/health` с интервалом 5–10 минут. На Free Web Service локальные `bot.db` и файлы очереди сбрасываются при redeploy или restart, поэтому возможна повторная подборка старых постов.
