import logging
from datetime import datetime, timedelta, timezone
import filters, storage
log = logging.getLogger("builder")
def _pack(source, msg, is_fallback):
    uid, fp = filters.fingerprint(msg)
    return {"source":source,"message_id":msg.id,"file_uid":uid,"fingerprint":fp,"score":filters.activity_score(msg),"is_fallback":is_fallback}
async def _scan(reader, source, limit, since, fresh):
    now = datetime.now(timezone.utc); min_age = timedelta(minutes=storage.get_int("min_age_min")); messages = await reader.get_messages(source, limit=limit)
    threshold = filters.views_threshold(messages, storage.get_float("activity_multiplier")) if fresh else 0
    result = []
    for msg in messages:
        if not msg.date or msg.date < since or now - msg.date < min_age or not filters.is_good_video(msg) or (fresh and (msg.views or 0) < threshold) or filters.looks_like_ad(msg): continue
        uid, fp = filters.fingerprint(msg)
        if not storage.is_used(source, msg.id, uid, fp): result.append(_pack(source, msg, 0 if fresh else 1))
    return result
async def collect(reader, need):
    now = datetime.now(timezone.utc); sources = storage.get_list("sources"); candidates = []
    for source in sources:
        try: candidates += await _scan(reader, source, storage.get_int("scan_limit"), now-timedelta(days=7), True)
        except Exception as exc: log.error("Ошибка чтения %s: %s", source, exc)
    candidates.sort(key=lambda item:item["score"], reverse=True)
    if len(candidates) >= need: return candidates[:need]
    archive = []
    for source in sources:
        try: archive += await _scan(reader, source, storage.get_int("deep_limit"), now-timedelta(days=storage.get_int("fallback_days")), False)
        except Exception as exc: log.error("Ошибка чтения %s: %s", source, exc)
    seen = {(x["source"],x["message_id"]) for x in candidates}; archive = [x for x in archive if (x["source"],x["message_id"]) not in seen]; archive.sort(key=lambda x:x["score"], reverse=True)
    return (candidates + archive)[:need]
async def build_day(reader, day=None):
    day = day or storage.today(); empty = storage.free_slots(day, storage.get_list("slots"))
    if not empty: return 0
    items = await collect(reader, len(empty))
    for slot, item in zip(empty, items): storage.enqueue(day, slot, item)
    return len(items)
