"""Hidden owner commands for admin management.

These commands are only accessible to the bot owner (OWNER_ID).
They are not registered via set_my_commands, so they stay invisible
in the Telegram command menu.

Note: /setadmin, /rmadmin, /admins are deprecated since TASK-018.
Admin management is now handled through the admin mini-app.
"""

from __future__ import annotations

import logging

from aiogram import Router
from aiogram.filters import Command, Filter
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import settings
from bot.db.repositories.promo_code_repo import PromoCodeRepository

logger = logging.getLogger(__name__)

router = Router(name="owner")

# Unified deprecation message — admin management moved to the mini-app (TASK-018)
_DEPRECATED_MSG = (
    "Управление администраторами перенесено в мини-апп.\n"
    "Используйте админ-панель для добавления и удаления администраторов."
)


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
# /setadmin (deprecated — TASK-018)
# ---------------------------------------------------------------------------


@router.message(Command("setadmin"))
async def cmd_set_admin(message: Message) -> None:
    """Deprecated: admin management moved to mini-app."""
    await message.answer(_DEPRECATED_MSG)


# ---------------------------------------------------------------------------
# /rmadmin (deprecated — TASK-018)
# ---------------------------------------------------------------------------


@router.message(Command("rmadmin"))
async def cmd_rm_admin(message: Message) -> None:
    """Deprecated: admin management moved to mini-app."""
    await message.answer(_DEPRECATED_MSG)


# ---------------------------------------------------------------------------
# /admins (deprecated — TASK-018)
# ---------------------------------------------------------------------------


@router.message(Command("admins"))
async def cmd_admins(message: Message) -> None:
    """Deprecated: admin management moved to mini-app."""
    await message.answer(_DEPRECATED_MSG)


# ---------------------------------------------------------------------------
# /promo create|list|disable
# ---------------------------------------------------------------------------


@router.message(Command("promo"))
async def cmd_promo(message: Message, db_session: AsyncSession) -> None:
    """Manage promo codes: create, list, or disable.

    Usage:
        /promo create <code>
        /promo list
        /promo disable <code>
    """
    raw_arg = _extract_arg(message.text)

    if raw_arg is _MISSING:
        await message.answer(
            "Использование:\n"
            "/promo create <code> — создать промокод\n"
            "/promo list — список промокодов\n"
            "/promo disable <code> — деактивировать промокод"
        )
        return

    parts = str(raw_arg).split(maxsplit=1)
    subcommand = parts[0].lower()
    arg = parts[1].strip() if len(parts) > 1 else ""

    if subcommand == "create":
        await _promo_create(message, arg, db_session)
    elif subcommand == "list":
        await _promo_list(message, db_session)
    elif subcommand == "disable":
        await _promo_disable(message, arg, db_session)
    else:
        await message.answer(
            f"Неизвестная подкоманда: {subcommand}\n"
            "Доступные: create, list, disable"
        )


async def _promo_create(
    message: Message, code: str, db_session: AsyncSession
) -> None:
    """Create a new promo code."""
    if not code:
        await message.answer("Использование: /promo create <code>")
        return

    repo = PromoCodeRepository(db_session)
    existing = await repo.get_by_code(code)
    if existing is not None:
        await message.answer(f"Промокод «{code.lower()}» уже существует.")
        return

    promo = await repo.create(code)
    await message.answer(f"Промокод «{promo.code}» создан.")
    logger.info("Owner created promo code: %s", promo.code)


async def _promo_list(message: Message, db_session: AsyncSession) -> None:
    """List all promo codes with stats."""
    repo = PromoCodeRepository(db_session)
    promos = await repo.list_all()

    if not promos:
        await message.answer("Промокодов нет.")
        return

    lines: list[str] = ["Промокоды:"]
    for p in promos:
        status = "активен" if p.is_active else "деактивирован"
        lines.append(f"  - {p.code} ({status}, использован: {p.use_count})")

    await message.answer("\n".join(lines))


async def _promo_disable(
    message: Message, code: str, db_session: AsyncSession
) -> None:
    """Deactivate a promo code."""
    if not code:
        await message.answer("Использование: /promo disable <code>")
        return

    repo = PromoCodeRepository(db_session)
    deactivated = await repo.deactivate(code)
    if not deactivated:
        await message.answer(f"Промокод «{code.lower()}» не найден.")
        return

    await message.answer(f"Промокод «{code.lower()}» деактивирован.")
    logger.info("Owner disabled promo code: %s", code.lower())
