"""Start command handler — /start and main menu."""

from __future__ import annotations

import logging

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

from bot.db.models import User
from bot.keyboards.menus import main_menu

logger = logging.getLogger(__name__)

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message, user: User) -> None:
    """Handle /start command — greet user and show main menu."""
    name = message.from_user.username or message.from_user.first_name or "пользователь"
    await message.answer(
        f"Привет, {name}!\n"
        "Я помогу управлять VPN-конфигурациями.\n"
        "Выберите действие:",
        reply_markup=main_menu(),
    )
    logger.info("User %s (%s) started the bot", user.telegram_id, name)


@router.callback_query(lambda c: c.data == "back_to_main")
async def back_to_main(callback: CallbackQuery, user: User) -> None:
    """Return to main menu."""
    await callback.message.edit_text(
        "Выберите действие:",
        reply_markup=main_menu(),
    )
    await callback.answer()
