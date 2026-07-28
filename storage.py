import sqlite3
from contextlib import closing
from datetime import datetime
import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS posted(source TEXT NOT NULL, message_id INTEGER NOT NULL,
 file_uid TEXT, fingerprint TEXT, posted_at TEXT DEFAULT CURRENT_TIMESTAMP,
 PRIMARY KEY(source, message_id));
CREATE INDEX IF NOT EXISTS idx_posted_uid ON posted(file_uid);
CREATE INDEX IF NOT EXISTS idx_posted_fp ON posted(fingerprint);
CREATE TABLE IF NOT EXISTS queue(id INTEGER PRIMARY KEY AUTOINCREMENT, day TEXT NOT NULL,
 slot TEXT NOT NULL, source TEXT NOT NULL, message_id INTEGER NOT NULL, file_uid TEXT,
 fingerprint TEXT, score REAL DEFAULT 0, is_fallback INTEGER DEFAULT 0,
 status TEXT DEFAULT 'pending', created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE UNIQUE INDEX IF NOT EXISTS idx_queue_day_slot ON queue(day, slot);
"""

def _db():
    return closing(sqlite3.connect(config.DB_PATH, timeout=30))

def init() -> None:
    with _db() as db:
        db.executescript(SCHEMA)
        db.executemany("INSERT OR IGNORE INTO settings(key,value) VALUES (?,?)", config.DEFAULTS.items())
        db.commit()

def get(key: str, default: str = "") -> str:
    with _db() as db:
        row = db.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row[0] if row else config.DEFAULTS.get(key, default)

def get_int(key: str) -> int: return int(float(get(key)))
def get_float(key: str) -> float: return float(get(key))
def get_list(key: str) -> list[str]: return [x.strip() for x in get(key).split(",") if x.strip()]

def set_value(key: str, value: str) -> None:
    with _db() as db:
        db.execute("INSERT INTO settings(key,value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, str(value)))
        db.commit()

def is_used(source: str, message_id: int, file_uid: str = "", fingerprint: str = "") -> bool:
    with _db() as db:
        row = db.execute("SELECT 1 FROM posted WHERE (source=? AND message_id=?) OR (file_uid!='' AND file_uid=?) OR (fingerprint!='' AND fingerprint=?) LIMIT 1", (source, message_id, file_uid, fingerprint)).fetchone()
        if row: return True
        row = db.execute("SELECT 1 FROM queue WHERE status IN ('pending','posted') AND ((source=? AND message_id=?) OR (file_uid!='' AND file_uid=?)) LIMIT 1", (source, message_id, file_uid)).fetchone()
    return row is not None

def mark_posted(source: str, message_id: int, file_uid: str, fingerprint: str) -> None:
    with _db() as db:
        db.execute("INSERT OR IGNORE INTO posted(source,message_id,file_uid,fingerprint) VALUES (?,?,?,?)", (source, message_id, file_uid, fingerprint)); db.commit()

def enqueue(day: str, slot: str, item: dict) -> None:
    with _db() as db:
        db.execute("INSERT OR REPLACE INTO queue(day,slot,source,message_id,file_uid,fingerprint,score,is_fallback,status) VALUES (?,?,?,?,?,?,?,?,'pending')", (day, slot, item['source'], item['message_id'], item.get('file_uid',''), item.get('fingerprint',''), item.get('score',0), int(item.get('is_fallback',0)))); db.commit()

def free_slots(day: str, slots: list[str]) -> list[str]:
    with _db() as db: taken = {r[0] for r in db.execute("SELECT slot FROM queue WHERE day=? AND status IN ('pending','posted')", (day,))}
    return [slot for slot in slots if slot not in taken]

def take_slot(day: str, slot: str) -> dict | None:
    with _db() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT id,source,message_id,file_uid,fingerprint,score,is_fallback FROM queue WHERE day=? AND slot=? AND status='pending'", (day, slot)).fetchone()
    if not row: return None
    return dict(zip(("id","source","message_id","file_uid","fingerprint","score","is_fallback"), row))

def set_status(queue_id: int, status: str) -> None:
    with _db() as db: db.execute("UPDATE queue SET status=? WHERE id=?", (status, queue_id)); db.commit()
def list_queue(day: str) -> list[tuple]:
    with _db() as db: return db.execute("SELECT slot,source,message_id,score,is_fallback,status FROM queue WHERE day=? ORDER BY slot", (day,)).fetchall()
def today() -> str: return datetime.now(config.TZ).strftime("%Y-%m-%d")
