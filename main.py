import asyncio, logging
from datetime import datetime
from telethon import TelegramClient
from telethon.sessions import MemorySession, StringSession
import admin, builder, config, health, publisher, reactions, storage
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
log = logging.getLogger("main")
_done: set[str] = set()

def reader_session():
    if config.TELEGRAM_SESSION_STRING:
        return StringSession(config.TELEGRAM_SESSION_STRING)
    return config.SESSION_NAME

async def create_clients():
    reader = TelegramClient(reader_session(), config.API_ID, config.API_HASH)
    bot = TelegramClient(MemorySession(), config.API_ID, config.API_HASH)
    return reader, bot

async def notify(bot, text):
    for owner_id in sorted(config.OWNER_IDS):
        try: await bot.send_message(owner_id, text, parse_mode="html", link_preview=False)
        except Exception: pass

async def add_reader_owner(reader):
    me = await reader.get_me()
    config.OWNER_IDS.add(me.id)
    log.info("Владельцев настроено: %s", len(config.OWNER_IDS))

async def run_scheduler_tick(reader, bot, now=None):
    now = now or datetime.now(config.TZ)
    day = now.strftime("%Y-%m-%d")
    hhmm = now.strftime("%H:%M")
    build_key = f"{day}:build"
    if hhmm == config.BUILD_AT and build_key not in _done:
        built = await asyncio.wait_for(
            builder.build_day(reader, day), timeout=config.BUILD_TIMEOUT_SEC
        )
        _done.add(build_key)
        await notify(bot, f"Очередь собрана: {built}")
    if storage.get("enabled") != "1":
        return None
    item = storage.claim_next_due(day, hhmm)
    if item is None:
        return None
    log.info("Публикация просроченного/текущего слота %s %s", day, item["slot"])
    if storage.get("moderation") == "1":
        await notify(bot, f"Слот {item['slot']}: /skip {item['slot']} для отмены")
        await asyncio.sleep(600)
        if storage.get_status(item["id"]) != "publishing":
            return False
    return await publisher.publish(reader, bot, item)

async def run_reactions_once(reader, now=None):
    now = now or datetime.now(config.TZ)
    reaction_day = reactions.due_reaction_day(now)
    reaction_key = f"{reaction_day.isoformat()}:reactions"
    if reaction_key in _done:
        return None
    try:
        stats = await asyncio.wait_for(
            reactions.react_to_day_posts(reader, reaction_day),
            timeout=config.REACTION_TIMEOUT_SEC,
        )
    except asyncio.TimeoutError:
        log.error("Таймаут реакций за %s после %.0f сек", reaction_day, config.REACTION_TIMEOUT_SEC)
        return False
    except Exception:
        log.exception("Ошибка реакций за %s", reaction_day)
        return False
    _done.add(reaction_key)
    log.info(
        "Реакции за %s: найдено=%s поставлено=%s уже было=%s ошибок=%s",
        reaction_day, stats["found"], stats["reacted"], stats["skipped"], stats["failed"],
    )
    return True

async def scheduler(reader, bot):
    while True:
        try:
            await run_scheduler_tick(reader, bot)
        except Exception:
            log.exception("Ошибка планировщика")
        await asyncio.sleep(config.SCHEDULER_POLL_SEC)

async def reaction_scheduler(reader):
    while True:
        await run_reactions_once(reader)
        await asyncio.sleep(config.SCHEDULER_POLL_SEC)

async def main():
    if not config.API_ID or not config.API_HASH or not config.BOT_TOKEN: raise RuntimeError("Заполни API_ID, API_HASH и BOT_TOKEN в .env")
    if config.IS_RENDER and not config.TELEGRAM_SESSION_STRING:
        raise RuntimeError("Для Render добавь TELEGRAM_SESSION_STRING в Environment")
    server = await health.start(config.PORT)
    log.info("Health endpoint: http://0.0.0.0:%s/health", config.PORT)
    reader, bot = await create_clients()
    storage.init(); await reader.start()
    await add_reader_owner(reader)
    await bot.start(bot_token=config.BOT_TOKEN)
    admin.register(bot, reader)
    await notify(bot, "Бот запущен ✅")
    try:
        await asyncio.wait_for(builder.build_day(reader), timeout=config.BUILD_TIMEOUT_SEC)
    except asyncio.TimeoutError:
        log.error("Начальная сборка очереди превысила таймаут %.0f сек", config.BUILD_TIMEOUT_SEC)
    except Exception:
        log.exception("Ошибка начальной сборки очереди")
    await asyncio.gather(
        server.serve_forever(),
        scheduler(reader, bot),
        reaction_scheduler(reader),
        bot.run_until_disconnected(),
    )
if __name__=="__main__": asyncio.run(main())
