"""AgentFlow Telegram bot starter — aiogram 3 with creator-only admin panel.

The platform writes BOT_TOKEN, BOT_USERNAME, and OWNER_TG_ID to .env before
starting this file via the Procfile supervisor. Override the user-facing
handlers (cmd_start, cmd_help, cmd_book) for the brief; leave admin.py and
db.py intact so the owner's `/admin` panel keeps working.

SLOT placeholder — the coder MUST fill in a real greeting matching the
brief:
<!-- SLOT:brief.start_greeting -->
"""
import asyncio
import logging
import os
import sys

from aiogram import Bot, Dispatcher
from aiogram.filters import Command, CommandStart
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message
from dotenv import load_dotenv

import admin
import db
from middleware import UserRegisterMiddleware

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("af-bot")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
BOT_USERNAME = os.getenv("BOT_USERNAME", "").strip()
OWNER_TG_ID = os.getenv("OWNER_TG_ID", "0").strip()

if not BOT_TOKEN:
    logger.error("BOT_TOKEN is empty — refusing to start. Check .env.")
    sys.exit(1)

if OWNER_TG_ID == "0" or not OWNER_TG_ID:
    logger.warning(
        "OWNER_TG_ID is not set — /admin will reject everyone until the platform "
        "injects the creator's Telegram ID."
    )

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
dp.update.outer_middleware(UserRegisterMiddleware())
dp.include_router(admin.router)


@dp.message(CommandStart())
async def cmd_start(msg: Message) -> None:
    # <!-- SLOT:brief.start_greeting -->
    # The coder agent replaces this body with brief-specific copy. Keep the
    # SLOT marker so the gate detects unfilled placeholders.
    await msg.answer(
        "Привет! Я бот на AgentFlow. Напиши /help чтобы посмотреть команды."
    )


@dp.message(Command("help"))
async def cmd_help(msg: Message) -> None:
    await msg.answer(
        "Доступные команды:\n"
        "/start — приветствие\n"
        "/book — оставить заявку\n"
        "/help — это сообщение\n"
    )


@dp.message(Command("book"))
async def cmd_book(msg: Message) -> None:
    """Generic «оставить заявку» handler. The coder agent rewrites this to
    capture brief-specific fields (date, slot, service, contact). Defaults
    to a single-message capture for the MVP."""
    if msg.from_user is None:
        return
    payload = {"raw_text": msg.text or ""}
    booking_id = db.add_booking(user_id=msg.from_user.id, payload=payload)
    await msg.answer(
        f"Заявка #{booking_id} принята. С тобой свяжутся."
    )


async def main() -> None:
    db.init_db()
    logger.info("Starting bot @%s (owner=%s)", BOT_USERNAME or "<unknown>", OWNER_TG_ID or "<unset>")
    # Clear any webhook before long-polling. A bot previously wired to a webhook
    # (an earlier platform /connect-telegram integration, or a prior deploy) makes
    # getUpdates fail with TelegramConflictError ("can't use getUpdates while
    # webhook is active") and the bot never receives messages. delete_webhook
    # makes the switch to polling deterministic for any token.
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
