"""Admin initialization handler — /admin command with FSM."""

from __future__ import annotations

import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from bot.config import settings
from bot.db.base import async_session_factory
from bot.db.repositories.admin_session_repo import AdminSessionRepository
from bot.db.repositories.user_repo import UserRepository
from bot.services.crypto import encrypt_credentials
from bot.services.xui_client import XUIAuthError, XUIClient, XUIConnectionError

logger = logging.getLogger(__name__)

router = Router(name="admin")


# ---------------------------------------------------------------------------
# FSM states
# ---------------------------------------------------------------------------


class AdminLoginStates(StatesGroup):
    """States for the admin login flow."""

    waiting_for_login = State()
    waiting_for_password = State()


# ---------------------------------------------------------------------------
# /admin command
# ---------------------------------------------------------------------------


@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext) -> None:
    """Start the admin initialization flow.

    The FSM remains as a fallback for manual credential entry.
    Primary configuration should be done through the admin mini-app.
    """
    await state.clear()
    await state.set_state(AdminLoginStates.waiting_for_login)
    await message.answer(
        "Настройки панели также доступны через мини-апп.\n\n"
        "Введите логин от панели 3x-ui:"
    )


# ---------------------------------------------------------------------------
# Step 1: receive login
# ---------------------------------------------------------------------------


@router.message(AdminLoginStates.waiting_for_login, F.text)
async def process_login(message: Message, state: FSMContext) -> None:
    """Store the login and ask for the password."""
    login_text = message.text.strip()
    if not login_text:
        await message.answer("Логин не может быть пустым. Попробуйте ещё раз:")
        return

    await state.update_data(panel_login=login_text)
    await state.set_state(AdminLoginStates.waiting_for_password)
    await message.answer(
        "Введите пароль от панели 3x-ui:\n"
        "(сообщение с паролем будет удалено после прочтения)"
    )


# ---------------------------------------------------------------------------
# Step 2: receive password, attempt login
# ---------------------------------------------------------------------------


@router.message(AdminLoginStates.waiting_for_password, F.text)
async def process_password(message: Message, state: FSMContext, bot: Bot) -> None:
    """Attempt to log in to the 3x-ui panel and finalize admin setup."""
    password_text = message.text.strip()

    # Delete the password message immediately for security
    try:
        await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    except Exception:
        logger.warning("Could not delete password message (chat_id=%s)", message.chat.id)

    if not password_text:
        await message.answer("Пароль не может быть пустым. Попробуйте ещё раз:")
        return

    data = await state.get_data()
    panel_login: str = data["panel_login"]
    panel_url = settings.PANEL_URL

    # Attempt login against the panel
    status_msg = await message.answer("Подключаюсь к панели...")

    try:
        async with XUIClient(panel_url) as xui:
            await xui.login(panel_login, password_text)
    except XUIAuthError:
        await status_msg.edit_text(
            "Неверный логин или пароль. Попробуйте снова.\n"
            "Введите логин от панели 3x-ui:"
        )
        await state.set_state(AdminLoginStates.waiting_for_login)
        return
    except XUIConnectionError as exc:
        logger.error("Panel connection error: %s", exc)
        await status_msg.edit_text(
            "Не удалось подключиться к панели. Проверьте доступность сервера.\n"
            "Введите логин от панели 3x-ui:"
        )
        await state.set_state(AdminLoginStates.waiting_for_login)
        return

    # Success — persist admin in the database
    encrypted = encrypt_credentials(panel_login, password_text)

    async with async_session_factory() as session, session.begin():
            user_repo = UserRepository(session)
            admin_repo = AdminSessionRepository(session)

            user = await user_repo.get_or_create(
                telegram_id=message.from_user.id,
                username=message.from_user.username,
            )
            await user_repo.set_admin(telegram_id=message.from_user.id)

            await admin_repo.upsert(
                user_id=user.id,
                panel_url=panel_url,
                encrypted_credentials=encrypted,
            )

    await status_msg.edit_text(
        "Вы успешно авторизованы как администратор!\n"
        f"Панель: {panel_url}"
    )
    await state.clear()
    logger.info(
        "User %s (%s) registered as admin",
        message.from_user.id,
        message.from_user.username,
    )


# ---------------------------------------------------------------------------
# Fallback: non-text messages in FSM states
# ---------------------------------------------------------------------------


@router.message(AdminLoginStates.waiting_for_login)
async def login_not_text(message: Message) -> None:
    """Handle non-text input when expecting login."""
    await message.answer("Пожалуйста, отправьте логин текстовым сообщением.")


@router.message(AdminLoginStates.waiting_for_password)
async def password_not_text(message: Message) -> None:
    """Handle non-text input when expecting password."""
    await message.answer("Пожалуйста, отправьте пароль текстовым сообщением.")
