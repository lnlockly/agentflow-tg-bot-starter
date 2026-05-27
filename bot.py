"""AgentFlow Telegram bot starter — aiogram 3.

The platform writes BOT_TOKEN + BOT_USERNAME to .env before starting this
file via `nohup python bot.py`. Override the handlers below with your own
logic; the platform's coder agent will edit /start, /help and add domain
commands based on your brief.

SLOT placeholder — the coder MUST fill in a real greeting matching the brief:
<!-- SLOT:brief.start_greeting -->
"""
import asyncio
import logging
import os
import sys

from aiogram import Bot, Dispatcher
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("af-bot")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
BOT_USERNAME = os.getenv("BOT_USERNAME", "").strip()

if not BOT_TOKEN:
    logger.error("BOT_TOKEN is empty — refusing to start. Check .env.")
    sys.exit(1)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


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
        "/help — это сообщение\n"
    )


async def main() -> None:
    logger.info("Starting bot @%s", BOT_USERNAME or "<unknown>")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
