"""Tests for bot.middlewares.auth."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.types import CallbackQuery, Message, User

from bot.dto import UserDTO
from bot.middlewares.auth import AuthMiddleware

NOW = datetime.now(tz=UTC)


def _make_user_dto() -> UserDTO:
    return UserDTO(
        id=1,
        telegram_id=123456,
        username="testuser",
        is_admin=False,
        created_at=NOW,
    )


class TestAuthMiddleware:
    @pytest.fixture()
    def middleware(self) -> AuthMiddleware:
        return AuthMiddleware()

    @pytest.mark.asyncio
    async def test_injects_user_dto_and_session(self, middleware: AuthMiddleware) -> None:
        handler = AsyncMock()

        event = MagicMock(spec=Message)
        tg_user = MagicMock(spec=User)
        tg_user.id = 123456
        tg_user.username = "testuser"
        event.from_user = tg_user

        mock_session = AsyncMock()
        user_dto = _make_user_dto()

        @asynccontextmanager
        async def fake_session_factory():
            yield mock_session

        @asynccontextmanager
        async def fake_begin():
            yield

        mock_session.begin = fake_begin

        with (
            patch("bot.middlewares.auth.async_session_factory", fake_session_factory),
            patch("bot.middlewares.auth.UserRepository") as mock_repo_cls,
            patch("bot.middlewares.auth.AdminRecordRepository") as mock_admin_repo_cls,
        ):
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_or_create = AsyncMock(return_value=user_dto)
            # User.is_admin is False, so the middleware will check admins table
            mock_admin_repo = mock_admin_repo_cls.return_value
            mock_admin_repo.exists_by_telegram_id = AsyncMock(return_value=False)

            data: dict = {}
            await middleware(handler, event, data)

        handler.assert_called_once()
        call_data = handler.call_args[0][1]
        assert isinstance(call_data["user"], UserDTO)
        assert call_data["user"].telegram_id == 123456
        assert call_data["db_session"] == mock_session

    @pytest.mark.asyncio
    async def test_promotes_admin_from_admins_table(self, middleware: AuthMiddleware) -> None:
        """If User.is_admin is False but admins table has the user, DTO is promoted."""
        handler = AsyncMock()

        event = MagicMock(spec=Message)
        tg_user = MagicMock(spec=User)
        tg_user.id = 123456
        tg_user.username = "testuser"
        event.from_user = tg_user

        mock_session = AsyncMock()
        # User with is_admin=False
        user_dto = _make_user_dto()

        @asynccontextmanager
        async def fake_session_factory():
            yield mock_session

        @asynccontextmanager
        async def fake_begin():
            yield

        mock_session.begin = fake_begin

        with (
            patch("bot.middlewares.auth.async_session_factory", fake_session_factory),
            patch("bot.middlewares.auth.UserRepository") as mock_repo_cls,
            patch("bot.middlewares.auth.AdminRecordRepository") as mock_admin_repo_cls,
        ):
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_or_create = AsyncMock(return_value=user_dto)
            # admins table says this user IS an admin
            mock_admin_repo = mock_admin_repo_cls.return_value
            mock_admin_repo.exists_by_telegram_id = AsyncMock(return_value=True)

            data: dict = {}
            await middleware(handler, event, data)

        call_data = handler.call_args[0][1]
        # The DTO should have is_admin=True despite the users table saying False
        assert call_data["user"].is_admin is True

    @pytest.mark.asyncio
    async def test_skips_admins_check_when_already_admin(self, middleware: AuthMiddleware) -> None:
        """If User.is_admin is already True, skip the admins table lookup."""
        handler = AsyncMock()

        event = MagicMock(spec=Message)
        tg_user = MagicMock(spec=User)
        tg_user.id = 123456
        tg_user.username = "testuser"
        event.from_user = tg_user

        mock_session = AsyncMock()
        user_dto = UserDTO(
            id=1,
            telegram_id=123456,
            username="testuser",
            is_admin=True,
            created_at=NOW,
        )

        @asynccontextmanager
        async def fake_session_factory():
            yield mock_session

        @asynccontextmanager
        async def fake_begin():
            yield

        mock_session.begin = fake_begin

        with (
            patch("bot.middlewares.auth.async_session_factory", fake_session_factory),
            patch("bot.middlewares.auth.UserRepository") as mock_repo_cls,
            patch("bot.middlewares.auth.AdminRecordRepository") as mock_admin_repo_cls,
        ):
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_or_create = AsyncMock(return_value=user_dto)

            data: dict = {}
            await middleware(handler, event, data)

        # AdminRecordRepository should never have been instantiated
        mock_admin_repo_cls.assert_not_called()

    @pytest.mark.asyncio
    async def test_works_with_callback_query(self, middleware: AuthMiddleware) -> None:
        handler = AsyncMock()

        event = MagicMock(spec=CallbackQuery)
        tg_user = MagicMock(spec=User)
        tg_user.id = 123456
        tg_user.username = "testuser"
        event.from_user = tg_user

        mock_session = AsyncMock()
        user_dto = _make_user_dto()

        @asynccontextmanager
        async def fake_session_factory():
            yield mock_session

        @asynccontextmanager
        async def fake_begin():
            yield

        mock_session.begin = fake_begin

        with (
            patch("bot.middlewares.auth.async_session_factory", fake_session_factory),
            patch("bot.middlewares.auth.UserRepository") as mock_repo_cls,
            patch("bot.middlewares.auth.AdminRecordRepository") as mock_admin_repo_cls,
        ):
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_or_create = AsyncMock(return_value=user_dto)
            mock_admin_repo = mock_admin_repo_cls.return_value
            mock_admin_repo.exists_by_telegram_id = AsyncMock(return_value=False)

            data: dict = {}
            await middleware(handler, event, data)

        handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_user_passes_through(self, middleware: AuthMiddleware) -> None:
        handler = AsyncMock()

        # Event without from_user
        event = MagicMock(spec=Message)
        event.from_user = None

        data: dict = {}
        await middleware(handler, event, data)

        handler.assert_called_once()
        assert "user" not in data
