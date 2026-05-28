"""Verify SQLite helpers — user upsert, booking insert, stats counts."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone


def test_upsert_user_creates_then_updates(fresh_db):
    fresh_db.upsert_user(telegram_id=42, username="user42", first_name="Alice")
    assert fresh_db.count_users() == 1
    fresh_db.upsert_user(telegram_id=42, username="renamed", first_name="Alice2")
    assert fresh_db.count_users() == 1  # still one row


def test_add_booking_and_list_recent(fresh_db):
    fresh_db.upsert_user(telegram_id=42, username="alice", first_name="Alice")
    bid = fresh_db.add_booking(user_id=42, payload={"slot": "10:00"})
    assert bid > 0
    rows = fresh_db.list_recent_bookings(10)
    assert len(rows) == 1
    assert rows[0]["status"] == "new"
    assert rows[0]["user_id"] == 42


def test_stats_snapshot_counts(fresh_db):
    for tg_id in (1, 2, 3):
        fresh_db.upsert_user(telegram_id=tg_id, username=f"u{tg_id}", first_name=None)
    fresh_db.add_booking(user_id=1)
    fresh_db.add_booking(user_id=2)
    s = fresh_db.stats_snapshot()
    assert s["users_total"] == 3
    assert s["bookings_total"] == 2
    assert s["bookings_24h"] == 2
    assert s["bookings_7d"] == 2


def test_count_bookings_since_threshold(fresh_db):
    fresh_db.upsert_user(telegram_id=1, username="u", first_name=None)
    fresh_db.add_booking(user_id=1)
    # Bookings created right now must be counted by a 24h-back threshold
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    assert fresh_db.count_bookings_since(cutoff) == 1
    future = datetime.now(timezone.utc) + timedelta(hours=1)
    assert fresh_db.count_bookings_since(future) == 0


def test_record_broadcast_persists(fresh_db):
    bid = fresh_db.record_broadcast("hello world", sent_count=5)
    assert bid > 0
    with fresh_db.cursor() as cur:
        cur.execute("SELECT text, sent_count FROM broadcasts WHERE id = ?", (bid,))
        row = cur.fetchone()
    assert row["text"] == "hello world"
    assert row["sent_count"] == 5


def test_all_user_ids_returns_distinct_ids(fresh_db):
    for tg_id in (10, 20, 30):
        fresh_db.upsert_user(telegram_id=tg_id, username=None, first_name=None)
    ids = fresh_db.all_user_ids()
    assert sorted(ids) == [10, 20, 30]
