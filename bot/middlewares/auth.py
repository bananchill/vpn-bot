"""Authentication middleware — injects user object into handler context."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from bot.db.base import async_session_factory
from bot.db.repositories.user_repo import UserRepository

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseMiddleware):
    """Get or create user on every message/callback and inject into handler data.

    Adds to handler kwargs:
        - ``user``: the ``User`` ORM instance
        - ``db_session``: the ``AsyncSession`` (auto-committed on success)
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        # Extract telegram user from the event
        tg_user = None
        if (isinstance(event, (Message, CallbackQuery))) and event.from_user:
            tg_user = event.from_user

        if tg_user is None:
            return await handler(event, data)

        async with async_session_factory() as session, session.begin():
            user_repo = UserRepository(session)
            user = await user_repo.get_or_create(
                telegram_id=tg_user.id,
                username=tg_user.username,
            )
            data["user"] = user
            data["db_session"] = session
            result = await handler(event, data)

        return result
