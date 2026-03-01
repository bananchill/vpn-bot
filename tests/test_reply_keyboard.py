"""Tests for reply keyboard builder and reply button handlers."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Chat, Message, ReplyKeyboardMarkup, User

from bot.dto import ConfigDTO, UserDTO
from bot.handlers.config import (
    ConfigCreateStates,
    reply_create_config,
    reply_my_configs,
)
from bot.keyboards.reply import BTN_CREATE_CONFIG, BTN_MY_CONFIGS, reply_main_menu

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

NOW = datetime.now(tz=UTC)


def _make_message(text: str | None = None, user_id: int = 123456) -> MagicMock:
    """Create a mock Message."""
    msg = MagicMock(spec=Message)
    msg.text = text
    msg.chat = MagicMock(spec=Chat)
    msg.chat.id = user_id
    msg.message_id = 42
    msg.from_user = MagicMock(spec=User)
    msg.from_user.id = user_id
    msg.from_user.username = "testuser"
    msg.answer = AsyncMock()
    return msg


def _make_state() -> FSMContext:
    """Create a real FSMContext backed by MemoryStorage."""
    storage = MemoryStorage()
    key = StorageKey(bot_id=1, chat_id=123456, user_id=123456)
    return FSMContext(storage=storage, key=key)


def _make_user_dto(user_id: int = 1) -> UserDTO:
    """Create a UserDTO for handler tests."""
    return UserDTO(
        id=user_id,
        telegram_id=123456,
        username="testuser",
        is_admin=False,
        created_at=NOW,
    )


def _make_config_dto(
    config_id: int = 1,
    user_id: int = 1,
    email: str = "test-config",
) -> ConfigDTO:
    """Create a ConfigDTO for handler tests."""
    return ConfigDTO(
        id=config_id,
        user_id=user_id,
        inbound_id=1,
        client_id="uuid-123",
        sub_id="abcdef0123456789",
        email=email,
        protocol="vless",
        created_at=NOW,
    )


# ---------------------------------------------------------------------------
# Tests: reply_main_menu() keyboard builder
# ---------------------------------------------------------------------------


class TestReplyMainMenu:
    def test_returns_reply_keyboard_markup(self) -> None:
        kb = reply_main_menu()
        assert isinstance(kb, ReplyKeyboardMarkup)

    def test_has_one_row_with_two_buttons(self) -> None:
        kb = reply_main_menu()
        assert len(kb.keyboard) == 1
        assert len(kb.keyboard[0]) == 2

    def test_create_config_button_text(self) -> None:
        kb = reply_main_menu()
        assert kb.keyboard[0][0].text == BTN_CREATE_CONFIG

    def test_my_configs_button_text(self) -> None:
        kb = reply_main_menu()
        assert kb.keyboard[0][1].text == BTN_MY_CONFIGS

    def test_resize_keyboard_enabled(self) -> None:
        kb = reply_main_menu()
        assert kb.resize_keyboard is True

    def test_persistent_enabled(self) -> None:
        kb = reply_main_menu()
        assert kb.persistent is True


# ---------------------------------------------------------------------------
# Tests: button text constants
# ---------------------------------------------------------------------------


class TestButtonConstants:
    def test_create_config_text(self) -> None:
        assert BTN_CREATE_CONFIG == "Создать конфиг"

    def test_my_configs_text(self) -> None:
        assert BTN_MY_CONFIGS == "Мои конфиги"


# ---------------------------------------------------------------------------
# Tests: reply_create_config handler
# ---------------------------------------------------------------------------


class TestReplyCreateConfig:
    @pytest.mark.asyncio
    async def test_sets_fsm_state_to_waiting_for_name(self) -> None:
        msg = _make_message(BTN_CREATE_CONFIG)
        state = _make_state()
        user = _make_user_dto()

        await reply_create_config(msg, state, user)

        current = await state.get_state()
        assert current == ConfigCreateStates.waiting_for_name

    @pytest.mark.asyncio
    async def test_sends_name_prompt(self) -> None:
        msg = _make_message(BTN_CREATE_CONFIG)
        state = _make_state()
        user = _make_user_dto()

        await reply_create_config(msg, state, user)

        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "название" in text.lower()


# ---------------------------------------------------------------------------
# Tests: reply_my_configs handler
# ---------------------------------------------------------------------------


class TestReplyMyConfigs:
    @pytest.mark.asyncio
    async def test_empty_list_shows_no_configs_message(self) -> None:
        msg = _make_message(BTN_MY_CONFIGS)
        user = _make_user_dto()
        session = AsyncMock()

        with patch("bot.handlers.config.ConfigRepository") as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_by_user_id = AsyncMock(return_value=[])

            await reply_my_configs(msg, user, session)

        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "нет конфигов" in text.lower()

    @pytest.mark.asyncio
    async def test_shows_config_list(self) -> None:
        msg = _make_message(BTN_MY_CONFIGS)
        user = _make_user_dto()
        session = AsyncMock()

        configs = [
            _make_config_dto(1, email="cfg-1"),
            _make_config_dto(2, email="cfg-2"),
        ]

        with patch("bot.handlers.config.ConfigRepository") as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_by_user_id = AsyncMock(return_value=configs)

            await reply_my_configs(msg, user, session)

        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "конфиги" in text.lower()
        # Verify inline keyboard is attached for the config list
        call_kwargs = msg.answer.call_args.kwargs
        assert call_kwargs.get("reply_markup") is not None

    @pytest.mark.asyncio
    async def test_only_shows_own_configs(self) -> None:
        """Verify the repository is queried with the correct user id."""
        msg = _make_message(BTN_MY_CONFIGS)
        user = _make_user_dto(user_id=42)
        session = AsyncMock()

        with patch("bot.handlers.config.ConfigRepository") as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_by_user_id = AsyncMock(return_value=[])

            await reply_my_configs(msg, user, session)

        mock_repo.get_by_user_id.assert_called_once_with(42)
