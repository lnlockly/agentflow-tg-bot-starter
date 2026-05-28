"""Verify broadcast handler fans messages to every registered user except the owner."""
from __future__ import annotations

import asyncio
import importlib
from types import SimpleNamespace

import pytest

OWNER = 1361064246


class FakeBot:
    def __init__(self):
        self.sent: list[tuple[int, str]] = []

    async def send_message(self, chat_id: int, text: str) -> None:
        self.sent.append((chat_id, text))


class FakeFSMContext:
    def __init__(self):
        self.cleared = False

    async def clear(self):
        self.cleared = True


class FakeMessage:
    def __init__(self, text: str, from_user_id: int):
        self.text = text
        self.from_user = SimpleNamespace(id=from_user_id)
        self.answers: list[tuple[str, object]] = []

    async def answer(self, text: str, reply_markup=None):
        self.answers.append((text, reply_markup))


@pytest.mark.asyncio
async def test_broadcast_sends_to_all_users_except_owner(fresh_db, monkeypatch):
    monkeypatch.setenv("OWNER_TG_ID", str(OWNER))
    import admin as admin_module  # noqa: WPS433

    importlib.reload(admin_module)

    # Seed 3 users + the owner.
    for tg_id in (101, 202, 303):
        fresh_db.upsert_user(telegram_id=tg_id, username=f"u{tg_id}", first_name=None)
    fresh_db.upsert_user(telegram_id=OWNER, username="owner", first_name="Owner")

    bot = FakeBot()
    state = FakeFSMContext()
    msg = FakeMessage(text="Salam alaikum", from_user_id=OWNER)

    await admin_module.receive_broadcast_text(msg, state, bot)

    sent_ids = sorted(uid for uid, _ in bot.sent)
    assert sent_ids == [101, 202, 303]  # owner excluded
    assert all(text == "Salam alaikum" for _, text in bot.sent)
    # Confirm the broadcasts table got a row
    with fresh_db.cursor() as cur:
        cur.execute("SELECT text, sent_count FROM broadcasts ORDER BY id DESC LIMIT 1")
        row = cur.fetchone()
    assert row["text"] == "Salam alaikum"
    assert row["sent_count"] == 3
    assert state.cleared is True


@pytest.mark.asyncio
async def test_broadcast_blocked_for_non_owner(fresh_db, monkeypatch):
    monkeypatch.setenv("OWNER_TG_ID", str(OWNER))
    import admin as admin_module  # noqa: WPS433

    importlib.reload(admin_module)

    fresh_db.upsert_user(telegram_id=42, username="other", first_name=None)
    bot = FakeBot()
    state = FakeFSMContext()
    msg = FakeMessage(text="spam", from_user_id=42)  # non-owner

    await admin_module.receive_broadcast_text(msg, state, bot)
    # Nothing was sent.
    assert bot.sent == []


def test_async_runs():
    # Sanity — pytest-asyncio is wired
    asyncio.run(asyncio.sleep(0))
