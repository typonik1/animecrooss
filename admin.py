import asyncio
import logging
from html import escape

from telethon import Button, events
import builder, config, publisher, storage
log = logging.getLogger("admin")
_now_lock = asyncio.Lock()
HELP = "<b>Команды</b>\n/sources /add @channel /del @channel\n/times 10:00,13:00,18:00,21:00\n/queue /build /skip 13:00 /now\nПосле /queue доступна кнопка обновления очереди.\n/set key value /config /pause /resume /id"
SET_USAGE = "Использование: /set параметр значение\nПараметры: " + ", ".join(config.DEFAULTS)
def is_owner(event): return event.is_private and event.sender_id in config.OWNER_IDS

def queue_controls():
    return Button.inline("🔄 Обновить очередь", b"refresh_queue")

def queue_line(slot, source, message_id, score, is_fallback, status):
    label = f"{source}/{message_id}"
    if source.startswith("@"):
        username = source[1:]
        post = f'<a href="https://t.me/{username}/{message_id}">{escape(label)}</a>'
    else:
        post = escape(label)
    return f"{escape(slot)} {'🕓' if is_fallback else '🆕'} {post} · {escape(status)}"

async def publish_now(reader, bot):
    items = await builder.collect(reader, 1)
    if not items:
        return None
    return await publisher.publish(reader, bot, items[0])

async def handle_now(event, reader, bot):
    if _now_lock.locked():
        await event.reply("Команда /now уже выполняется")
        return False
    await _now_lock.acquire()
    try:
        await event.reply("Ищу свежий уникальный ролик…")
        try:
            result = await asyncio.wait_for(
                publish_now(reader, bot), timeout=config.NOW_TIMEOUT_SEC
            )
        except asyncio.TimeoutError:
            log.error("Команда /now превысила таймаут %.0f сек", config.NOW_TIMEOUT_SEC)
            await event.reply("Время ожидания /now истекло. Попробуй ещё раз.")
            return False
        except Exception:
            log.exception("Ошибка команды /now")
            await event.reply("Ошибка /now: публикация не выполнена")
            return False
        await event.reply(
            "Опубликовано"
            if result is True
            else "Ошибка публикации"
            if result is False
            else "Свежих уникальных роликов не найдено"
        )
        return result
    finally:
        _now_lock.release()

async def refresh_queue(reader):
    day = storage.today()
    pending = storage.pending_count(day)
    replaced = 0
    if pending:
        # Collect while the current pending rows still exist.  This both
        # excludes old selections and preserves them if replacements run out.
        items = await builder.collect(reader, pending)
        if items:
            replaced = storage.replace_pending(day, items)
    filled = await builder.build_day(reader, day)
    return replaced, replaced + filled

def register(bot, reader):
    def owner(event): return is_owner(event)
    @bot.on(events.NewMessage(pattern=r"^/(start|help)"))
    async def help_cmd(event):
        if is_owner(event): await event.reply(HELP, parse_mode="html")
        elif event.is_private: await event.reply(f"Ваш id: <code>{event.sender_id}</code>", parse_mode="html")
    @bot.on(events.NewMessage(pattern=r"^/id"))
    async def id_cmd(event): await event.reply(f"<code>{event.sender_id}</code>", parse_mode="html")
    @bot.on(events.NewMessage(pattern=r"^/sources"))
    async def sources(event):
        if owner(event): await event.reply("Источники:\n"+"\n".join(storage.get_list("sources")))
    @bot.on(events.NewMessage(pattern=r"^/add\s+(\S+)"))
    async def add(event):
        if not owner(event): return
        channel = event.pattern_match.group(1).replace("https://t.me/", "@"); channel = channel if channel.startswith("@") else "@"+channel
        if channel not in storage.get_list("sources"):
            try: await reader.get_entity(channel)
            except Exception: await event.reply("Не могу открыть канал: аккаунт-читатель должен быть на него подписан."); return
            storage.set_value("sources", ",".join(storage.get_list("sources")+[channel]))
        await event.reply(f"Добавлен {channel}")
    @bot.on(events.NewMessage(pattern=r"^/del\s+(\S+)"))
    async def delete(event):
        if owner(event): storage.set_value("sources", ",".join(x for x in storage.get_list("sources") if x.lower()!=event.pattern_match.group(1).lower())); await event.reply("Удалено")
    @bot.on(events.NewMessage(pattern=r"^/times(?:\s+(.+))?"))
    async def times(event):
        if not owner(event): return
        arg=event.pattern_match.group(1)
        if arg: storage.set_value("slots", ",".join(sorted({x.strip() for x in arg.split(",") if len(x.strip())==5 and x.strip()[2]==":"})))
        await event.reply("Слоты: "+storage.get("slots"))
    @bot.on(events.NewMessage(pattern=r"^/queue"))
    async def queue(event):
        if owner(event):
            text = "\n".join(queue_line(*item) for item in storage.list_queue(storage.today())) or "Очередь пуста"
            await event.reply(text, buttons=queue_controls(), parse_mode="html", link_preview=False)
    @bot.on(events.NewMessage(pattern=r"^/build"))
    async def build(event):
        if owner(event): await event.reply(f"Добавлено: {await builder.build_day(reader)}")
    @bot.on(events.NewMessage(pattern=r"^/skip\s+(\S+)"))
    async def skip(event):
        if not owner(event): return
        item=storage.skip_slot(storage.today(), event.pattern_match.group(1))
        if item: storage.mark_posted(item["source"],item["message_id"],item["file_uid"],item["fingerprint"]); await builder.build_day(reader)
        await event.reply("Готово")
    @bot.on(events.NewMessage(pattern=r"^/now"))
    async def now(event):
        if not owner(event): return
        await handle_now(event, reader, bot)
    @bot.on(events.CallbackQuery(data=b"refresh_queue"))
    async def refresh(event):
        if not is_owner(event): return
        removed, added = await refresh_queue(reader)
        await event.answer("Очередь обновлена", alert=False)
        await event.edit(f"Очередь обновлена: удалено {removed}, добавлено {added}", buttons=queue_controls())
    @bot.on(events.NewMessage(pattern=r"^/set(?:\s+(\w+)(?:\s+(.+))?)?$"))
    async def setting(event):
        if not owner(event): return
        key, value = event.pattern_match.group(1), event.pattern_match.group(2)
        if not key or value is None:
            await event.reply(SET_USAGE)
        elif key in config.DEFAULTS:
            value = value.strip()
            storage.set_value(key, value)
            await event.reply(f"{key} = {value}")
        else:
            await event.reply("Неизвестный параметр\n" + SET_USAGE)
    @bot.on(events.NewMessage(pattern=r"^/config"))
    async def settings(event):
        if owner(event): await event.reply("\n".join(f"{k} = {storage.get(k)}" for k in config.DEFAULTS))
    @bot.on(events.NewMessage(pattern=r"^/(pause|resume)"))
    async def enabled(event):
        if owner(event): storage.set_value("enabled", "0" if event.pattern_match.group(1)=="pause" else "1"); await event.reply("Готово")
