"""Хранилище MVP: SQLite через стандартную библиотеку.

Объём данных пилота (класс — десятки анкет, школа — сотни) полностью
покрывается SQLite. При тиражировании на регион схема переносится в
PostgreSQL без изменения логики: таблицы и запросы совместимы.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import get_settings

_local = threading.local()

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id              TEXT PRIMARY KEY,
    max_user_id     TEXT NOT NULL,
    chat_id         TEXT,
    school_id       TEXT NOT NULL,
    class_code      TEXT NOT NULL,
    initial_profile TEXT,
    selected_fields TEXT NOT NULL DEFAULT '[]',
    extra_subjects  TEXT NOT NULL DEFAULT '[]',
    chosen_profile  TEXT,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    finished_at     TEXT
);
CREATE INDEX IF NOT EXISTS idx_sessions_class ON sessions(class_code);
CREATE UNIQUE INDEX IF NOT EXISTS idx_sessions_user_class ON sessions(max_user_id, class_code);

CREATE TABLE IF NOT EXISTS outbox (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id    TEXT NOT NULL,
    kind       TEXT NOT NULL,
    payload    TEXT NOT NULL,
    due_at     TEXT NOT NULL,
    sent_at    TEXT,
    attempts   INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_outbox_pending ON outbox(sent_at, due_at);

CREATE TABLE IF NOT EXISTS events (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    type       TEXT NOT NULL,
    payload    TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_type ON events(type);
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect() -> sqlite3.Connection:
    """Соединение на поток: SQLite-объекты нельзя делить между потоками."""
    conn = getattr(_local, "conn", None)
    if conn is None:
        path = get_settings().db_path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute("PRAGMA foreign_keys=ON")
        _local.conn = conn
    return conn


def init_db() -> None:
    connect().executescript(SCHEMA)
    connect().commit()


def new_id() -> str:
    return uuid.uuid4().hex


# --- сессии -------------------------------------------------------------

def create_or_get_session(max_user_id: str, chat_id: str | None, school_id: str, class_code: str) -> sqlite3.Row:
    """Одна анкета на пару (пользователь, класс): повторный /start её продолжает."""
    conn = connect()
    row = conn.execute(
        "SELECT * FROM sessions WHERE max_user_id=? AND class_code=?", (max_user_id, class_code)
    ).fetchone()
    if row:
        return row
    sid = new_id()
    ts = now()
    conn.execute(
        "INSERT INTO sessions (id, max_user_id, chat_id, school_id, class_code, created_at, updated_at)"
        " VALUES (?,?,?,?,?,?,?)",
        (sid, max_user_id, chat_id, school_id, class_code, ts, ts),
    )
    conn.commit()
    log_event(sid, "session_created", {"class_code": class_code})
    return conn.execute("SELECT * FROM sessions WHERE id=?", (sid,)).fetchone()


def get_session(session_id: str) -> sqlite3.Row | None:
    return connect().execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()


def update_session(session_id: str, **fields: Any) -> None:
    if not fields:
        return
    for key in ("selected_fields", "extra_subjects"):
        if key in fields and not isinstance(fields[key], str):
            fields[key] = json.dumps(fields[key], ensure_ascii=False)
    fields["updated_at"] = now()
    sets = ", ".join(f"{k}=?" for k in fields)
    connect().execute(f"UPDATE sessions SET {sets} WHERE id=?", (*fields.values(), session_id))
    connect().commit()


def sessions_of_class(class_code: str) -> list[sqlite3.Row]:
    return connect().execute(
        "SELECT * FROM sessions WHERE class_code=? ORDER BY created_at", (class_code,)
    ).fetchall()


# --- очередь сообщений боту --------------------------------------------

def push_outbox(chat_id: str, kind: str, payload: dict, due_at: str | None = None) -> int:
    conn = connect()
    cur = conn.execute(
        "INSERT INTO outbox (chat_id, kind, payload, due_at, created_at) VALUES (?,?,?,?,?)",
        (chat_id, kind, json.dumps(payload, ensure_ascii=False), due_at or now(), now()),
    )
    conn.commit()
    return int(cur.lastrowid)


def pending_outbox(limit: int = 20) -> list[sqlite3.Row]:
    return connect().execute(
        "SELECT * FROM outbox WHERE sent_at IS NULL AND due_at<=? ORDER BY id LIMIT ?",
        (now(), limit),
    ).fetchall()


def ack_outbox(item_id: int, ok: bool = True) -> None:
    conn = connect()
    if ok:
        conn.execute("UPDATE outbox SET sent_at=? WHERE id=?", (now(), item_id))
    else:
        conn.execute("UPDATE outbox SET attempts=attempts+1 WHERE id=?", (item_id,))
    conn.commit()


def cancel_outbox(chat_id: str, kind: str) -> int:
    """Снять неотправленные сообщения того же типа (например, старое напоминание)."""
    conn = connect()
    cur = conn.execute(
        "DELETE FROM outbox WHERE chat_id=? AND kind=? AND sent_at IS NULL", (chat_id, kind)
    )
    conn.commit()
    return cur.rowcount


# --- события (метрики) --------------------------------------------------

def log_event(session_id: str | None, type_: str, payload: dict | None = None) -> None:
    conn = connect()
    conn.execute(
        "INSERT INTO events (session_id, type, payload, created_at) VALUES (?,?,?,?)",
        (session_id, type_, json.dumps(payload or {}, ensure_ascii=False), now()),
    )
    conn.commit()


def count_events(type_: str) -> int:
    return int(connect().execute("SELECT COUNT(*) c FROM events WHERE type=?", (type_,)).fetchone()["c"])
