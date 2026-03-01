"""Config CRUD handler — create, list, view, delete VPN configs."""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import settings
from bot.db.repositories.config_repo import ConfigRepository
from bot.dto import UserDTO
from bot.keyboards.menus import config_detail_menu, config_list, confirm_delete, main_menu
from bot.keyboards.reply import BTN_CREATE_CONFIG, BTN_MY_CONFIGS
from bot.services.vpn_service import (
    ConfigLinks,
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


def _format_links(links: ConfigLinks) -> str:
    """Format both VPN links into a user-facing HTML message block."""
    return (
        f"Прямая ссылка (один конфиг):\n"
        f"<code>{links.vless_link}</code>\n\n"
        f"Ссылка-подписка (все конфиги):\n"
        f"<code>{links.subscription_url}</code>"
    )


async def _get_xui_client() -> XUIClient:
    """Get an authenticated XUI client using credentials from settings."""
    xui = XUIClient(settings.PANEL_URL)
    await xui.login(settings.PANEL_USERNAME, settings.PANEL_PASSWORD)
    return xui


# ---------------------------------------------------------------------------
# Reply keyboard handlers.
# StateFilter(None) ensures these fire ONLY when no FSM state is active.
# When the user is in waiting_for_name, these filters do not match and the
# FSM handler (ConfigCreateStates.waiting_for_name) takes priority automatically.
# ---------------------------------------------------------------------------


@router.message(F.text == BTN_CREATE_CONFIG, StateFilter(None))
async def reply_create_config(
    message: Message,
    state: FSMContext,
    user: UserDTO,
) -> None:
    """Handle 'Создать конфиг' reply button — start config creation FSM."""
    await state.set_state(ConfigCreateStates.waiting_for_name)
    await message.answer(
        "Введите название для нового конфига:\n"
        "(латинские буквы, цифры, дефис или подчёркивание — без пробелов)"
    )


@router.message(F.text == BTN_MY_CONFIGS, StateFilter(None))
async def reply_my_configs(
    message: Message,
    user: UserDTO,
    db_session: AsyncSession,
) -> None:
    """Handle 'Мои конфиги' reply button — show user's config list."""
    config_repo = ConfigRepository(db_session)
    configs = await config_repo.get_by_user_id(user.id)

    if not configs:
        await message.answer(
            "У вас пока нет конфигов.",
            reply_markup=main_menu(),
        )
        return

    items = [(c.id, c.email) for c in configs]
    await message.answer(
        "Ваши конфиги:",
        reply_markup=config_list(items),
    )


# ---------------------------------------------------------------------------
# Create config flow
# ---------------------------------------------------------------------------


@router.callback_query(F.data == "create_config")
async def start_create_config(
    callback: CallbackQuery,
    state: FSMContext,
    user: UserDTO,
) -> None:
    """Start the config creation flow — ask for a name."""
    await state.set_state(ConfigCreateStates.waiting_for_name)
    await callback.message.edit_text(
        "Введите название для нового конфига:\n"
        "(латинские буквы, цифры, дефис или подчёркивание — без пробелов)"
    )
    await callback.answer()


@router.message(ConfigCreateStates.waiting_for_name, F.text)
async def process_config_name(
    message: Message,
    state: FSMContext,
    user: UserDTO,
    db_session: AsyncSession,
) -> None:
    """Receive config name and create the config on the panel."""
    # 3x-ui panel rejects uppercase in the email field, so normalize to lowercase
    name = message.text.strip().lower()

    # Validate name
    if not name or not name.replace("-", "").replace("_", "").isalnum():
        await message.answer(
            "Некорректное название. Используйте латинские буквы, цифры, дефис или подчёркивание.\n"
            "Попробуйте ещё раз:"
        )
        return

    # Guard: enforce per-user config limit before hitting the panel
    config_repo = ConfigRepository(db_session)
    config_count = await config_repo.count_by_user_id(user.id)
    max_configs = settings.MAX_CONFIGS_PER_USER
    if config_count >= max_configs:
        await message.answer(
            f"Достигнут лимит конфигов ({max_configs}/{max_configs}). "
            "Удалите старый конфиг, чтобы создать новый.",
            reply_markup=main_menu(),
        )
        await state.clear()
        return

    status_msg = await message.answer("Создаю конфиг...")

    try:
        xui = await _get_xui_client()
        try:
            links = await create_config(
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
            f"{_format_links(links)}",
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
    user: UserDTO,
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
    user: UserDTO,
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
    user: UserDTO,
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
        xui = await _get_xui_client()
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
        return

    await callback.answer()


# ---------------------------------------------------------------------------
# Get link
# ---------------------------------------------------------------------------


@router.callback_query(F.data.regexp(r"^config:(\d+):link$"))
async def show_link(
    callback: CallbackQuery,
    user: UserDTO,
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
        xui = await _get_xui_client()
        try:
            links = await get_config_link(config.id, xui, db_session)
        finally:
            await xui.close()

        await callback.message.edit_text(
            f"Ссылка для «{config.email}»:\n\n"
            f"{_format_links(links)}",
            parse_mode="HTML",
            reply_markup=config_detail_menu(config.id),
        )
    except XUIError as exc:
        logger.error("Failed to get link: %s", exc)
        await callback.answer("Ошибка при генерации ссылки.", show_alert=True)
        return

    await callback.answer()


# ---------------------------------------------------------------------------
# Refresh config
# ---------------------------------------------------------------------------


@router.callback_query(F.data.regexp(r"^config:(\d+):refresh$"))
async def refresh_config(
    callback: CallbackQuery,
    user: UserDTO,
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
        xui = await _get_xui_client()
        try:
            links = await get_config_link(config.id, xui, db_session)
        finally:
            await xui.close()

        await callback.message.edit_text(
            f"Конфиг «{config.email}» обновлён.\n\n"
            f"{_format_links(links)}",
            parse_mode="HTML",
            reply_markup=config_detail_menu(config.id),
        )
    except XUIError as exc:
        logger.error("Failed to refresh config: %s", exc)
        await callback.answer("Ошибка при обновлении конфига.", show_alert=True)
        return

    await callback.answer()


# ---------------------------------------------------------------------------
# Delete config
# ---------------------------------------------------------------------------


@router.callback_query(F.data.regexp(r"^config:(\d+):delete$"))
async def ask_delete_config(
    callback: CallbackQuery,
    user: UserDTO,
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
    user: UserDTO,
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
        xui = await _get_xui_client()
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
        return

    await callback.answer()
