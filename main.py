import asyncio, logging
from datetime import datetime
from telethon import TelegramClient
import admin, builder, config, publisher, storage
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
reader = TelegramClient(config.SESSION_NAME, config.API_ID, config.API_HASH)
bot = TelegramClient("bot_session", config.API_ID, config.API_HASH)
_done: set[str] = set()
async def notify(text):
    if config.OWNER_ID:
        try: await bot.send_message(config.OWNER_ID, text, parse_mode="html", link_preview=False)
        except Exception: pass
async def scheduler():
    while True:
        try:
            now=datetime.now(config.TZ); day=now.strftime("%Y-%m-%d"); hhmm=now.strftime("%H:%M")
            if hhmm==config.BUILD_AT and f"{day}:build" not in _done:
                _done.add(f"{day}:build"); await notify(f"Очередь собрана: {await builder.build_day(reader)}")
            if storage.get("enabled")=="1" and hhmm in storage.get_list("slots") and f"{day}:{hhmm}" not in _done:
                _done.add(f"{day}:{hhmm}"); item=storage.take_slot(day,hhmm)
                if item is None: await builder.build_day(reader,day); item=storage.take_slot(day,hhmm)
                if item and storage.get("moderation")=="1": await notify(f"Слот {hhmm}: /skip {hhmm} для отмены"); await asyncio.sleep(600); item=storage.take_slot(day,hhmm)
                if item and not await publisher.publish(reader,bot,item): await builder.build_day(reader,day)
        except Exception: logging.getLogger("main").exception("Ошибка планировщика")
        await asyncio.sleep(20)
async def main():
    if not config.API_ID or not config.API_HASH or not config.BOT_TOKEN: raise RuntimeError("Заполни API_ID, API_HASH и BOT_TOKEN в .env")
    storage.init(); await reader.start(); await bot.start(bot_token=config.BOT_TOKEN); admin.register(bot,reader); await notify("Бот запущен ✅"); await builder.build_day(reader); await asyncio.gather(scheduler(),bot.run_until_disconnected())
if __name__=="__main__": asyncio.run(main())
