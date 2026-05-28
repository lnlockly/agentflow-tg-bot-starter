"""Owner-only `/admin` panel.

Access is gated on `OWNER_TG_ID` env var, which the AgentFlow platform
writes to `/workspace/.env` from the creator's linked Telegram account.
A request whose `from_user.id` does not match is rejected with a short
notice — no leak of menu contents.

Four buttons:
  - 📊 Stats: aggregate counts from db.stats_snapshot().
  - 📋 Recent leads: last 10 rows from bookings, with timestamps.
  - 📣 Broadcast: prompts for body, sends to all rows in users.
  - ❌ Close: deletes the admin menu message.
"""
from __future__ import annotations

import asyncio
import logging
import os

from aiogram import Bot, Router, F
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

import db

logger = logging.getLogger("af-bot.admin")
router = Router(name="admin")


def get_owner_tg_id() -> int:
    raw = os.getenv("OWNER_TG_ID", "0").strip()
    try:
        return int(raw)
    except ValueError:
        return 0


def is_owner(user_id: int | None) -> bool:
    owner = get_owner_tg_id()
    return owner != 0 and user_id == owner


class BroadcastFlow(StatesGroup):
    waiting_for_text = State()


def _menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 Статистика", callback_data="admin:stats")],
            [InlineKeyboardButton(text="📋 Последние 10 заявок", callback_data="admin:recent")],
            [InlineKeyboardButton(text="📣 Рассылка", callback_data="admin:broadcast")],
            [InlineKeyboardButton(text="❌ Закрыть", callback_data="admin:close")],
        ]
    )


def _back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="« Назад", callback_data="admin:menu")]]
    )


@router.message(Command("admin"))
async def cmd_admin(msg: Message) -> None:
    if not is_owner(msg.from_user.id if msg.from_user else None):
        await msg.answer("Доступ только для владельца.")
        return
    await msg.answer("Админка. Выбери раздел:", reply_markup=_menu_kb())


@router.callback_query(F.data == "admin:menu")
async def cb_menu(cb: CallbackQuery) -> None:
    if not is_owner(cb.from_user.id):
        await cb.answer("Доступ только для владельца.", show_alert=True)
        return
    if isinstance(cb.message, Message):
        await cb.message.edit_text("Админка. Выбери раздел:", reply_markup=_menu_kb())
    await cb.answer()


@router.callback_query(F.data == "admin:stats")
async def cb_stats(cb: CallbackQuery) -> None:
    if not is_owner(cb.from_user.id):
        await cb.answer("Доступ только для владельца.", show_alert=True)
        return
    s = db.stats_snapshot()
    text = (
        "📊 Статистика\n\n"
        f"Юзеры всего: {s['users_total']}\n"
        f"Заявок всего: {s['bookings_total']}\n"
        f"Заявок за 24ч: {s['bookings_24h']}\n"
        f"Заявок за 7 дней: {s['bookings_7d']}\n"
    )
    if isinstance(cb.message, Message):
        await cb.message.edit_text(text, reply_markup=_back_kb())
    await cb.answer()


@router.callback_query(F.data == "admin:recent")
async def cb_recent(cb: CallbackQuery) -> None:
    if not is_owner(cb.from_user.id):
        await cb.answer("Доступ только для владельца.", show_alert=True)
        return
    rows = db.list_recent_bookings(10)
    if not rows:
        text = "📋 Последние заявки\n\nПока пусто."
    else:
        lines = ["📋 Последние 10 заявок\n"]
        for r in rows:
            who = r["username"] or r["first_name"] or f"id{r['user_id']}"
            lines.append(f"#{r['id']} · {r['created_at'][:16]} · {who} · {r['status']}")
        text = "\n".join(lines)
    if isinstance(cb.message, Message):
        await cb.message.edit_text(text, reply_markup=_back_kb())
    await cb.answer()


@router.callback_query(F.data == "admin:broadcast")
async def cb_broadcast_start(cb: CallbackQuery, state: FSMContext) -> None:
    if not is_owner(cb.from_user.id):
        await cb.answer("Доступ только для владельца.", show_alert=True)
        return
    await state.set_state(BroadcastFlow.waiting_for_text)
    if isinstance(cb.message, Message):
        await cb.message.edit_text(
            "📣 Пришли текст рассылки одним сообщением.\n"
            "Для отмены: /cancel",
            reply_markup=_back_kb(),
        )
    await cb.answer()


@router.message(Command("cancel"), BroadcastFlow.waiting_for_text)
async def cmd_cancel_broadcast(msg: Message, state: FSMContext) -> None:
    await state.clear()
    await msg.answer("Рассылка отменена.")


@router.message(BroadcastFlow.waiting_for_text)
async def receive_broadcast_text(msg: Message, state: FSMContext, bot: Bot) -> None:
    if not is_owner(msg.from_user.id if msg.from_user else None):
        return
    text = (msg.text or "").strip()
    if not text:
        await msg.answer("Пустое сообщение. Пришли текст или /cancel.")
        return
    await state.clear()
    user_ids = db.all_user_ids()
    owner_id = get_owner_tg_id()
    sent = 0
    failed = 0
    for uid in user_ids:
        if uid == owner_id:
            continue  # don't echo broadcast to the sender
        try:
            await bot.send_message(uid, text)
            sent += 1
        except (TelegramForbiddenError, TelegramBadRequest) as e:
            failed += 1
            logger.info("broadcast skip uid=%s: %s", uid, e.__class__.__name__)
        except Exception as e:  # noqa: BLE001
            failed += 1
            logger.warning("broadcast error uid=%s: %s", uid, e)
        await asyncio.sleep(0.04)  # ~25 msg/s, well under TG limit
    db.record_broadcast(text, sent)
    await msg.answer(
        f"✅ Рассылка отправлена.\n"
        f"Доставлено: {sent}\n"
        f"Не доставлено: {failed}",
        reply_markup=_menu_kb(),
    )


@router.callback_query(F.data == "admin:close")
async def cb_close(cb: CallbackQuery) -> None:
    if isinstance(cb.message, Message):
        try:
            await cb.message.delete()
        except TelegramBadRequest:
            pass
    await cb.answer()
