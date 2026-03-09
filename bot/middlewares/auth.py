"""Authentication middleware — injects user object into handler context.

Performs a two-source admin check (TASK-018):
1. ``User.is_admin`` — fast denormalized flag in the ``users`` table.
2. ``admins`` table — the single source of truth managed by admin-mini-app.

If a user is found in the ``admins`` table but ``User.is_admin`` is
``False``, the middleware promotes ``is_admin`` in the DTO so that
downstream handlers see the correct value within the same request.
The denormalized flag in the DB is **not** updated here to avoid
write contention; the admin-mini-app handles that on first login.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from bot.db.base import async_session_factory
from bot.db.repositories.admin_record_repo import AdminRecordRepository
from bot.db.repositories.user_repo import UserRepository

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseMiddleware):
    """Get or create user on every message/callback and inject into handler data.

    Adds to handler kwargs:
        - ``user``: a ``UserDTO`` (Pydantic, not ORM)
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

            # Fallback admin check: if User.is_admin is False, consult the
            # authoritative ``admins`` table to catch admins added via mini-app.
            if not user.is_admin:
                admin_repo = AdminRecordRepository(session)
                if await admin_repo.exists_by_telegram_id(tg_user.id):
                    # Promote the in-memory DTO so handlers see correct rights
                    user = user.model_copy(update={"is_admin": True})

            data["user"] = user
            data["db_session"] = session
            result = await handler(event, data)

        return result
