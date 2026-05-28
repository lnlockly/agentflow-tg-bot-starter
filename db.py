"""SQLite mini-database for the AgentFlow Telegram bot.

Three tables track user activity, generic «заявки» (leads / bookings /
requests — whatever the brief decides to call them) and broadcast history.
The coder agent can extend this schema for the brief, but the four
existing tables must stay so `/admin` keeps working.

Schema is created on import via `init_db()`. SQLite lives at the path in
`BOT_DB_PATH` (defaults to `bot.db` in cwd).
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Iterable, Iterator

DB_PATH = os.getenv("BOT_DB_PATH", "bot.db")

_lock = threading.Lock()


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def cursor() -> Iterator[sqlite3.Cursor]:
    with _lock:
        conn = _connect()
        try:
            cur = conn.cursor()
            yield cur
            conn.commit()
        finally:
            conn.close()


def init_db() -> None:
    """Create tables if absent. Safe to call on every boot."""
    with cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                username    TEXT,
                first_name  TEXT,
                joined_at   TEXT NOT NULL,
                last_seen   TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS bookings (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                status      TEXT NOT NULL DEFAULT 'new',
                payload     TEXT NOT NULL DEFAULT '{}',
                created_at  TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(telegram_id)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS broadcasts (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                text        TEXT NOT NULL,
                sent_count  INTEGER NOT NULL DEFAULT 0,
                created_at  TEXT NOT NULL
            )
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_bookings_user ON bookings(user_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_bookings_created ON bookings(created_at)")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def upsert_user(telegram_id: int, username: str | None, first_name: str | None) -> None:
    now = _now_iso()
    with cursor() as cur:
        cur.execute(
            """
            INSERT INTO users (telegram_id, username, first_name, joined_at, last_seen)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name,
                last_seen = excluded.last_seen
            """,
            (telegram_id, username, first_name, now, now),
        )


def add_booking(user_id: int, payload: dict | None = None, status: str = "new") -> int:
    with cursor() as cur:
        cur.execute(
            "INSERT INTO bookings (user_id, status, payload, created_at) VALUES (?, ?, ?, ?)",
            (user_id, status, json.dumps(payload or {}, ensure_ascii=False), _now_iso()),
        )
        return int(cur.lastrowid)


def list_recent_bookings(limit: int = 10) -> list[sqlite3.Row]:
    with cursor() as cur:
        cur.execute(
            """
            SELECT b.id, b.user_id, b.status, b.payload, b.created_at,
                   u.username, u.first_name
              FROM bookings b
              LEFT JOIN users u ON u.telegram_id = b.user_id
             ORDER BY b.id DESC
             LIMIT ?
            """,
            (limit,),
        )
        return list(cur.fetchall())


def count_users() -> int:
    with cursor() as cur:
        cur.execute("SELECT COUNT(*) AS c FROM users")
        return int(cur.fetchone()["c"])


def count_bookings_since(since: datetime | None) -> int:
    with cursor() as cur:
        if since is None:
            cur.execute("SELECT COUNT(*) AS c FROM bookings")
        else:
            cur.execute(
                "SELECT COUNT(*) AS c FROM bookings WHERE created_at >= ?",
                (since.isoformat(),),
            )
        return int(cur.fetchone()["c"])


def stats_snapshot() -> dict:
    now = datetime.now(timezone.utc)
    day_ago = now - timedelta(days=1)
    week_ago = now - timedelta(days=7)
    return {
        "users_total": count_users(),
        "bookings_total": count_bookings_since(None),
        "bookings_24h": count_bookings_since(day_ago),
        "bookings_7d": count_bookings_since(week_ago),
    }


def all_user_ids() -> list[int]:
    with cursor() as cur:
        cur.execute("SELECT telegram_id FROM users")
        return [int(r["telegram_id"]) for r in cur.fetchall()]


def record_broadcast(text: str, sent_count: int) -> int:
    with cursor() as cur:
        cur.execute(
            "INSERT INTO broadcasts (text, sent_count, created_at) VALUES (?, ?, ?)",
            (text, sent_count, _now_iso()),
        )
        return int(cur.lastrowid)
