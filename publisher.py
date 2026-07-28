import logging, os
import config, enrich, filters, storage
log = logging.getLogger("publisher")
async def publish(reader, bot, item) -> bool:
    msg = await reader.get_messages(item["source"], ids=item["message_id"])
    if not msg or not filters.get_video(msg): storage.set_status(item["id"], "failed"); return False
    parsed = await enrich.parse_caption(msg.message or "", filters.file_name_of(msg))
    if parsed["ad"]: storage.set_status(item["id"], "skipped"); storage.mark_posted(item["source"], msg.id, item["file_uid"], item["fingerprint"]); return False
    path = await reader.download_media(msg, file=config.DOWNLOAD_DIR)
    if not path: storage.set_status(item["id"], "failed"); return False
    try:
        await bot.send_file(config.TARGET_CHANNEL, path, caption=enrich.build_caption(parsed["anime"], parsed["track"]), parse_mode="html", supports_streaming=True, link_preview=False)
        storage.set_status(item["id"], "posted"); storage.mark_posted(item["source"], msg.id, item["file_uid"], item["fingerprint"]); return True
    except Exception:
        log.exception("Ошибка публикации"); storage.set_status(item["id"], "failed"); return False
    finally:
        if os.path.exists(path): os.remove(path)
