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


async def _main() -> None:
    logging.basicConfig(level=logging.INFO)

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
