"""Start command handler — /start and main menu."""

from __future__ import annotations

import logging

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.dto import UserDTO
from bot.keyboards.menus import main_menu
from bot.keyboards.reply import reply_main_menu
from bot.services import subscription_service

logger = logging.getLogger(__name__)

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message, user: UserDTO, db_session: AsyncSession) -> None:
    """Handle /start command — greet user and show main menu.

    Sends two messages: first sets the persistent reply keyboard under
    the input field, then shows the inline menu for quick navigation.
    For non-admin users, also shows subscription status.
    """
    name = message.from_user.username or message.from_user.first_name or "пользователь"

    # Build subscription status line for non-admin users
    sub_line = ""
    if not user.is_admin:
        sub = await subscription_service.get_active(user.id, db_session)
        if sub is not None:
            expires_str = sub.expires_at.strftime("%d.%m.%Y")
            sub_line = f"\n\u2705 Подписка до {expires_str}"
        else:
            sub_line = "\n\u274c Подписка не активна"

    # First message sets the persistent reply keyboard panel
    await message.answer(
        f"Привет, {name}!\n"
        f"Я помогу управлять VPN-конфигурациями.{sub_line}",
        reply_markup=reply_main_menu(),
    )
    # Second message shows inline buttons for immediate action
    await message.answer(
        "Выберите действие:",
        reply_markup=main_menu(),
    )
    logger.info("User %s (%s) started the bot", user.telegram_id, name)


@router.callback_query(lambda c: c.data == "back_to_main")
async def back_to_main(callback: CallbackQuery, user: UserDTO) -> None:
    """Return to main menu."""
    await callback.message.edit_text(
        "Выберите действие:",
        reply_markup=main_menu(),
    )
    await callback.answer()
