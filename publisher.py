import logging, os
import config, enrich, filters, storage
log = logging.getLogger("publisher")
async def publish(reader, bot, item, queue_id=None) -> bool:
    queue_id = item.get("id") if queue_id is None else queue_id
    msg = await reader.get_messages(item["source"], ids=item["message_id"])
    if not msg or not filters.get_video(msg):
        if queue_id is not None: storage.set_status(queue_id, "failed")
        return False
    parsed = await enrich.parse_caption(msg.message or "", filters.file_name_of(msg))
    # Модель может принять обычную строку «Автор: ...» за рекламу канала.
    # Пропускаем только если AI-флаг подтверждается детерминированным фильтром.
    if parsed["ad"] and filters.looks_like_ad(msg):
        if queue_id is not None: storage.set_status(queue_id, "skipped")
        storage.mark_posted(item["source"], msg.id, item["file_uid"], item["fingerprint"]); return False
    path = await reader.download_media(msg, file=config.DOWNLOAD_DIR)
    if not path:
        if queue_id is not None: storage.set_status(queue_id, "failed")
        return False
    try:
        await bot.send_file(config.TARGET_CHANNEL, path, caption=enrich.build_caption(parsed["anime"], parsed["track"]), parse_mode="html", supports_streaming=True, link_preview=False)
        if queue_id is not None: storage.set_status(queue_id, "posted")
        storage.mark_posted(item["source"], msg.id, item["file_uid"], item["fingerprint"]); return True
    except Exception:
        log.exception("Ошибка публикации")
        if queue_id is not None: storage.set_status(queue_id, "failed")
        return False
    finally:
        if os.path.exists(path): os.remove(path)
