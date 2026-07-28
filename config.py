import os
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
SESSION_NAME = os.getenv("SESSION_NAME", "anime_reader")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
TARGET_CHANNEL = os.getenv("TARGET_CHANNEL", "@anime_edit_videoo")
OWNER_ID = int(os.getenv("OWNER_ID", "0") or 0)
DB_PATH = os.getenv("DB_PATH", "bot.db")
DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "downloads")
ROUTERAI_API_KEY = os.getenv("ROUTERAI_API_KEY", os.getenv("GEMINI_API_KEY", ""))
ROUTERAI_MODEL = os.getenv("ROUTERAI_MODEL", os.getenv("GEMINI_MODEL", "google/gemini-3.1-flash-lite"))
ROUTERAI_BASE_URL = os.getenv("ROUTERAI_BASE_URL", os.getenv("GEMINI_BASE_URL", "https://routerai.ru/api/v1"))
TZ = ZoneInfo("Europe/Moscow")
BUILD_AT = "08:00"
SIGNATURE = "#аниме #анимеэдит #anime #amv #animeedit"
DEFAULTS = {
    "slots": "10:00,13:00,18:00,21:00",
    "sources": "@Anitik_edits,@AnWordX,@AniZedEdits",
    "activity_multiplier": "1.3", "scan_limit": "120", "deep_limit": "1500",
    "fallback_days": "120", "min_age_min": "90", "min_sec": "5",
    "max_sec": "240", "max_mb": "48", "moderation": "0", "enabled": "1",
}
EMOJI_POOL = ["⚔️", "🔥", "🌸", "🩸", "🌙", "⚡", "🖤", "❄️", "🌊", "👺", "🎴", "💫"]
