"""Config CRUD handler — create, list, view, delete VPN configs."""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import settings
from bot.db.models import User
from bot.db.repositories.config_repo import ConfigRepository
from bot.keyboards.menus import config_detail_menu, config_list, confirm_delete, main_menu
from bot.services.crypto import decrypt_credentials
from bot.services.vpn_service import (
    create_config,
    delete_config,
    get_config_link,
    get_config_traffic,
)
from bot.services.xui_client import XUIClient, XUIError

logger = logging.getLogger(__name__)

router = Router(name="config")


# ---------------------------------------------------------------------------
# FSM states
# ---------------------------------------------------------------------------


class ConfigCreateStates(StatesGroup):
    """States for config creation flow."""

    waiting_for_name = State()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_xui_client(session: AsyncSession) -> XUIClient | None:
    """Get an authenticated XUI client using admin credentials from DB.

    Returns None if no admin session is configured.
    """
    # Use the first available admin session
    from sqlalchemy import select

    from bot.db.models import AdminSession

    stmt = select(AdminSession).limit(1)
    result = await session.execute(stmt)
    admin_session = result.scalar_one_or_none()

    if admin_session is None:
        return None

    creds = decrypt_credentials(admin_session.encrypted_credentials)
    xui = XUIClient(admin_session.panel_url)
    await xui.login(creds["username"], creds["password"])
    return xui


# ---------------------------------------------------------------------------
# Create config flow
# ---------------------------------------------------------------------------


@router.callback_query(F.data == "create_config")
async def start_create_config(
    callback: CallbackQuery,
    state: FSMContext,
    user: User,
) -> None:
    """Start the config creation flow — ask for a name."""
    await state.set_state(ConfigCreateStates.waiting_for_name)
    await callback.message.edit_text(
        "Введите название для нового конфига:\n"
        "(латинские буквы, цифры, без пробелов)"
    )
    await callback.answer()


@router.message(ConfigCreateStates.waiting_for_name, F.text)
async def process_config_name(
    message: Message,
    state: FSMContext,
    user: User,
    db_session: AsyncSession,
) -> None:
    """Receive config name and create the config on the panel."""
    name = message.text.strip()

    # Validate name
    if not name or not name.replace("-", "").replace("_", "").isalnum():
        await message.answer(
            "Некорректное название. Используйте латинские буквы, цифры, дефис или подчёркивание.\n"
            "Попробуйте ещё раз:"
        )
        return

    status_msg = await message.answer("Создаю конфиг...")

    try:
        xui = await _get_xui_client(db_session)
        if xui is None:
            await status_msg.edit_text(
                "Администратор ещё не настроил подключение к панели.\n"
                "Обратитесь к администратору.",
                reply_markup=main_menu(),
            )
            await state.clear()
            return

        try:
            link = await create_config(
                user_id=user.id,
                name=name,
                inbound_id=settings.DEFAULT_INBOUND_ID,
                xui=xui,
                session=db_session,
            )
        finally:
            await xui.close()

        await status_msg.edit_text(
            f"Конфиг «{name}» создан!\n\n"
            f"Ссылка для подключения:\n<code>{link}</code>",
            parse_mode="HTML",
            reply_markup=main_menu(),
        )
    except XUIError as exc:
        logger.error("Failed to create config: %s", exc)
        await status_msg.edit_text(
            "Ошибка при создании конфига. Попробуйте позже.",
            reply_markup=main_menu(),
        )
    except Exception:
        logger.exception("Unexpected error creating config")
        await status_msg.edit_text(
            "Произошла непредвиденная ошибка.",
            reply_markup=main_menu(),
        )

    await state.clear()


@router.message(ConfigCreateStates.waiting_for_name)
async def config_name_not_text(message: Message) -> None:
    """Handle non-text input when expecting config name."""
    await message.answer("Пожалуйста, отправьте название текстовым сообщением.")


# ---------------------------------------------------------------------------
# List configs
# ---------------------------------------------------------------------------


@router.callback_query(F.data == "my_configs")
async def list_configs(
    callback: CallbackQuery,
    user: User,
    db_session: AsyncSession,
) -> None:
    """Show list of user's configs."""
    config_repo = ConfigRepository(db_session)
    configs = await config_repo.get_by_user_id(user.id)

    if not configs:
        await callback.message.edit_text(
            "У вас пока нет конфигов.",
            reply_markup=main_menu(),
        )
        await callback.answer()
        return

    items = [(c.id, c.email) for c in configs]
    await callback.message.edit_text(
        "Ваши конфиги:",
        reply_markup=config_list(items),
    )
    await callback.answer()


# ---------------------------------------------------------------------------
# Config detail
# ---------------------------------------------------------------------------


@router.callback_query(F.data.regexp(r"^config:(\d+):detail$"))
async def show_config_detail(
    callback: CallbackQuery,
    user: User,
    db_session: AsyncSession,
) -> None:
    """Show detail menu for a specific config."""
    config_id = int(callback.data.split(":")[1])
    config_repo = ConfigRepository(db_session)
    config = await config_repo.get_by_id(config_id)

    if config is None or config.user_id != user.id:
        await callback.answer("Конфиг не найден.", show_alert=True)
        return

    await callback.message.edit_text(
        f"Конфиг: {config.email}\n"
        f"Протокол: {config.protocol}\n"
        f"Создан: {config.created_at.strftime('%d.%m.%Y %H:%M')}",
        reply_markup=config_detail_menu(config.id),
    )
    await callback.answer()


