"""Additional tests for bot.handlers.config — coverage gaps and edge cases."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.types import CallbackQuery, User

from bot.dto import ConfigDTO, UserDTO
from bot.handlers.config import refresh_config
from bot.services.xui_client import XUIError

NOW = datetime.now(tz=UTC)


def _make_callback(data: str, user_id: int = 123456) -> MagicMock:
    cb = MagicMock(spec=CallbackQuery)
    cb.data = data
    cb.from_user = MagicMock(spec=User)
    cb.from_user.id = user_id
    cb.message = MagicMock()
    cb.message.edit_text = AsyncMock()
    cb.answer = AsyncMock()
    return cb


def _make_user_dto(user_id: int = 1) -> UserDTO:
    return UserDTO(
        id=user_id,
        telegram_id=123456,
        username="testuser",
        is_admin=False,
        created_at=NOW,
    )


def _make_config_dto(config_id: int = 1, user_id: int = 1) -> ConfigDTO:
    return ConfigDTO(
        id=config_id,
        user_id=user_id,
        inbound_id=1,
        client_id="uuid-123",
        email="test-config",
        protocol="vless",
        created_at=NOW,
    )


# ---------------------------------------------------------------------------
# Tests: refresh_config handler
# ---------------------------------------------------------------------------


class TestRefreshConfig:
    @pytest.mark.asyncio
    async def test_refresh_success_edits_message(self) -> None:
        from bot.services.vpn_service import ConfigLinks

        cb = _make_callback("config:1:refresh")
        user = _make_user_dto()
        session = AsyncMock()
        config = _make_config_dto(1)
        mock_xui = AsyncMock()
        mock_links = ConfigLinks(
            vless_link="vless://refreshed-link",
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

            await refresh_config(cb, user, session)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "обновлён" in text.lower()
        assert "vless://refreshed-link" in text
        assert "http://localhost:2053/sub/uuid-123" in text

    @pytest.mark.asyncio
    async def test_refresh_not_found_shows_alert(self) -> None:
        cb = _make_callback("config:999:refresh")
        user = _make_user_dto()
        session = AsyncMock()

        with patch("bot.handlers.config.ConfigRepository") as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_by_id = AsyncMock(return_value=None)

            await refresh_config(cb, user, session)

        cb.answer.assert_called_once()
        assert cb.message.edit_text.call_count == 0

    @pytest.mark.asyncio
    async def test_refresh_wrong_user_shows_alert(self) -> None:
        cb = _make_callback("config:1:refresh")
        user = _make_user_dto(user_id=999)
        session = AsyncMock()
        config = _make_config_dto(1, user_id=1)

        with patch("bot.handlers.config.ConfigRepository") as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_by_id = AsyncMock(return_value=config)

            await refresh_config(cb, user, session)

        cb.answer.assert_called_once()
        assert cb.message.edit_text.call_count == 0

    @pytest.mark.asyncio
    async def test_refresh_xui_login_failure_shows_alert(self) -> None:
        cb = _make_callback("config:1:refresh")
        user = _make_user_dto()
        session = AsyncMock()
        config = _make_config_dto(1)

        with (
            patch("bot.handlers.config.ConfigRepository") as mock_repo_cls,
            patch(
                "bot.handlers.config._get_xui_client",
                new_callable=AsyncMock,
                side_effect=XUIError("login failed"),
            ),
        ):
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_by_id = AsyncMock(return_value=config)

            await refresh_config(cb, user, session)

        cb.answer.assert_called()
        assert cb.message.edit_text.call_count == 0

    @pytest.mark.asyncio
    async def test_refresh_xui_error_shows_alert(self) -> None:
        cb = _make_callback("config:1:refresh")
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
                "bot.handlers.config.get_config_link",
                new_callable=AsyncMock,
                side_effect=XUIError("panel error"),
            ),
        ):
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_by_id = AsyncMock(return_value=config)

            await refresh_config(cb, user, session)

        cb.answer.assert_called()


# ---------------------------------------------------------------------------
# Tests: confirm_delete — no admin session
# ---------------------------------------------------------------------------


class TestConfirmDeleteEdgeCases:
    @pytest.mark.asyncio
    async def test_confirm_delete_xui_login_failure_shows_alert(self) -> None:
        from bot.handlers.config import confirm_delete_config

        cb = _make_callback("config:1:confirm_delete")
        user = _make_user_dto()
        session = AsyncMock()
        config = _make_config_dto(1)

        with (
            patch("bot.handlers.config.ConfigRepository") as mock_repo_cls,
            patch(
                "bot.handlers.config._get_xui_client",
                new_callable=AsyncMock,
                side_effect=XUIError("login failed"),
            ),
        ):
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_by_id = AsyncMock(return_value=config)

            await confirm_delete_config(cb, user, session)

        cb.answer.assert_called()
        cb.message.edit_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_confirm_delete_xui_error_shows_alert(self) -> None:
        from bot.handlers.config import confirm_delete_config

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
                side_effect=XUIError("panel error"),
            ),
        ):
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_by_id = AsyncMock(return_value=config)

            await confirm_delete_config(cb, user, session)

        cb.answer.assert_called()
        cb.message.edit_text.assert_not_called()


# ---------------------------------------------------------------------------
# Tests: show_traffic — no admin session edge case
# ---------------------------------------------------------------------------


class TestShowTrafficEdgeCases:
    @pytest.mark.asyncio
    async def test_show_traffic_xui_login_failure_shows_alert(self) -> None:
        from bot.handlers.config import show_traffic

        cb = _make_callback("config:1:traffic")
        user = _make_user_dto()
        session = AsyncMock()
        config = _make_config_dto(1)

        with (
            patch("bot.handlers.config.ConfigRepository") as mock_repo_cls,
            patch(
                "bot.handlers.config._get_xui_client",
                new_callable=AsyncMock,
                side_effect=XUIError("login failed"),
            ),
        ):
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_by_id = AsyncMock(return_value=config)

            await show_traffic(cb, user, session)

        cb.answer.assert_called()
        cb.message.edit_text.assert_not_called()


# ---------------------------------------------------------------------------
# Tests: show_link — no admin session edge case
# ---------------------------------------------------------------------------


class TestShowLinkEdgeCases:
    @pytest.mark.asyncio
    async def test_show_link_xui_login_failure_shows_alert(self) -> None:
        from bot.handlers.config import show_link

        cb = _make_callback("config:1:link")
        user = _make_user_dto()
        session = AsyncMock()
        config = _make_config_dto(1)

        with (
            patch("bot.handlers.config.ConfigRepository") as mock_repo_cls,
            patch(
                "bot.handlers.config._get_xui_client",
                new_callable=AsyncMock,
                side_effect=XUIError("login failed"),
            ),
        ):
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_by_id = AsyncMock(return_value=config)

            await show_link(cb, user, session)

        cb.answer.assert_called()
        cb.message.edit_text.assert_not_called()
