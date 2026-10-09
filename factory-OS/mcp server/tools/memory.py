"""Persistent, user-scoped key/value memory using SQLite."""
import json
import os
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

DB_PATH = Path(os.getenv("FACTORY_OS_MEMORY_DB", Path(__file__).resolve().parents[1] / "memory.db"))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def connect():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    with connect() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            memory_type TEXT NOT NULL DEFAULT 'general',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(user_id, key))""")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_user ON memories(user_id)")

init_db()


def store_memory(user_id: str, key: str, value_json: str, memory_type: str = "general"):
    _validate(user_id, key)
    value = json.dumps(json.loads(value_json), ensure_ascii=False)
    now = datetime.now(timezone.utc).isoformat()
    with connect() as conn:
        conn.execute("""INSERT INTO memories(user_id,key,value,memory_type,created_at,updated_at)
            VALUES(?,?,?,?,?,?) ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value,
            memory_type=excluded.memory_type, updated_at=excluded.updated_at""",
            (user_id, key, value, memory_type, now, now))
    return {"success": True, "user_id": user_id, "key": key}


def get_memory(user_id: str, key: str):
    _validate(user_id, key)
    with connect() as conn:
        row = conn.execute("SELECT key,value,memory_type,created_at,updated_at FROM memories WHERE user_id=? AND key=?", (user_id,key)).fetchone()
    if not row:
        return {"found": False}
    return {"found": True, "key": row[0], "value": json.loads(row[1]), "memory_type": row[2], "created_at": row[3], "updated_at": row[4]}


def search_memory(user_id: str, query: str, limit: int = 10):
    if not user_id.strip() or not query.strip():
        raise ValueError("user_id and query are required")
    limit = max(1, min(int(limit), 50))
    pattern = f"%{query}%"
    with connect() as conn:
        rows = conn.execute("SELECT key,value,memory_type,updated_at FROM memories WHERE user_id=? AND (key LIKE ? OR value LIKE ?) ORDER BY updated_at DESC LIMIT ?", (user_id,pattern,pattern,limit)).fetchall()
    return [{"key": r[0], "value": json.loads(r[1]), "memory_type": r[2], "updated_at": r[3]} for r in rows]


def list_memories(user_id: str, memory_type: str = "", limit: int = 50):
    if not user_id.strip():
        raise ValueError("user_id is required")
    limit = max(1, min(int(limit), 100))
    with connect() as conn:
        if memory_type:
            rows = conn.execute("SELECT key,value,memory_type,updated_at FROM memories WHERE user_id=? AND memory_type=? ORDER BY updated_at DESC LIMIT ?", (user_id,memory_type,limit)).fetchall()
        else:
            rows = conn.execute("SELECT key,value,memory_type,updated_at FROM memories WHERE user_id=? ORDER BY updated_at DESC LIMIT ?", (user_id,limit)).fetchall()
    return [{"key": r[0], "value": json.loads(r[1]), "memory_type": r[2], "updated_at": r[3]} for r in rows]


def delete_memory(user_id: str, key: str):
    _validate(user_id, key)
    with connect() as conn:
        cur = conn.execute("DELETE FROM memories WHERE user_id=? AND key=?", (user_id,key))
    return {"success": cur.rowcount > 0, "deleted": cur.rowcount}


def _validate(user_id, key):
    if not isinstance(user_id, str) or not user_id.strip():
        raise ValueError("user_id is required")
    if not isinstance(key, str) or not key.strip():
        raise ValueError("key is required")
