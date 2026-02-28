"""Tests for bot.handlers.admin -- /admin FSM flow."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Chat, Message, User

from bot.dto import UserDTO
from bot.handlers.admin import (
    AdminLoginStates,
    cmd_admin,
    login_not_text,
    password_not_text,
    process_login,
    process_password,
)
from bot.services.xui_client import XUIAuthError, XUIConnectionError

NOW = datetime.now(tz=UTC)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_message(text: str | None = None, user_id: int = 123456) -> MagicMock:
    """Create a mock Message with essential attributes."""
    msg = MagicMock(spec=Message)
    msg.text = text
    msg.chat = MagicMock(spec=Chat)
    msg.chat.id = user_id
    msg.message_id = 42
    msg.from_user = MagicMock(spec=User)
    msg.from_user.id = user_id
    msg.from_user.username = "testuser"
    msg.answer = AsyncMock(return_value=MagicMock(edit_text=AsyncMock()))
    return msg


def _make_state() -> FSMContext:
    """Create a real FSMContext backed by MemoryStorage."""
    storage = MemoryStorage()
    key = StorageKey(bot_id=1, chat_id=123456, user_id=123456)
    return FSMContext(storage=storage, key=key)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCmdAdmin:
    @pytest.mark.asyncio
    async def test_cmd_admin_sets_state(self) -> None:
        msg = _make_message("/admin")
        state = _make_state()

        await cmd_admin(msg, state)

        current = await state.get_state()
        assert current == AdminLoginStates.waiting_for_login
        msg.answer.assert_called_once()
        assert "логин" in msg.answer.call_args[0][0].lower()


class TestProcessLogin:
    @pytest.mark.asyncio
    async def test_stores_login_and_asks_password(self) -> None:
        msg = _make_message("myadmin")
        state = _make_state()
        await state.set_state(AdminLoginStates.waiting_for_login)

        await process_login(msg, state)

        data = await state.get_data()
        assert data["panel_login"] == "myadmin"
        current = await state.get_state()
        assert current == AdminLoginStates.waiting_for_password
        msg.answer.assert_called_once()
        assert "пароль" in msg.answer.call_args[0][0].lower()

    @pytest.mark.asyncio
    async def test_empty_login_rejected(self) -> None:
        msg = _make_message("   ")
        state = _make_state()
        await state.set_state(AdminLoginStates.waiting_for_login)

        await process_login(msg, state)

        current = await state.get_state()
        assert current == AdminLoginStates.waiting_for_login
        assert "пустым" in msg.answer.call_args[0][0].lower()


class TestProcessPassword:
    @pytest.mark.asyncio
    async def test_successful_login(self) -> None:
        msg = _make_message("secretpass")
        state = _make_state()
        await state.set_state(AdminLoginStates.waiting_for_password)
        await state.update_data(panel_login="admin")

        bot = AsyncMock()
        status_msg = AsyncMock()
        msg.answer = AsyncMock(return_value=status_msg)

        # Build a proper async-context-manager mock for the DB session
        mock_session = AsyncMock()

        @asynccontextmanager
        async def fake_session_factory():
            yield mock_session

        @asynccontextmanager
        async def fake_begin():
            yield

        mock_session.begin = fake_begin

        with (
            patch("bot.handlers.admin.XUIClient") as mock_client,
            patch("bot.handlers.admin.async_session_factory", fake_session_factory),
        ):
            # Mock XUI client
            mock_xui = AsyncMock()
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_xui)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)

            # Mock repos — get_or_create now returns UserDTO
            mock_user = UserDTO(
                id=1,
                telegram_id=123456,
                username="testuser",
                is_admin=True,
                created_at=NOW,
            )

            with (
                patch("bot.handlers.admin.UserRepository") as mock_user_repo_cls,
                patch("bot.handlers.admin.AdminSessionRepository") as mock_admin_repo_cls,
                patch("bot.handlers.admin.encrypt_credentials", return_value="encrypted"),
            ):
                mock_user_repo = mock_user_repo_cls.return_value
                mock_user_repo.get_or_create = AsyncMock(return_value=mock_user)
                mock_user_repo.set_admin = AsyncMock()

                mock_admin_repo = mock_admin_repo_cls.return_value
                mock_admin_repo.upsert = AsyncMock()

                await process_password(msg, state, bot)

            # Password message should be deleted
            bot.delete_message.assert_called_once()

            # Success message
            status_msg.edit_text.assert_called()
            final_text = status_msg.edit_text.call_args[0][0]
            assert "успешно" in final_text.lower()

            # State cleared
            current = await state.get_state()
            assert current is None

    @pytest.mark.asyncio
    async def test_auth_error_resets_to_login(self) -> None:
        msg = _make_message("wrongpass")
        state = _make_state()
        await state.set_state(AdminLoginStates.waiting_for_password)
        await state.update_data(panel_login="admin")

        bot = AsyncMock()
        status_msg = AsyncMock()
        msg.answer = AsyncMock(return_value=status_msg)

        with patch("bot.handlers.admin.XUIClient") as mock_client:
            mock_xui = AsyncMock()
            mock_xui.login.side_effect = XUIAuthError("bad creds")
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_xui)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)

            await process_password(msg, state, bot)

        current = await state.get_state()
        assert current == AdminLoginStates.waiting_for_login
        assert "неверный" in status_msg.edit_text.call_args[0][0].lower()

    @pytest.mark.asyncio
    async def test_connection_error_resets_to_login(self) -> None:
        msg = _make_message("pass")
        state = _make_state()
        await state.set_state(AdminLoginStates.waiting_for_password)
        await state.update_data(panel_login="admin")

        bot = AsyncMock()
        status_msg = AsyncMock()
        msg.answer = AsyncMock(return_value=status_msg)

        with patch("bot.handlers.admin.XUIClient") as mock_client:
            mock_xui = AsyncMock()
            mock_xui.login.side_effect = XUIConnectionError("refused")
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_xui)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)

            await process_password(msg, state, bot)

        current = await state.get_state()
        assert current == AdminLoginStates.waiting_for_login
        assert "подключиться" in status_msg.edit_text.call_args[0][0].lower()

    @pytest.mark.asyncio
    async def test_empty_password_rejected(self) -> None:
        msg = _make_message("   ")
        state = _make_state()
        await state.set_state(AdminLoginStates.waiting_for_password)
        await state.update_data(panel_login="admin")

        bot = AsyncMock()
        await process_password(msg, state, bot)

        assert "пустым" in msg.answer.call_args[0][0].lower()


class TestFallbacks:
    @pytest.mark.asyncio
    async def test_login_not_text(self) -> None:
        msg = _make_message(None)
        await login_not_text(msg)
        msg.answer.assert_called_once()
        assert "текстовым" in msg.answer.call_args[0][0].lower()

    @pytest.mark.asyncio
    async def test_password_not_text(self) -> None:
        msg = _make_message(None)
        await password_not_text(msg)
        msg.answer.assert_called_once()
        assert "текстовым" in msg.answer.call_args[0][0].lower()
