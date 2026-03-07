"""FastAPI dependency injection providers.

Provides database sessions and the authenticated admin user for route handlers.
"""

import logging
from collections.abc import AsyncGenerator
from typing import Annotated

from config import ADMIN_BOT_TOKEN, DEV_ADMIN_ID, DEV_MODE
from db.engine import async_session_factory
from db.models import Admin
from db.repositories import admin_repo
from db.repositories import user_repo as bot_user_repo
from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import validate_init_data

logger = logging.getLogger(__name__)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session that auto-closes after the request."""
    async with async_session_factory() as session, session.begin():
        yield session


def _extract_username(user_data: dict[str, str | int]) -> str | None:
    """Extract the Telegram username from parsed initData user object."""
    raw = user_data.get("username")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return None


async def get_current_admin(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Admin:
    """Validate the Telegram initData header and return the authenticated admin.

    On the very first request (zero admins in DB), the requesting user is
    automatically promoted to 'owner'. This enables the initial setup flow
    without manual database intervention.

    In dev mode (ADMIN_DEV_MODE=true), initData validation is skipped and
    a fake admin with DEV_ADMIN_ID is used for local browser testing.

    On every successful authentication the Telegram username is synced from
    initData into the ``Admin.username`` column so it stays up to date.
    """
    username: str | None = None

    if DEV_MODE:
        telegram_id = DEV_ADMIN_ID
        username = "dev_admin"
        logger.debug("Dev mode: using fake admin telegram_id=%d", telegram_id)
    else:
        init_data = request.headers.get("X-Telegram-Init-Data")
        if not init_data:
            raise HTTPException(status_code=401, detail="Missing initData")

        user_data = validate_init_data(init_data, ADMIN_BOT_TOKEN)
        if not user_data:
            raise HTTPException(status_code=401, detail="Invalid initData")

        telegram_id = user_data.get("id")
        if not isinstance(telegram_id, int):
            raise HTTPException(status_code=401, detail="Invalid user data in initData")

        username = _extract_username(user_data)

    admin = await admin_repo.get_by_telegram_id(session, telegram_id)

    if admin is not None:
        # Sync username from initData on every entry
        if username is not None and admin.username != username:
            await admin_repo.update_username(session, admin.id, username)
        return admin

    # Auto-create the first admin as owner when the database is empty
    admin_count = await admin_repo.count(session)
    if admin_count == 0:
        logger.info("No admins found, creating first owner: %d", telegram_id)
        admin = await admin_repo.create(
            session, telegram_id, role="owner", username=username,
        )
        # Set User.is_admin = true in the users table for the bot
        await bot_user_repo.ensure_is_admin(session, telegram_id)
        return admin

    raise HTTPException(status_code=403, detail="Not an admin")
