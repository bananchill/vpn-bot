"""Bot entry point."""

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import settings
from bot.handlers.admin import router as admin_router


async def _main() -> None:
    logging.basicConfig(level=logging.INFO)

    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(admin_router)

    await dp.start_polling(bot)


def main() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    main()
