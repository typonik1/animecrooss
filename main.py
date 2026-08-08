import asyncio, logging
from datetime import datetime
from telethon import TelegramClient
from telethon.sessions import MemorySession, StringSession
import admin, builder, config, health, publisher, storage
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
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
    logging.getLogger("main").info("Владельцев настроено: %s", len(config.OWNER_IDS))
async def scheduler(reader, bot):
    while True:
        try:
            now=datetime.now(config.TZ); day=now.strftime("%Y-%m-%d"); hhmm=now.strftime("%H:%M")
            if hhmm==config.BUILD_AT and f"{day}:build" not in _done:
                _done.add(f"{day}:build"); await notify(bot, f"Очередь собрана: {await builder.build_day(reader)}")
            if storage.get("enabled")=="1" and hhmm in storage.get_list("slots") and f"{day}:{hhmm}" not in _done:
                _done.add(f"{day}:{hhmm}"); item=storage.take_slot(day,hhmm)
                if item is None: await builder.build_day(reader,day); item=storage.take_slot(day,hhmm)
                if item and storage.get("moderation")=="1": await notify(bot, f"Слот {hhmm}: /skip {hhmm} для отмены"); await asyncio.sleep(600); item=storage.take_slot(day,hhmm)
                if item and not await publisher.publish(reader,bot,item): await builder.build_day(reader,day)
        except Exception: logging.getLogger("main").exception("Ошибка планировщика")
        await asyncio.sleep(20)
async def main():
    if not config.API_ID or not config.API_HASH or not config.BOT_TOKEN: raise RuntimeError("Заполни API_ID, API_HASH и BOT_TOKEN в .env")
    if config.IS_RENDER and not config.TELEGRAM_SESSION_STRING:
        raise RuntimeError("Для Render добавь TELEGRAM_SESSION_STRING в Environment")
    server = await health.start(config.PORT)
    logging.getLogger("main").info("Health endpoint: http://0.0.0.0:%s/health", config.PORT)
    reader, bot = await create_clients()
    storage.init(); await reader.start()
    await add_reader_owner(reader)
    await bot.start(bot_token=config.BOT_TOKEN); admin.register(bot,reader); await notify(bot, "Бот запущен ✅"); await builder.build_day(reader); await asyncio.gather(server.serve_forever(), scheduler(reader, bot), bot.run_until_disconnected())
if __name__=="__main__": asyncio.run(main())
