"""Tests for _load_settings_from_db (bot/__main__.py)."""

from __future__ import annotations

import os

# Set FERNET_KEY before any bot imports
os.environ.setdefault(
    "FERNET_KEY", "uD1gNjS5zNNNWL0fthTbmqp_0MO--Wpc3K-be1seUCY="
)

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cryptography.fernet import Fernet

from bot.__main__ import _load_settings_from_db
from bot.config import settings


def _make_bot_settings_row(
    fernet: Fernet,
    *,
    bot_token: str = "123456:ABC-DEF",
    panel_url: str = "https://panel.example.com",
    panel_sub_url: str = "https://sub.example.com",
    panel_username: str = "admin",
    panel_password: str = "secret123",
    owner_id: int = 777777,
) -> MagicMock:
    """Create a mock BotSettingsRecord with encrypted fields."""
    row = MagicMock()
    row.id = 1
    row.client_bot_token = fernet.encrypt(bot_token.encode()).decode()
    row.panel_url = panel_url
    row.panel_sub_url = panel_sub_url
    row.panel_username = panel_username
    row.panel_password = fernet.encrypt(panel_password.encode()).decode()
    row.owner_id = owner_id
    return row


@pytest.fixture()
def fernet() -> Fernet:
    return Fernet(settings.FERNET_KEY.encode())


class TestLoadSettingsFromDB:
    """Tests for _load_settings_from_db."""

    @pytest.mark.asyncio
    async def test_loads_and_decrypts_all_fields(self, fernet: Fernet) -> None:
        row = _make_bot_settings_row(fernet)
        session = AsyncMock()
        session.scalar.return_value = row

        with patch("bot.__main__.async_session_factory") as factory:
            factory.return_value.__aenter__ = AsyncMock(return_value=session)
            factory.return_value.__aexit__ = AsyncMock(return_value=False)
            await _load_settings_from_db()

        assert settings.BOT_TOKEN == "123456:ABC-DEF"
        assert settings.PANEL_URL == "https://panel.example.com"
        assert settings.PANEL_SUB_URL == "https://sub.example.com"
        assert settings.PANEL_USERNAME == "admin"
        assert settings.PANEL_PASSWORD == "secret123"
        assert settings.OWNER_ID == 777777

    @pytest.mark.asyncio
    async def test_retries_when_no_row(self, fernet: Fernet) -> None:
        """First call returns None, second returns valid row."""
        row = _make_bot_settings_row(fernet, bot_token="retry-token")
        session = AsyncMock()
        session.scalar.side_effect = [None, row]

        with (
            patch("bot.__main__.async_session_factory") as factory,
            patch("bot.__main__.asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
        ):
            factory.return_value.__aenter__ = AsyncMock(return_value=session)
            factory.return_value.__aexit__ = AsyncMock(return_value=False)
            await _load_settings_from_db()

        mock_sleep.assert_called_once_with(30)
        assert settings.BOT_TOKEN == "retry-token"

    @pytest.mark.asyncio
    async def test_retries_when_token_empty(self, fernet: Fernet) -> None:
        """Row exists but client_bot_token is None → retry."""
        empty_row = MagicMock()
        empty_row.client_bot_token = None

        valid_row = _make_bot_settings_row(fernet, bot_token="after-empty")
        session = AsyncMock()
        session.scalar.side_effect = [empty_row, valid_row]

        with (
            patch("bot.__main__.async_session_factory") as factory,
            patch("bot.__main__.asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
        ):
            factory.return_value.__aenter__ = AsyncMock(return_value=session)
            factory.return_value.__aexit__ = AsyncMock(return_value=False)
            await _load_settings_from_db()

        mock_sleep.assert_called_once_with(30)
        assert settings.BOT_TOKEN == "after-empty"

    @pytest.mark.asyncio
    async def test_skips_none_plaintext_fields(self, fernet: Fernet) -> None:
        """When optional fields are None, settings keep their defaults."""
        row = MagicMock()
        row.id = 1
        row.client_bot_token = fernet.encrypt(b"token-only").decode()
        row.panel_url = None
        row.panel_sub_url = None
        row.panel_username = None
        row.panel_password = None
        row.owner_id = None

        # Set known defaults to verify they're preserved
        settings.PANEL_URL = "old-url"
        session = AsyncMock()
        session.scalar.return_value = row

        with patch("bot.__main__.async_session_factory") as factory:
            factory.return_value.__aenter__ = AsyncMock(return_value=session)
            factory.return_value.__aexit__ = AsyncMock(return_value=False)
            await _load_settings_from_db()

        assert settings.BOT_TOKEN == "token-only"
        assert settings.PANEL_URL == "old-url"  # unchanged

    @pytest.mark.asyncio
    async def test_raises_without_fernet_key(self) -> None:
        original = settings.FERNET_KEY
        try:
            settings.FERNET_KEY = ""
            with pytest.raises(RuntimeError, match="FERNET_KEY is not set"):
                await _load_settings_from_db()
        finally:
            settings.FERNET_KEY = original
