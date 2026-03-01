"""Tests for bot.services.vpn_service."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from bot.dto import ConfigDTO
from bot.services.vpn_service import (
    ConfigLinks,
    TrafficInfo,
    create_config,
    delete_config,
    get_config_link,
    get_config_traffic,
)

NOW = datetime.now(tz=UTC)


def _make_config_dto(
    config_id: int = 1,
    inbound_id: int = 1,
    client_id: str = "uuid-123",
    email: str = "test",
) -> ConfigDTO:
    return ConfigDTO(
        id=config_id,
        user_id=1,
        inbound_id=inbound_id,
        client_id=client_id,
        email=email,
        protocol="vless",
        created_at=NOW,
    )


class TestTrafficInfo:
    def test_format_bytes_b(self) -> None:
        t = TrafficInfo(up=500, down=300, total=0, enable=True)
        assert t.format_bytes(500) == "500 B"

    def test_format_bytes_kb(self) -> None:
        t = TrafficInfo(up=0, down=0, total=0, enable=True)
        assert t.format_bytes(2048) == "2.0 KB"

    def test_format_bytes_mb(self) -> None:
        t = TrafficInfo(up=0, down=0, total=0, enable=True)
        assert t.format_bytes(5 * 1024 * 1024) == "5.0 MB"

    def test_format_bytes_gb(self) -> None:
        t = TrafficInfo(up=0, down=0, total=0, enable=True)
        assert t.format_bytes(2 * 1024**3) == "2.00 GB"

    def test_format_message_active(self) -> None:
        t = TrafficInfo(up=1024, down=2048, total=0, enable=True)
        msg = t.format_message()
        assert "Активен" in msg
        assert "Загрузка" in msg
        assert "Скачивание" in msg

    def test_format_message_disabled(self) -> None:
        t = TrafficInfo(up=0, down=0, total=0, enable=False)
        msg = t.format_message()
        assert "Отключен" in msg


class TestCreateConfig:
    @pytest.mark.asyncio
    async def test_creates_config_and_returns_config_links(self) -> None:
        xui = AsyncMock()
        session = AsyncMock()

        inbound_data = {
            "protocol": "vless",
            "port": 443,
            "listen": "1.2.3.4",
            "settings": json.dumps({"clients": []}),
            "streamSettings": json.dumps({
                "network": "tcp",
                "security": "none",
            }),
        }
        xui.get_inbound = AsyncMock(return_value=inbound_data)
        xui.add_client = AsyncMock()

        config_dto = _make_config_dto()

        with patch("bot.services.vpn_service.ConfigRepository") as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.create = AsyncMock(return_value=config_dto)

            with patch("bot.services.vpn_service.generate_link_from_inbound") as mock_gen:
                mock_gen.return_value = "vless://test-link"

                result = await create_config(
                    user_id=1,
                    name="test-config",
                    inbound_id=1,
                    xui=xui,
                    session=session,
                )

        assert isinstance(result, ConfigLinks)
        assert result.vless_link == "vless://test-link"
        # Subscription URL built from settings.PANEL_URL and the generated UUID
        assert "/sub/" in result.subscription_url
        xui.add_client.assert_called_once()
        mock_repo.create.assert_called_once()


class TestDeleteConfig:
    @pytest.mark.asyncio
    async def test_deletes_from_panel_and_db(self) -> None:
        xui = AsyncMock()
        session = AsyncMock()

        config_dto = _make_config_dto(config_id=1, inbound_id=1, client_id="uuid-123", email="test")

        with patch("bot.services.vpn_service.ConfigRepository") as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_by_id = AsyncMock(return_value=config_dto)
            mock_repo.delete = AsyncMock()

            await delete_config(config_id=1, xui=xui, session=session)

        xui.delete_client.assert_called_once_with(1, "uuid-123")
        mock_repo.delete.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_raises_if_not_found(self) -> None:
        xui = AsyncMock()
        session = AsyncMock()

        with patch("bot.services.vpn_service.ConfigRepository") as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_by_id = AsyncMock(return_value=None)

            with pytest.raises(ValueError, match="not found"):
                await delete_config(config_id=999, xui=xui, session=session)


class TestGetConfigTraffic:
    @pytest.mark.asyncio
    async def test_returns_traffic_info(self) -> None:
        xui = AsyncMock()
        xui.get_client_traffic = AsyncMock(return_value={
            "up": 1024,
            "down": 2048,
            "total": 0,
            "enable": True,
        })

        traffic = await get_config_traffic("test@email", xui)

        assert traffic.up == 1024
        assert traffic.down == 2048
        assert traffic.enable is True

    @pytest.mark.asyncio
    async def test_returns_empty_on_none(self) -> None:
        xui = AsyncMock()
        xui.get_client_traffic = AsyncMock(return_value=None)

        traffic = await get_config_traffic("test@email", xui)

        assert traffic.up == 0
        assert traffic.down == 0
        assert traffic.enable is False


class TestGetConfigLink:
    @pytest.mark.asyncio
    async def test_returns_config_links(self) -> None:
        xui = AsyncMock()
        session = AsyncMock()

        config_dto = _make_config_dto(config_id=1, inbound_id=1, client_id="uuid-123", email="test")

        xui.get_inbound = AsyncMock(return_value={"protocol": "vless"})

        with (
            patch("bot.services.vpn_service.ConfigRepository") as mock_repo_cls,
            patch("bot.services.vpn_service.generate_link_from_inbound") as mock_gen,
        ):
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_by_id = AsyncMock(return_value=config_dto)
            mock_gen.return_value = "vless://link"

            result = await get_config_link(config_id=1, xui=xui, session=session)

        assert isinstance(result, ConfigLinks)
        assert result.vless_link == "vless://link"
        assert result.subscription_url == "http://localhost:2053/sub/uuid-123"

    @pytest.mark.asyncio
    async def test_raises_if_not_found(self) -> None:
        xui = AsyncMock()
        session = AsyncMock()

        with patch("bot.services.vpn_service.ConfigRepository") as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_by_id = AsyncMock(return_value=None)

            with pytest.raises(ValueError, match="not found"):
                await get_config_link(config_id=999, xui=xui, session=session)
