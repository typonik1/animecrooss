import os
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()

def parse_owner_ids(value: str, legacy_value: str = "") -> set[int]:
    parts = [part.strip() for part in f"{value},{legacy_value}".split(",")]
    return {int(part) for part in parts if part}

API_ID = int(os.getenv("API_ID", "0") or 0)
API_HASH = os.getenv("API_HASH", "")
SESSION_NAME = os.getenv("SESSION_NAME", "anime_reader")
TELEGRAM_SESSION_STRING = os.getenv("TELEGRAM_SESSION_STRING", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
TARGET_CHANNEL = os.getenv("TARGET_CHANNEL", "@anime_edit_videoo")
OWNER_ID = int(os.getenv("OWNER_ID", "0") or 0)
OWNER_IDS = parse_owner_ids(os.getenv("OWNER_IDS", ""), os.getenv("OWNER_ID", ""))
DB_PATH = os.getenv("DB_PATH", "bot.db")
DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "downloads")
PORT = int(os.getenv("PORT", "10000") or 10000)
IS_RENDER = os.getenv("RENDER", "").lower() == "true"
ROUTERAI_API_KEY = os.getenv("ROUTERAI_API_KEY", os.getenv("GEMINI_API_KEY", ""))
ROUTERAI_MODEL = os.getenv("ROUTERAI_MODEL", os.getenv("GEMINI_MODEL", "google/gemini-3.1-flash-lite"))
ROUTERAI_BASE_URL = os.getenv("ROUTERAI_BASE_URL", os.getenv("GEMINI_BASE_URL", "https://routerai.ru/api/v1"))
TZ = ZoneInfo("Europe/Moscow")
BUILD_AT = "08:00"
REACTION_AT = os.getenv("REACTION_AT", "23:55")
REACTION_EMOJI = os.getenv("REACTION_EMOJI", "❤")
PUBLISH_TIMEOUT_SEC = float(os.getenv("PUBLISH_TIMEOUT_SEC", "600"))
NOW_TIMEOUT_SEC = float(os.getenv("NOW_TIMEOUT_SEC", "660"))
REACTION_TIMEOUT_SEC = float(os.getenv("REACTION_TIMEOUT_SEC", "300"))
BUILD_TIMEOUT_SEC = float(os.getenv("BUILD_TIMEOUT_SEC", "300"))
SCHEDULER_POLL_SEC = float(os.getenv("SCHEDULER_POLL_SEC", "20"))
SIGNATURE = (
    "#аниме #анимеэдит #anime #amv #animeedit\n"
    '<a href="https://t.me/NosokVPNBot?start=partner_8235497168">Лучший VPN</a>'
)
DEFAULTS = {
    "slots": "10:00,13:00,18:00,21:00",
    "sources": "@Anitik_edits,@AnWordX,@AniZedEdits",
    "activity_multiplier": "1.3", "scan_limit": "120", "fresh_days": "7",
    "target_scan_limit": "1000", "min_age_min": "90", "min_sec": "5",
    "max_sec": "240", "max_mb": "48", "moderation": "0", "enabled": "1",
}
EMOJI_POOL = ["⚔️", "🔥", "🌸", "🩸", "🌙", "⚡", "🖤", "❄️", "🌊", "👺", "🎴", "💫"]
