import logging
from datetime import datetime, timedelta, timezone

import config
import filters
import storage

log = logging.getLogger("builder")

_target_history_synced = False


def _pack(source, msg, is_fallback):
    uid, fingerprint = filters.fingerprint(msg)
    return {
        "source": source,
        "message_id": msg.id,
        "file_uid": uid,
        "fingerprint": fingerprint,
        "score": filters.activity_score(msg),
        "is_fallback": is_fallback,
    }


async def _scan(reader, source, limit, since, fresh):
    now = datetime.now(timezone.utc)
    min_age = timedelta(minutes=storage.get_int("min_age_min"))
    messages = await reader.get_messages(source, limit=limit)
    eligible = []
    for msg in messages:
        if (
            not msg.date
            or msg.date < since
            or now - msg.date < min_age
            or not filters.is_good_video(msg)
            or filters.looks_like_ad(msg)
        ):
            continue
        eligible.append(msg)

    # Old posts have had much longer to accumulate views.  Including them in
    # the median makes every genuinely fresh post look inactive, so compare a
    # fresh video only with the other videos in the same eligibility window.
    threshold = filters.views_threshold(eligible, storage.get_float("activity_multiplier")) if fresh else 0
    result = []
    for msg in eligible:
        if fresh and (msg.views or 0) < threshold:
            continue
        uid, fingerprint = filters.fingerprint(msg)
        if not storage.is_used(source, msg.id, uid, fingerprint):
            result.append(_pack(source, msg, 0 if fresh else 1))
    return result


def balanced_select(groups: dict[str, list[dict]], need: int) -> list[dict]:
    """Take the most active eligible item from each source in rotation."""
    ranked = {
        source: sorted(items, key=lambda item: item["score"], reverse=True)
        for source, items in groups.items()
    }
    selected = []
    while len(selected) < need:
        added = False
        for source in groups:
            if not ranked[source]:
                continue
            selected.append(ranked[source].pop(0))
            added = True
            if len(selected) == need:
                break
        if not added:
            break
    return selected


async def sync_target_history(reader, limit: int | None = None) -> int:
    """Restore duplicate protection from recent video messages in the target."""
    limit = limit or storage.get_int("target_scan_limit")
    messages = await reader.get_messages(config.TARGET_CHANNEL, limit=limit)
    imported = 0
    for message in messages:
        if not filters.get_video(message):
            continue
        _, fingerprint = filters.fingerprint(message)
        if not fingerprint:
            continue
        storage.mark_posted("__target__", message.id, "", fingerprint)
        imported += 1
    removed = storage.clear_used_pending()
    log.info("Загружено отпечатков из целевого канала: %s", imported)
    if removed:
        log.info("Удалено ожидающих дублей после сверки с целевым каналом: %s", removed)
    return imported


async def ensure_target_history_synced(reader) -> None:
    global _target_history_synced
    if _target_history_synced:
        return
    try:
        await sync_target_history(reader)
    except Exception as exc:
        log.error("Не удалось загрузить историю целевого канала: %s", exc)
    finally:
        _target_history_synced = True


async def collect(reader, need):
    await ensure_target_history_synced(reader)
    now = datetime.now(timezone.utc)
    sources = storage.get_list("sources")
    candidates = {}
    for source in sources:
        try:
            candidates[source] = await _scan(
                reader,
                source,
                storage.get_int("scan_limit"),
                now - timedelta(days=storage.get_int("fresh_days")),
                True,
            )
        except Exception as exc:
            log.error("Ошибка чтения %s: %s", source, exc)
    return balanced_select(candidates, need)


async def build_day(reader, day=None):
    await ensure_target_history_synced(reader)
    day = day or storage.today()
    empty = storage.free_slots(day, storage.get_list("slots"))
    if not empty:
        return 0
    items = await collect(reader, len(empty))
    for slot, item in zip(empty, items):
        storage.enqueue(day, slot, item)
    return len(items)
