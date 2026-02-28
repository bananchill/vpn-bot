"""Hidden owner commands for admin management.

These commands are only accessible to the bot owner (OWNER_ID).
They are not registered via set_my_commands, so they stay invisible
in the Telegram command menu.
"""

from __future__ import annotations

import logging

from aiogram import Router
from aiogram.filters import Command, Filter
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import settings
from bot.db.repositories.user_repo import UserRepository

logger = logging.getLogger(__name__)

router = Router(name="owner")


# ---------------------------------------------------------------------------
# Owner-only filter
# ---------------------------------------------------------------------------


class IsOwnerFilter(Filter):
    """Allow only the bot owner (OWNER_ID) to trigger the handler."""

    async def __call__(self, message: Message) -> bool:
        if message.from_user is None:
            return False
        return message.from_user.id == settings.OWNER_ID


# Apply the filter to every handler in this router
router.message.filter(IsOwnerFilter())


# ---------------------------------------------------------------------------
# Helper: extract command argument
# ---------------------------------------------------------------------------

# Sentinel to distinguish "missing arg" from "not a number"
_MISSING = object()


def _extract_arg(text: str | None) -> str | object:
    """Return the raw argument string, or _MISSING if absent."""
    if text is None:
        return _MISSING
    parts = text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        return _MISSING
    return parts[1].strip()


# ---------------------------------------------------------------------------
# /setadmin <telegram_id>
# ---------------------------------------------------------------------------


@router.message(Command("setadmin"))
async def cmd_set_admin(message: Message, db_session: AsyncSession) -> None:
    """Promote a user to admin by their Telegram ID."""
    raw_arg = _extract_arg(message.text)

    if raw_arg is _MISSING:
        await message.answer("Использование: /setadmin <telegram_id>")
        return

    try:
        telegram_id = int(raw_arg)  # type: ignore[arg-type]
    except ValueError:
        await message.answer("Ошибка: telegram_id должен быть числом.")
        return

    repo = UserRepository(db_session)

    # Check if user already is an admin before modifying
    existing = await repo.get_by_telegram_id(telegram_id)
    if existing is None:
        await message.answer(
            f"Пользователь {telegram_id} не найден в базе данных.\n"
            "Пользователь должен сначала написать боту."
        )
        return

    if existing.is_admin:
        await message.answer(
            f"Пользователь {telegram_id} уже является администратором."
        )
        return

    await repo.set_admin(telegram_id, is_admin=True)
    await message.answer(
        f"Пользователь {telegram_id} назначен администратором."
    )
    logger.info("Owner set admin: telegram_id=%s", telegram_id)


# ---------------------------------------------------------------------------
# /rmadmin <telegram_id>
# ---------------------------------------------------------------------------


@router.message(Command("rmadmin"))
async def cmd_rm_admin(message: Message, db_session: AsyncSession) -> None:
    """Remove admin privileges from a user by their Telegram ID."""
    raw_arg = _extract_arg(message.text)

    if raw_arg is _MISSING:
        await message.answer("Использование: /rmadmin <telegram_id>")
        return

    try:
        telegram_id = int(raw_arg)  # type: ignore[arg-type]
    except ValueError:
        await message.answer("Ошибка: telegram_id должен быть числом.")
        return

    repo = UserRepository(db_session)

    existing = await repo.get_by_telegram_id(telegram_id)
    if existing is None or not existing.is_admin:
        await message.answer(
            f"Пользователь {telegram_id} не найден или не является администратором."
        )
        return

    await repo.set_admin(telegram_id, is_admin=False)
    await message.answer(
        f"Права администратора сняты с пользователя {telegram_id}."
    )
    logger.info("Owner removed admin: telegram_id=%s", telegram_id)


# ---------------------------------------------------------------------------
# /admins
# ---------------------------------------------------------------------------


@router.message(Command("admins"))
async def cmd_admins(message: Message, db_session: AsyncSession) -> None:
    """List all current admin users."""
    repo = UserRepository(db_session)
    admins = await repo.list_admins()

    if not admins:
        await message.answer("Администраторов нет.")
        return

    lines: list[str] = ["Текущие администраторы:"]
    for admin in admins:
        if admin.username:
            lines.append(f"  - @{admin.username} (ID: {admin.telegram_id})")
        else:
            lines.append(f"  - ID: {admin.telegram_id}")

    await message.answer("\n".join(lines))
