"""Tests for TASK-016 additions to vpn_service.create_config:
- expiryTime is set to expires_at * 1000 when provided
- expiryTime is 0 when expires_at is None (admin path)
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from bot.dto import ConfigDTO
from bot.services.vpn_service import create_config

NOW = datetime(2026, 4, 1, 0, 0, 0, tzinfo=UTC)


def _make_config_dto(
    config_id: int = 1,
    email: str = "testcfg",
    sub_id: str = "abcdef1234567890",
) -> ConfigDTO:
    return ConfigDTO(
        id=config_id,
        user_id=1,
        inbound_id=1,
        client_id="uuid-test",
        sub_id=sub_id,
        email=email,
        protocol="vless",
        created_at=NOW,
    )


def _make_inbound(protocol: str = "vless", security: str = "none") -> dict:
    return {
        "protocol": protocol,
        "port": 443,
        "listen": "1.2.3.4",
        "settings": json.dumps({"clients": []}),
        "streamSettings": json.dumps({"network": "tcp", "security": security}),
    }


class TestCreateConfigExpiryTime:
    @pytest.mark.asyncio
    async def test_expiry_time_ms_set_when_expires_at_provided(self) -> None:
        """When expires_at is passed, expiryTime in the panel call = int(ts * 1000)."""
        xui = AsyncMock()
        xui.get_inbound = AsyncMock(return_value=_make_inbound())
        xui.add_client = AsyncMock()
        session = AsyncMock()

        config_dto = _make_config_dto()

        with patch("bot.services.vpn_service.ConfigRepository") as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.create = AsyncMock(return_value=config_dto)

            with patch("bot.services.vpn_service.generate_link_from_inbound", return_value="vless://link"):
                await create_config(
                    user_id=1,
                    name="testcfg",
                    inbound_id=1,
                    xui=xui,
                    session=session,
                    expires_at=NOW,
                )

        client_settings = xui.add_client.call_args[0][1]
        expected_ms = int(NOW.timestamp() * 1000)
        assert client_settings["expiryTime"] == expected_ms

    @pytest.mark.asyncio
    async def test_expiry_time_zero_when_no_expires_at(self) -> None:
        """When expires_at is None (admin), expiryTime must be 0 (no limit)."""
        xui = AsyncMock()
        xui.get_inbound = AsyncMock(return_value=_make_inbound())
        xui.add_client = AsyncMock()
        session = AsyncMock()

        config_dto = _make_config_dto()

        with patch("bot.services.vpn_service.ConfigRepository") as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.create = AsyncMock(return_value=config_dto)

            with patch("bot.services.vpn_service.generate_link_from_inbound", return_value="vless://link"):
                await create_config(
                    user_id=1,
                    name="testcfg",
                    inbound_id=1,
                    xui=xui,
                    session=session,
                    expires_at=None,
                )

        client_settings = xui.add_client.call_args[0][1]
        assert client_settings["expiryTime"] == 0

    @pytest.mark.asyncio
    async def test_expiry_time_default_is_zero(self) -> None:
        """When expires_at is omitted entirely, expiryTime must be 0."""
        xui = AsyncMock()
        xui.get_inbound = AsyncMock(return_value=_make_inbound())
        xui.add_client = AsyncMock()
        session = AsyncMock()

        config_dto = _make_config_dto()

        with patch("bot.services.vpn_service.ConfigRepository") as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.create = AsyncMock(return_value=config_dto)

            with patch("bot.services.vpn_service.generate_link_from_inbound", return_value="vless://link"):
                # expires_at not passed — should default to None
                await create_config(
                    user_id=1,
                    name="testcfg",
                    inbound_id=1,
                    xui=xui,
                    session=session,
                )

        client_settings = xui.add_client.call_args[0][1]
        assert client_settings["expiryTime"] == 0

    @pytest.mark.asyncio
    async def test_expiry_time_is_integer(self) -> None:
        """expiryTime must be an int, not a float."""
        xui = AsyncMock()
        xui.get_inbound = AsyncMock(return_value=_make_inbound())
        xui.add_client = AsyncMock()
        session = AsyncMock()

        config_dto = _make_config_dto()

        with patch("bot.services.vpn_service.ConfigRepository") as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.create = AsyncMock(return_value=config_dto)

            with patch("bot.services.vpn_service.generate_link_from_inbound", return_value="vless://link"):
                await create_config(
                    user_id=1,
                    name="testcfg",
                    inbound_id=1,
                    xui=xui,
                    session=session,
                    expires_at=NOW,
                )

        client_settings = xui.add_client.call_args[0][1]
        assert isinstance(client_settings["expiryTime"], int)
