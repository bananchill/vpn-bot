"""Bot entry point."""

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import settings
from bot.handlers.admin import router as admin_router
from bot.handlers.config import router as config_router
from bot.handlers.start import router as start_router
from bot.middlewares.auth import AuthMiddleware


async def _main() -> None:
    logging.basicConfig(level=logging.INFO)

    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # Register auth middleware on all event types
    dp.message.middleware(AuthMiddleware())
    dp.callback_query.middleware(AuthMiddleware())

    # Include routers (order matters for FSM)
    dp.include_router(admin_router)
    dp.include_router(start_router)
    dp.include_router(config_router)

    await dp.start_polling(bot)


def main() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    main()
