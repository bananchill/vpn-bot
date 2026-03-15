"""Bot entry point."""

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import settings
from bot.db.base import async_session_factory
from bot.handlers.admin import router as admin_router
from bot.handlers.config import router as config_router
from bot.handlers.owner import router as owner_router
from bot.handlers.payment import router as payment_router
from bot.handlers.start import router as start_router
from bot.middlewares.auth import AuthMiddleware
from bot.scheduler import scheduler, setup_scheduler

logger = logging.getLogger(__name__)

SETTINGS_RETRY_INTERVAL = 30  # seconds between retries


async def _load_settings_from_db() -> None:
    """Load bot settings from ``bot_settings`` DB table.

    Retries every 30 seconds until a valid row with ``client_bot_token`` is
    found, preventing crash-loops when the admin hasn't configured the bot yet.
    """
    from cryptography.fernet import Fernet
    from sqlalchemy import select

    from bot.db.models import BotSettingsRecord

    if not settings.FERNET_KEY:
        raise RuntimeError(
            "FERNET_KEY is not set. Cannot decrypt bot settings from DB."
        )

    fernet = Fernet(settings.FERNET_KEY.encode())

    while True:
        async with async_session_factory() as session:
            row = await session.scalar(
                select(BotSettingsRecord).where(BotSettingsRecord.id == 1)
            )

        if row and row.client_bot_token:
            break

        logger.warning(
            "bot_settings row not found or client_bot_token is empty. "
            "Retrying in %ds...",
            SETTINGS_RETRY_INTERVAL,
        )
        await asyncio.sleep(SETTINGS_RETRY_INTERVAL)

    # Decrypt sensitive fields
    settings.BOT_TOKEN = fernet.decrypt(row.client_bot_token.encode()).decode()

    if row.panel_password:
        settings.PANEL_PASSWORD = fernet.decrypt(row.panel_password.encode()).decode()

    # Copy plaintext fields
    if row.panel_url:
        settings.PANEL_URL = row.panel_url
    if row.panel_sub_url:
        settings.PANEL_SUB_URL = row.panel_sub_url
    if row.panel_username:
        settings.PANEL_USERNAME = row.panel_username
    if row.owner_id:
        settings.OWNER_ID = row.owner_id

    logger.info("Bot settings loaded from DB (panel_url=%s)", settings.PANEL_URL)


async def _main() -> None:
    logging.basicConfig(level=logging.INFO)

    await _load_settings_from_db()

    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # Register auth middleware on all event types
    dp.message.middleware(AuthMiddleware())
    dp.callback_query.middleware(AuthMiddleware())
    dp.pre_checkout_query.middleware(AuthMiddleware())

    # Include routers (order matters — owner first for highest priority)
    dp.include_router(owner_router)
    dp.include_router(payment_router)
    dp.include_router(admin_router)
    dp.include_router(start_router)
    dp.include_router(config_router)

    # Start the background scheduler for periodic tasks (expiry notifications)
    setup_scheduler(bot, async_session_factory)
    scheduler.start()

    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)


def main() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    main()
