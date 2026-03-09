"""Repository for reading admin records from the shared ``admins`` table.

The ``admins`` table is the single source of truth for administrator
identity (TASK-018).  This repository provides read-only access from
the bot side; writes are handled by the admin-mini-app.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import AdminRecord


class AdminRecordRepository:
    """Data-access layer for the ``admins`` table (read-only from bot)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def exists_by_telegram_id(self, telegram_id: int) -> bool:
        """Check whether a given Telegram user is registered as an admin.

        Returns True if a row exists in the ``admins`` table for the
        given ``telegram_id``, regardless of role.
        """
        stmt = (
            select(AdminRecord.id)
            .where(AdminRecord.telegram_id == telegram_id)
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def get_by_telegram_id(
        self, telegram_id: int
    ) -> AdminRecord | None:
        """Return the admin record for a Telegram user, or None."""
        stmt = select(AdminRecord).where(
            AdminRecord.telegram_id == telegram_id
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
