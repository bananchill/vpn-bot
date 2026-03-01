"""Tests for bot.handlers.start -- /start command and main menu."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.types import Chat, Message, User

from bot.dto import UserDTO
from bot.handlers.start import back_to_main, cmd_start
from bot.keyboards.reply import reply_main_menu

NOW = datetime.now(tz=UTC)


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
    msg.from_user.first_name = "Test"
    msg.answer = AsyncMock()
    msg.edit_text = AsyncMock()
    return msg


def _make_user_dto(user_id: int = 1, telegram_id: int = 123456) -> UserDTO:
    """Create a UserDTO for handler tests."""
    return UserDTO(
        id=user_id,
        telegram_id=telegram_id,
        username="testuser",
        is_admin=False,
        created_at=NOW,
    )


class TestCmdStart:
    @pytest.mark.asyncio
    async def test_sends_two_messages(self) -> None:
        """cmd_start sends greeting with reply keyboard, then inline menu."""
        msg = _make_message("/start")
        user = _make_user_dto()

        await cmd_start(msg, user)

        assert msg.answer.call_count == 2

    @pytest.mark.asyncio
    async def test_first_message_has_greeting_and_reply_keyboard(self) -> None:
        msg = _make_message("/start")
        user = _make_user_dto()

        await cmd_start(msg, user)

        first_call = msg.answer.call_args_list[0]
        text = first_call[0][0]
        assert "testuser" in text
        # First message sets the persistent reply keyboard
        reply_markup = first_call[1]["reply_markup"]
        expected_kb = reply_main_menu()
        assert type(reply_markup) is type(expected_kb)

    @pytest.mark.asyncio
    async def test_second_message_has_inline_menu(self) -> None:
        msg = _make_message("/start")
        user = _make_user_dto()

        await cmd_start(msg, user)

        second_call = msg.answer.call_args_list[1]
        text = second_call[0][0]
        assert "действие" in text.lower()
        assert second_call[1]["reply_markup"] is not None

    @pytest.mark.asyncio
    async def test_greets_by_first_name_if_no_username(self) -> None:
        msg = _make_message("/start")
        msg.from_user.username = None
        msg.from_user.first_name = "John"
        user = _make_user_dto()

        await cmd_start(msg, user)

        text = msg.answer.call_args_list[0][0][0]
        assert "John" in text


class TestBackToMain:
    @pytest.mark.asyncio
    async def test_edits_message_with_main_menu(self) -> None:
        callback = MagicMock()
        callback.data = "back_to_main"
        callback.message = MagicMock()
        callback.message.edit_text = AsyncMock()
        callback.answer = AsyncMock()
        user = _make_user_dto()

        await back_to_main(callback, user)

        callback.message.edit_text.assert_called_once()
        text = callback.message.edit_text.call_args[0][0]
        assert "действие" in text.lower()
        callback.answer.assert_called_once()
