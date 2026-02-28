"""Tests for bot.db.repositories.user_repo."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from bot.db.repositories.user_repo import UserRepository
from bot.dto import UserDTO

NOW = datetime.now(tz=UTC)


def _make_orm_user(
    user_id: int = 1,
    telegram_id: int = 123456,
    username: str | None = "testuser",
    is_admin: bool = False,
) -> MagicMock:
    u = MagicMock()
    u.id = user_id
    u.telegram_id = telegram_id
    u.username = username
    u.is_admin = is_admin
    u.created_at = NOW
    return u


class TestUserRepository:
    @pytest.fixture()
    def session(self) -> AsyncMock:
        return AsyncMock()

    @pytest.fixture()
    def repo(self, session: AsyncMock) -> UserRepository:
        return UserRepository(session)

    @pytest.mark.asyncio
    async def test_get_by_telegram_id_returns_user_dto(
        self, repo: UserRepository, session: AsyncMock
    ) -> None:
        orm_user = _make_orm_user()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = orm_user
        session.execute = AsyncMock(return_value=mock_result)

        result = await repo.get_by_telegram_id(123456)

        assert isinstance(result, UserDTO)
        assert result.telegram_id == 123456
        assert result.username == "testuser"

    @pytest.mark.asyncio
    async def test_get_by_telegram_id_not_found_returns_none(
        self, repo: UserRepository, session: AsyncMock
    ) -> None:
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)

        result = await repo.get_by_telegram_id(999999)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_or_create_existing_user_returns_dto(
        self, repo: UserRepository, session: AsyncMock
    ) -> None:
        orm_user = _make_orm_user(telegram_id=111)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = orm_user
        session.execute = AsyncMock(return_value=mock_result)

        result = await repo.get_or_create(telegram_id=111, username="existing")

        assert isinstance(result, UserDTO)
        assert result.telegram_id == 111
        # Should NOT call add or flush for an existing user
        session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_or_create_new_user_inserts_and_returns_dto(
        self, repo: UserRepository, session: AsyncMock
    ) -> None:
        # First query returns None (user does not exist)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)
        session.flush = AsyncMock()

        async def fake_refresh(obj: object) -> None:
            obj.id = 10  # type: ignore[attr-defined]
            obj.created_at = NOW  # type: ignore[attr-defined]
            obj.is_admin = False  # type: ignore[attr-defined]

        session.refresh = fake_refresh

        result = await repo.get_or_create(telegram_id=999, username="newuser")

        session.add.assert_called_once()
        session.flush.assert_called_once()
        assert isinstance(result, UserDTO)

    @pytest.mark.asyncio
    async def test_set_admin_returns_user_dto(
        self, repo: UserRepository, session: AsyncMock
    ) -> None:
        orm_user = _make_orm_user(is_admin=False)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = orm_user
        session.execute = AsyncMock(return_value=mock_result)
        session.flush = AsyncMock()

        result = await repo.set_admin(telegram_id=123456, is_admin=True)

        assert isinstance(result, UserDTO)
        # is_admin was set on the ORM object
        assert orm_user.is_admin is True
        session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_admin_not_found_raises_value_error(
        self, repo: UserRepository, session: AsyncMock
    ) -> None:
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(ValueError, match="not found"):
            await repo.set_admin(telegram_id=99999)

    @pytest.mark.asyncio
    async def test_list_admins_returns_list_of_dtos(
        self, repo: UserRepository, session: AsyncMock
    ) -> None:
        orm_admins = [
            _make_orm_user(user_id=1, is_admin=True),
            _make_orm_user(user_id=2, telegram_id=654321, is_admin=True),
        ]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = orm_admins
        session.execute = AsyncMock(return_value=mock_result)

        result = await repo.list_admins()

        assert len(result) == 2
        assert all(isinstance(u, UserDTO) for u in result)
        assert all(u.is_admin for u in result)

    @pytest.mark.asyncio
    async def test_list_admins_empty(
        self, repo: UserRepository, session: AsyncMock
    ) -> None:
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(return_value=mock_result)

        result = await repo.list_admins()

        assert result == []
