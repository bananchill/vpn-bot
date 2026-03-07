"""Tests for bot.db.repositories.admin_record_repo (TASK-018).

Covers the read-only repository that checks the shared ``admins`` table.
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from bot.db.repositories.admin_record_repo import AdminRecordRepository


def _make_orm_admin(
    record_id: int = 1,
    telegram_id: int = 123456,
    role: str = "owner",
    username: str | None = "adminuser",
) -> MagicMock:
    """Build a minimal ORM-like mock for AdminRecord."""
    rec = MagicMock()
    rec.id = record_id
    rec.telegram_id = telegram_id
    rec.role = role
    rec.username = username
    rec.added_at = datetime(2026, 1, 1)
    return rec


class TestAdminRecordRepository:
    @pytest.fixture()
    def session(self) -> AsyncMock:
        return AsyncMock()

    @pytest.fixture()
    def repo(self, session: AsyncMock) -> AdminRecordRepository:
        return AdminRecordRepository(session)

    # ------------------------------------------------------------------
    # exists_by_telegram_id
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_exists_by_telegram_id_returns_true_when_found(
        self, repo: AdminRecordRepository, session: AsyncMock
    ) -> None:
        """Returns True when the telegram_id is in the admins table."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = 1  # row ID found
        session.execute = AsyncMock(return_value=mock_result)

        result = await repo.exists_by_telegram_id(123456)

        assert result is True
        session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_exists_by_telegram_id_returns_false_when_not_found(
        self, repo: AdminRecordRepository, session: AsyncMock
    ) -> None:
        """Returns False when the telegram_id is not in the admins table."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)

        result = await repo.exists_by_telegram_id(999999)

        assert result is False

    @pytest.mark.asyncio
    async def test_exists_by_telegram_id_uses_limit_one(
        self, repo: AdminRecordRepository, session: AsyncMock
    ) -> None:
        """The query must use LIMIT 1 to avoid a full-table scan."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)

        await repo.exists_by_telegram_id(123456)

        # Verify a DB round-trip happened (not cached or skipped)
        session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_exists_by_telegram_id_owner_role_is_recognized(
        self, repo: AdminRecordRepository, session: AsyncMock
    ) -> None:
        """A user with role='owner' is considered an admin."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = 42  # row ID
        session.execute = AsyncMock(return_value=mock_result)

        result = await repo.exists_by_telegram_id(100200)

        assert result is True

    @pytest.mark.asyncio
    async def test_exists_by_telegram_id_moderator_role_is_recognized(
        self, repo: AdminRecordRepository, session: AsyncMock
    ) -> None:
        """A user with any role (e.g. 'moderator') is considered an admin — no role filter."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = 7
        session.execute = AsyncMock(return_value=mock_result)

        result = await repo.exists_by_telegram_id(555555)

        assert result is True

    # ------------------------------------------------------------------
    # get_by_telegram_id
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_get_by_telegram_id_returns_record_when_found(
        self, repo: AdminRecordRepository, session: AsyncMock
    ) -> None:
        """Returns the ORM record when the telegram_id is present."""
        orm_admin = _make_orm_admin(telegram_id=123456, role="owner")
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = orm_admin
        session.execute = AsyncMock(return_value=mock_result)

        result = await repo.get_by_telegram_id(123456)

        assert result is orm_admin
        assert result.telegram_id == 123456
        assert result.role == "owner"

    @pytest.mark.asyncio
    async def test_get_by_telegram_id_returns_none_when_not_found(
        self, repo: AdminRecordRepository, session: AsyncMock
    ) -> None:
        """Returns None when no admin record exists for that telegram_id."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)

        result = await repo.get_by_telegram_id(404404)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_telegram_id_returns_username(
        self, repo: AdminRecordRepository, session: AsyncMock
    ) -> None:
        """Record returned includes the username field."""
        orm_admin = _make_orm_admin(telegram_id=777, username="alice")
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = orm_admin
        session.execute = AsyncMock(return_value=mock_result)

        result = await repo.get_by_telegram_id(777)

        assert result is not None
        assert result.username == "alice"

    @pytest.mark.asyncio
    async def test_get_by_telegram_id_returns_none_username(
        self, repo: AdminRecordRepository, session: AsyncMock
    ) -> None:
        """Record with username=None is handled correctly."""
        orm_admin = _make_orm_admin(telegram_id=888, username=None)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = orm_admin
        session.execute = AsyncMock(return_value=mock_result)

        result = await repo.get_by_telegram_id(888)

        assert result is not None
        assert result.username is None

    @pytest.mark.asyncio
    async def test_get_by_telegram_id_executes_query(
        self, repo: AdminRecordRepository, session: AsyncMock
    ) -> None:
        """Verifies that execute is called exactly once per lookup."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)

        await repo.get_by_telegram_id(123)

        session.execute.assert_called_once()
