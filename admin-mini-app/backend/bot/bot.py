"""Minimal aiogram bot: sends a WebAppInfo button on /start.

This bot exists solely to provide the entry point for opening the
Telegram Mini App. No other handlers, FSM, or inline keyboards.
"""

import asyncio
import logging

from aiogram import Bot, Dispatcher, Router
from aiogram.filters import CommandStart
from aiogram.types import (
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    WebAppInfo,
)
from config import ADMIN_BOT_TOKEN, WEBAPP_URL

logger = logging.getLogger(__name__)

router = Router()

bot = Bot(token=ADMIN_BOT_TOKEN)
dp = Dispatcher()
dp.include_router(router)


@router.message(CommandStart())
async def handle_start(message: Message) -> None:
    """Send a reply keyboard with a button that opens the admin Mini App."""
    webapp_button = KeyboardButton(
        text="Open Admin Panel",
        web_app=WebAppInfo(url=WEBAPP_URL),
    )
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[webapp_button]],
        resize_keyboard=True,
    )
    await message.answer(
        "Welcome to the Admin Panel bot. Tap the button below to open the admin interface.",
        reply_markup=keyboard,
    )


_RETRY_DELAY_SECONDS = 5


async def start_polling() -> None:
    """Start the bot's long-polling loop with automatic retry.

    Called as a background task during FastAPI lifespan startup.
    Retries indefinitely on transient errors (network issues, Telegram
    API downtime) with a short delay between attempts.
    """
    while True:
        try:
            logger.info("Starting admin bot polling")
            await dp.start_polling(bot)
            # start_polling returns normally when stop_polling is called
            break
        except Exception:
            logger.exception(
                "Bot polling failed, retrying in %d seconds",
                _RETRY_DELAY_SECONDS,
            )
            await asyncio.sleep(_RETRY_DELAY_SECONDS)


async def stop_polling() -> None:
    """Gracefully shut down the bot polling."""
    logger.info("Stopping admin bot polling")
    await dp.stop_polling()
    await bot.session.close()
