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
        ):
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_or_create = AsyncMock(return_value=user_dto)

            data: dict = {}
            await middleware(handler, event, data)

        handler.assert_called_once()
        call_data = handler.call_args[0][1]
        assert isinstance(call_data["user"], UserDTO)
        assert call_data["user"].telegram_id == 123456
        assert call_data["db_session"] == mock_session

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
        ):
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_or_create = AsyncMock(return_value=user_dto)

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
