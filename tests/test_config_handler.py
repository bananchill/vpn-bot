"""Tests for bot.handlers.config -- config CRUD handler."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, Chat, Message, User

from bot.dto import ConfigDTO, UserDTO
from bot.handlers.config import (
    ConfigCreateStates,
    ask_delete_config,
    config_name_not_text,
    confirm_delete_config,
    list_configs,
    process_config_name,
    show_config_detail,
    show_link,
    show_traffic,
    start_create_config,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

NOW = datetime.now(tz=UTC)


def _make_callback(data: str, user_id: int = 123456) -> MagicMock:
    """Create a mock CallbackQuery."""
    cb = MagicMock(spec=CallbackQuery)
    cb.data = data
    cb.from_user = MagicMock(spec=User)
    cb.from_user.id = user_id
    cb.message = MagicMock()
    cb.message.edit_text = AsyncMock()
    cb.answer = AsyncMock()
    return cb


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
    msg.answer = AsyncMock(return_value=MagicMock(edit_text=AsyncMock()))
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
    protocol: str = "vless",
) -> ConfigDTO:
    """Create a ConfigDTO for handler tests."""
    return ConfigDTO(
        id=config_id,
        user_id=user_id,
        inbound_id=1,
        client_id="uuid-123",
        sub_id="abcdef0123456789",
        email=email,
        protocol=protocol,
        created_at=NOW,
    )


# ---------------------------------------------------------------------------
# Tests: Create config flow
# ---------------------------------------------------------------------------


class TestStartCreateConfig:
    @pytest.mark.asyncio
    async def test_sets_fsm_state(self) -> None:
        cb = _make_callback("create_config")
        state = _make_state()
        user = _make_user_dto()

        await start_create_config(cb, state, user)

        current = await state.get_state()
        assert current == ConfigCreateStates.waiting_for_name
        cb.message.edit_text.assert_called_once()
        assert "название" in cb.message.edit_text.call_args[0][0].lower()
        cb.answer.assert_called_once()


class TestProcessConfigName:
    @pytest.mark.asyncio
    async def test_invalid_name_rejected(self) -> None:
        msg = _make_message("bad name with spaces!")
        state = _make_state()
        await state.set_state(ConfigCreateStates.waiting_for_name)
        user = _make_user_dto()
        session = AsyncMock()

        await process_config_name(msg, state, user, session)

        msg.answer.assert_called_once()
        assert "некорректное" in msg.answer.call_args[0][0].lower()

    @pytest.mark.asyncio
    async def test_valid_name_creates_config(self) -> None:
        from bot.services.vpn_service import ConfigLinks

        msg = _make_message("my-config")
        state = _make_state()
        await state.set_state(ConfigCreateStates.waiting_for_name)
        user = _make_user_dto()
        session = AsyncMock()

        status_msg = AsyncMock()
        msg.answer = AsyncMock(return_value=status_msg)

        mock_xui = AsyncMock()
        mock_links = ConfigLinks(
            vless_link="vless://test-link",
            subscription_url="http://localhost:2053/sub/uuid-123",
        )

        with (
            patch(
                "bot.handlers.config._get_xui_client",
                new_callable=AsyncMock,
                return_value=mock_xui,
            ),
            patch(
                "bot.handlers.config.create_config",
                new_callable=AsyncMock,
                return_value=mock_links,
            ) as mock_create,
        ):
            await process_config_name(msg, state, user, session)

        mock_create.assert_called_once()
        status_msg.edit_text.assert_called()
        final_text = status_msg.edit_text.call_args[0][0]
        assert "my-config" in final_text
        assert "vless://test-link" in final_text
        assert "http://localhost:2053/sub/uuid-123" in final_text

        current = await state.get_state()
        assert current is None

    @pytest.mark.asyncio
    async def test_xui_login_failure_shows_error(self) -> None:
        from bot.services.xui_client import XUIError

        msg = _make_message("my-config")
        state = _make_state()
        await state.set_state(ConfigCreateStates.waiting_for_name)
        user = _make_user_dto()
        session = AsyncMock()

        status_msg = AsyncMock()
        msg.answer = AsyncMock(return_value=status_msg)

        with patch(
            "bot.handlers.config._get_xui_client",
            new_callable=AsyncMock,
            side_effect=XUIError("login failed"),
        ):
            await process_config_name(msg, state, user, session)

        status_msg.edit_text.assert_called()
        final_text = status_msg.edit_text.call_args[0][0]
        assert "ошибка" in final_text.lower()

    @pytest.mark.asyncio
    async def test_empty_name_rejected(self) -> None:
        msg = _make_message("   ")
        state = _make_state()
        await state.set_state(ConfigCreateStates.waiting_for_name)
        user = _make_user_dto()
        session = AsyncMock()

        await process_config_name(msg, state, user, session)

        msg.answer.assert_called_once()
        assert "некорректное" in msg.answer.call_args[0][0].lower()


class TestConfigNameNotText:
    @pytest.mark.asyncio
    async def test_rejects_non_text(self) -> None:
        msg = _make_message(None)
        await config_name_not_text(msg)
        msg.answer.assert_called_once()
        assert "текстовым" in msg.answer.call_args[0][0].lower()


# ---------------------------------------------------------------------------
# Tests: List configs
# ---------------------------------------------------------------------------


class TestListConfigs:
    @pytest.mark.asyncio
    async def test_empty_list(self) -> None:
        cb = _make_callback("my_configs")
        user = _make_user_dto()
        session = AsyncMock()

        with patch("bot.handlers.config.ConfigRepository") as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_by_user_id = AsyncMock(return_value=[])

            await list_configs(cb, user, session)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "нет конфигов" in text.lower()

    @pytest.mark.asyncio
    async def test_shows_configs(self) -> None:
        cb = _make_callback("my_configs")
        user = _make_user_dto()
        session = AsyncMock()

        configs = [
            _make_config_dto(1, email="cfg-1"),
            _make_config_dto(2, email="cfg-2"),
        ]

        with patch("bot.handlers.config.ConfigRepository") as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_by_user_id = AsyncMock(return_value=configs)

            await list_configs(cb, user, session)

        cb.message.edit_text.assert_called_once()


# ---------------------------------------------------------------------------
# Tests: Config detail
# ---------------------------------------------------------------------------


class TestShowConfigDetail:
    @pytest.mark.asyncio
    async def test_shows_detail(self) -> None:
        cb = _make_callback("config:1:detail")
        user = _make_user_dto()
        session = AsyncMock()
        config = _make_config_dto(1)

        with patch("bot.handlers.config.ConfigRepository") as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_by_id = AsyncMock(return_value=config)

            await show_config_detail(cb, user, session)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "test-config" in text

    @pytest.mark.asyncio
    async def test_not_found(self) -> None:
        cb = _make_callback("config:999:detail")
        user = _make_user_dto()
        session = AsyncMock()

        with patch("bot.handlers.config.ConfigRepository") as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_by_id = AsyncMock(return_value=None)

            await show_config_detail(cb, user, session)

        cb.answer.assert_called_once()
        assert "не найден" in cb.answer.call_args[1].get("text", cb.answer.call_args[0][0]).lower()

    @pytest.mark.asyncio
    async def test_wrong_user(self) -> None:
        cb = _make_callback("config:1:detail")
        user = _make_user_dto(user_id=999)
        session = AsyncMock()
        config = _make_config_dto(1, user_id=1)

        with patch("bot.handlers.config.ConfigRepository") as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_by_id = AsyncMock(return_value=config)

            await show_config_detail(cb, user, session)

        cb.answer.assert_called_once()


# ---------------------------------------------------------------------------
# Tests: Traffic
# ---------------------------------------------------------------------------


class TestShowTraffic:
    @pytest.mark.asyncio
    async def test_shows_traffic(self) -> None:
        cb = _make_callback("config:1:traffic")
        user = _make_user_dto()
        session = AsyncMock()
        config = _make_config_dto(1)

        from bot.services.vpn_service import TrafficInfo

        traffic = TrafficInfo(up=1024, down=2048, total=0, enable=True)
        mock_xui = AsyncMock()

        with (
            patch("bot.handlers.config.ConfigRepository") as mock_repo_cls,
            patch(
                "bot.handlers.config._get_xui_client",
                new_callable=AsyncMock,
                return_value=mock_xui,
            ),
            patch(
                "bot.handlers.config.get_config_traffic",
                new_callable=AsyncMock,
                return_value=traffic,
            ),
        ):
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_by_id = AsyncMock(return_value=config)

            await show_traffic(cb, user, session)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "Трафик" in text or "трафик" in text.lower()


# ---------------------------------------------------------------------------
# Tests: Get link
# ---------------------------------------------------------------------------


class TestShowLink:
    @pytest.mark.asyncio
    async def test_shows_link(self) -> None:
        from bot.services.vpn_service import ConfigLinks

        cb = _make_callback("config:1:link")
        user = _make_user_dto()
        session = AsyncMock()
        config = _make_config_dto(1)
        mock_xui = AsyncMock()
        mock_links = ConfigLinks(
            vless_link="vless://test-link",
            subscription_url="http://localhost:2053/sub/uuid-123",
        )

        with (
            patch("bot.handlers.config.ConfigRepository") as mock_repo_cls,
            patch(
                "bot.handlers.config._get_xui_client",
                new_callable=AsyncMock,
                return_value=mock_xui,
            ),
            patch(
                "bot.handlers.config.get_config_link",
                new_callable=AsyncMock,
                return_value=mock_links,
            ),
        ):
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_by_id = AsyncMock(return_value=config)

            await show_link(cb, user, session)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "vless://test-link" in text
        assert "http://localhost:2053/sub/uuid-123" in text


# ---------------------------------------------------------------------------
# Tests: Delete config
# ---------------------------------------------------------------------------


class TestDeleteConfig:
    @pytest.mark.asyncio
    async def test_ask_delete_shows_confirmation(self) -> None:
        cb = _make_callback("config:1:delete")
        user = _make_user_dto()
        session = AsyncMock()
        config = _make_config_dto(1)

        with patch("bot.handlers.config.ConfigRepository") as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_by_id = AsyncMock(return_value=config)

            await ask_delete_config(cb, user, session)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "уверены" in text.lower()

    @pytest.mark.asyncio
    async def test_confirm_delete_succeeds(self) -> None:
        cb = _make_callback("config:1:confirm_delete")
        user = _make_user_dto()
        session = AsyncMock()
        config = _make_config_dto(1)
        mock_xui = AsyncMock()

        with (
            patch("bot.handlers.config.ConfigRepository") as mock_repo_cls,
            patch(
                "bot.handlers.config._get_xui_client",
                new_callable=AsyncMock,
                return_value=mock_xui,
            ),
            patch(
                "bot.handlers.config.delete_config",
                new_callable=AsyncMock,
            ) as mock_delete,
        ):
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_by_id = AsyncMock(return_value=config)

            await confirm_delete_config(cb, user, session)

        mock_delete.assert_called_once()
        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "удалён" in text.lower()
