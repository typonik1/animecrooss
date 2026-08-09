import re, statistics
from typing import Iterable
from telethon.tl.types import DocumentAttributeFilename, DocumentAttributeVideo, MessageMediaDocument, ReplyInlineMarkup
import storage
AD_WORDS = ["реклам", "партнер", "партнёр", "взаимопиар", "промокод", "скидк", "розыгрыш", "казино", "букмекер", "крипт", "заработок", "вакансия", "сотрудничеств", "подпишись", "переходи", "бесплатно", "promo", "subscribe", "join"]
LINK_RE = re.compile(r"(https?://|t\.me/|@[A-Za-z][A-Za-z0-9_]{3,})")
INVITE_RE = re.compile(r"t\.me/(joinchat|\+)", re.I)
def looks_like_ad(message) -> bool:
    text = (getattr(message, "message", "") or "").lower()
    if getattr(message, "fwd_from", None) is not None or isinstance(getattr(message, "reply_markup", None), ReplyInlineMarkup) or INVITE_RE.search(text): return True
    hits = sum(word in text for word in AD_WORDS)
    return hits >= 2 or (hits >= 1 and LINK_RE.search(text)) or (len(text) > 400 and LINK_RE.search(text))
def get_video(message):
    if not isinstance(getattr(message, "media", None), MessageMediaDocument): return None
    doc = message.media.document
    for attr in doc.attributes:
        if isinstance(attr, DocumentAttributeVideo): return doc, attr
    return None
def file_name_of(message) -> str:
    found = get_video(message)
    if not found: return ""
    return next((a.file_name for a in found[0].attributes if isinstance(a, DocumentAttributeFilename)), "")
def is_good_video(message) -> bool:
    found = get_video(message)
    if not found: return False
    doc, attr = found
    return storage.get_int("min_sec") <= attr.duration <= storage.get_int("max_sec") and doc.size <= storage.get_int("max_mb") * 1024 * 1024
def fingerprint(message) -> tuple[str, str]:
    found = get_video(message)
    if not found: return "", ""
    doc, _ = found
    # Telegram assigns a new document id when the bot uploads the file and may
    # also lose duration/dimensions.  The exact byte size survives the upload,
    # so it is the stable metadata available without downloading every video.
    return str(doc.id), f"size:{doc.size}"

def upload_attributes(message) -> list:
    """Preserve source video metadata when the bot uploads a downloaded file."""
    found = get_video(message)
    if not found:
        return []
    _, video = found
    attributes = [
        DocumentAttributeVideo(
            duration=video.duration,
            w=video.w,
            h=video.h,
            supports_streaming=True,
        )
    ]
    filename = file_name_of(message)
    if filename:
        attributes.append(DocumentAttributeFilename(filename))
    return attributes
def reactions_count(message) -> int:
    reactions = getattr(message, "reactions", None)
    return sum(r.count for r in (getattr(reactions, "results", None) or [])) if reactions else 0
def activity_score(message) -> float: return (getattr(message, "views", 0) or 0) + (getattr(message, "forwards", 0) or 0) * 25 + reactions_count(message) * 8
def views_threshold(messages: Iterable, multiplier: float) -> float:
    views = [m.views or 0 for m in messages if (m.views or 0) > 0]
    return statistics.median(views) * multiplier if len(views) >= 5 else 0.0
