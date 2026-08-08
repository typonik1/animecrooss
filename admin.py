from telethon import Button, events
import builder, config, publisher, storage
HELP = "<b>Команды</b>\n/sources /add @channel /del @channel\n/times 10:00,13:00,18:00,21:00\n/queue /build /skip 13:00 /now\nПосле /queue доступна кнопка обновления очереди.\n/set key value /config /pause /resume /id"
def is_owner(event): return event.is_private and event.sender_id in config.OWNER_IDS

def queue_controls():
    return Button.inline("🔄 Обновить очередь", b"refresh_queue")

async def publish_now(reader, bot):
    items = await builder.collect(reader, 1)
    if not items:
        return None
    return await publisher.publish(reader, bot, items[0])

async def refresh_queue(reader):
    removed = storage.clear_pending(storage.today())
    added = await builder.build_day(reader)
    return removed, added

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
        if owner(event): await event.reply("\n".join(f"{s} {'🕓' if fb else '🆕'} {src}/{mid} · {st}" for s,src,mid,score,fb,st in storage.list_queue(storage.today())) or "Очередь пуста", buttons=queue_controls())
    @bot.on(events.NewMessage(pattern=r"^/build"))
    async def build(event):
        if owner(event): await event.reply(f"Добавлено: {await builder.build_day(reader)}")
    @bot.on(events.NewMessage(pattern=r"^/skip\s+(\S+)"))
    async def skip(event):
        if not owner(event): return
        item=storage.take_slot(storage.today(), event.pattern_match.group(1))
        if item: storage.set_status(item["id"], "skipped"); storage.mark_posted(item["source"],item["message_id"],item["file_uid"],item["fingerprint"]); await builder.build_day(reader)
        await event.reply("Готово")
    @bot.on(events.NewMessage(pattern=r"^/now"))
    async def now(event):
        if not owner(event): return
        result = await publish_now(reader, bot)
        await event.reply("Опубликовано" if result is True else "Ошибка публикации" if result is False else "Свежих уникальных роликов не найдено")
    @bot.on(events.CallbackQuery(data=b"refresh_queue"))
    async def refresh(event):
        if not is_owner(event): return
        removed, added = await refresh_queue(reader)
        await event.answer("Очередь обновлена", alert=False)
        await event.edit(f"Очередь обновлена: удалено {removed}, добавлено {added}", buttons=queue_controls())
    @bot.on(events.NewMessage(pattern=r"^/set\s+(\w+)\s+(.+)"))
    async def setting(event):
        if owner(event):
            key,value=event.pattern_match.group(1),event.pattern_match.group(2).strip()
            if key in config.DEFAULTS: storage.set_value(key,value); await event.reply(f"{key} = {value}")
            else: await event.reply("Неизвестный параметр")
    @bot.on(events.NewMessage(pattern=r"^/config"))
    async def settings(event):
        if owner(event): await event.reply("\n".join(f"{k} = {storage.get(k)}" for k in config.DEFAULTS))
    @bot.on(events.NewMessage(pattern=r"^/(pause|resume)"))
    async def enabled(event):
        if owner(event): storage.set_value("enabled", "0" if event.pattern_match.group(1)=="pause" else "1"); await event.reply("Готово")
