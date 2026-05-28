"""Track every interacting user in the SQLite `users` table.

Registered as an outer middleware on the dispatcher so it fires once per
update regardless of which handler ultimately serves the message. This
feeds `db.stats_snapshot()` and the broadcast recipient list.
"""
from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User

import db

logger = logging.getLogger("af-bot.middleware")


def _extract_user(event: TelegramObject) -> User | None:
    user = getattr(event, "from_user", None)
    if user is not None:
        return user
    # CallbackQuery wraps the message — fall through if no from_user.
    inner = getattr(event, "message", None)
    if inner is not None:
        return getattr(inner, "from_user", None)
    return None


class UserRegisterMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = _extract_user(event)
        if user is not None and not user.is_bot:
            try:
                db.upsert_user(
                    telegram_id=user.id,
                    username=user.username,
                    first_name=user.first_name,
                )
            except Exception as e:  # noqa: BLE001 — never block handler
                logger.warning("upsert_user failed for %s: %s", user.id, e)
        return await handler(event, data)