# ---------------------------------------------------------------------------
# Traffic stats
# ---------------------------------------------------------------------------


@router.callback_query(F.data.regexp(r"^config:(\d+):traffic$"))
async def show_traffic(
    callback: CallbackQuery,
    user: User,
    db_session: AsyncSession,
) -> None:
    """Show traffic stats for a config."""
    config_id = int(callback.data.split(":")[1])
    config_repo = ConfigRepository(db_session)
    config = await config_repo.get_by_id(config_id)

    if config is None or config.user_id != user.id:
        await callback.answer("Конфиг не найден.", show_alert=True)
        return

    try:
        xui = await _get_xui_client(db_session)
        if xui is None:
            await callback.answer("Панель не настроена.", show_alert=True)
            return

        try:
            traffic = await get_config_traffic(config.email, xui)
        finally:
            await xui.close()

        await callback.message.edit_text(
            f"Трафик для «{config.email}»:\n\n"
            f"{traffic.format_message()}",
            reply_markup=config_detail_menu(config.id),
        )
    except XUIError as exc:
        logger.error("Failed to get traffic: %s", exc)
        await callback.answer("Ошибка при получении трафика.", show_alert=True)

    await callback.answer()


# ---------------------------------------------------------------------------
# Get link
# ---------------------------------------------------------------------------


@router.callback_query(F.data.regexp(r"^config:(\d+):link$"))
async def show_link(
    callback: CallbackQuery,
    user: User,
    db_session: AsyncSession,
) -> None:
    """Generate and show connection link for a config."""
    config_id = int(callback.data.split(":")[1])
    config_repo = ConfigRepository(db_session)
    config = await config_repo.get_by_id(config_id)

    if config is None or config.user_id != user.id:
        await callback.answer("Конфиг не найден.", show_alert=True)
        return

    try:
        xui = await _get_xui_client(db_session)
        if xui is None:
            await callback.answer("Панель не настроена.", show_alert=True)
            return

        try:
            link = await get_config_link(config.id, xui, db_session)
        finally:
            await xui.close()

        await callback.message.edit_text(
            f"Ссылка для «{config.email}»:\n\n"
            f"<code>{link}</code>",
            parse_mode="HTML",
            reply_markup=config_detail_menu(config.id),
        )
    except XUIError as exc:
        logger.error("Failed to get link: %s", exc)
        await callback.answer("Ошибка при генерации ссылки.", show_alert=True)

    await callback.answer()


# ---------------------------------------------------------------------------
# Refresh config
# ---------------------------------------------------------------------------


@router.callback_query(F.data.regexp(r"^config:(\d+):refresh$"))
async def refresh_config(
    callback: CallbackQuery,
    user: User,
    db_session: AsyncSession,
) -> None:
    """Refresh config — fetch fresh link from panel."""
    config_id = int(callback.data.split(":")[1])
    config_repo = ConfigRepository(db_session)
    config = await config_repo.get_by_id(config_id)

    if config is None or config.user_id != user.id:
        await callback.answer("Конфиг не найден.", show_alert=True)
        return

    try:
        xui = await _get_xui_client(db_session)
        if xui is None:
            await callback.answer("Панель не настроена.", show_alert=True)
            return

        try:
            link = await get_config_link(config.id, xui, db_session)
        finally:
            await xui.close()

        await callback.message.edit_text(
            f"Конфиг «{config.email}» обновлён.\n\n"
            f"Ссылка:\n<code>{link}</code>",
            parse_mode="HTML",
            reply_markup=config_detail_menu(config.id),
        )
    except XUIError as exc:
        logger.error("Failed to refresh config: %s", exc)
        await callback.answer("Ошибка при обновлении конфига.", show_alert=True)

    await callback.answer()


# ---------------------------------------------------------------------------
# Delete config
# ---------------------------------------------------------------------------


@router.callback_query(F.data.regexp(r"^config:(\d+):delete$"))
async def ask_delete_config(
    callback: CallbackQuery,
    user: User,
    db_session: AsyncSession,
) -> None:
    """Ask for delete confirmation."""
    config_id = int(callback.data.split(":")[1])
    config_repo = ConfigRepository(db_session)
    config = await config_repo.get_by_id(config_id)

    if config is None or config.user_id != user.id:
        await callback.answer("Конфиг не найден.", show_alert=True)
        return

    await callback.message.edit_text(
        f"Вы уверены, что хотите удалить конфиг «{config.email}»?\n"
        "Это действие нельзя отменить.",
        reply_markup=confirm_delete(config.id),
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^config:(\d+):confirm_delete$"))
async def confirm_delete_config(
    callback: CallbackQuery,
    user: User,
    db_session: AsyncSession,
) -> None:
    """Delete config after confirmation."""
    config_id = int(callback.data.split(":")[1])
    config_repo = ConfigRepository(db_session)
    config = await config_repo.get_by_id(config_id)

    if config is None or config.user_id != user.id:
        await callback.answer("Конфиг не найден.", show_alert=True)
        return

    try:
        xui = await _get_xui_client(db_session)
        if xui is None:
            await callback.answer("Панель не настроена.", show_alert=True)
            return

        try:
            await delete_config(config.id, xui, db_session)
        finally:
            await xui.close()

        await callback.message.edit_text(
            f"Конфиг «{config.email}» удалён.",
            reply_markup=main_menu(),
        )
    except XUIError as exc:
        logger.error("Failed to delete config: %s", exc)
        await callback.answer("Ошибка при удалении конфига.", show_alert=True)

    await callback.answer()
