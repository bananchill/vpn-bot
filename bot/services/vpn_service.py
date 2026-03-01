"""Business logic layer for VPN config operations."""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import settings
from bot.db.repositories.config_repo import ConfigRepository
from bot.services.link_generator import generate_link_from_inbound, generate_subscription_url
from bot.services.xui_client import XUIClient

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class TrafficInfo:
    """Formatted traffic statistics."""

    up: int
    down: int
    total: int
    enable: bool

    def format_bytes(self, value: int) -> str:
        """Format bytes into human-readable string."""
        if value < 1024:
            return f"{value} B"
        elif value < 1024**2:
            return f"{value / 1024:.1f} KB"
        elif value < 1024**3:
            return f"{value / 1024**2:.1f} MB"
        else:
            return f"{value / 1024**3:.2f} GB"

    def format_message(self) -> str:
        """Return a formatted Russian message with traffic stats."""
        status = "Активен" if self.enable else "Отключен"
        return (
            f"Статус: {status}\n"
            f"Загрузка: {self.format_bytes(self.up)}\n"
            f"Скачивание: {self.format_bytes(self.down)}\n"
            f"Всего: {self.format_bytes(self.up + self.down)}"
        )


@dataclass(frozen=True, slots=True)
class ConfigLinks:
    """Both connection links for a VPN config."""

    vless_link: str
    subscription_url: str


async def create_config(
    user_id: int,
    name: str,
    inbound_id: int,
    xui: XUIClient,
    session: AsyncSession,
) -> ConfigLinks:
    """Create a new VPN config and return both connection links.

    Args:
        user_id: Internal DB user ID.
        name: User-provided config name (used as email in 3x-ui).
        inbound_id: Target inbound ID on the panel.
        xui: Authenticated XUI client.
        session: DB session (caller manages transaction).

    Returns:
        ConfigLinks with vless_link and subscription_url.
    """
    client_uuid = str(uuid.uuid4())

    # Get inbound info to determine protocol
    inbound = await xui.get_inbound(inbound_id)
    protocol = inbound.get("protocol", "vless")

    # Build client settings for 3x-ui
    client_settings: dict[str, Any] = {
        "id": client_uuid,
        "email": name,
        "enable": True,
        "totalGB": 0,
        "expiryTime": 0,
    }

    # Add flow for VLESS with Reality
    if protocol == "vless":
        stream_raw = inbound.get("streamSettings", "{}")
        stream = json.loads(stream_raw) if isinstance(stream_raw, str) else stream_raw
        security = stream.get("security", "none")
        if security == "reality":
            client_settings["flow"] = "xtls-rprx-vision"

    await xui.add_client(inbound_id, client_settings)

    # Save to DB
    config_repo = ConfigRepository(session)
    await config_repo.create(
        user_id=user_id,
        inbound_id=inbound_id,
        client_id=client_uuid,
        email=name,
        protocol=protocol,
    )

    # Fetch updated inbound to generate link with all settings
    inbound = await xui.get_inbound(inbound_id)
    vless_link = generate_link_from_inbound(inbound, client_uuid, name)
    subscription_url = generate_subscription_url(settings.PANEL_URL, client_uuid)

    logger.info("Created config '%s' (uuid=%s) for user_id=%s", name, client_uuid, user_id)
    return ConfigLinks(vless_link=vless_link, subscription_url=subscription_url)


async def delete_config(
    config_id: int,
    xui: XUIClient,
    session: AsyncSession,
) -> None:
    """Delete a VPN config from both the panel and DB.

    Args:
        config_id: Internal DB config ID.
        xui: Authenticated XUI client.
        session: DB session (caller manages transaction).

    Raises:
        ValueError: If config not found.
    """
    config_repo = ConfigRepository(session)
    config = await config_repo.get_by_id(config_id)
    if config is None:
        raise ValueError(f"Config with id={config_id} not found")

    # Delete from 3x-ui panel
    await xui.delete_client(config.inbound_id, config.client_id)

    # Delete from DB
    await config_repo.delete(config_id)

    logger.info("Deleted config id=%s (email=%s)", config_id, config.email)


async def get_config_traffic(
    email: str,
    xui: XUIClient,
) -> TrafficInfo:
    """Get traffic statistics for a config.

    Args:
        email: Client email identifier in 3x-ui.
        xui: Authenticated XUI client.

    Returns:
        TrafficInfo with formatted stats.
    """
    data = await xui.get_client_traffic(email)
    if data is None:
        return TrafficInfo(up=0, down=0, total=0, enable=False)

    return TrafficInfo(
        up=data.get("up", 0),
        down=data.get("down", 0),
        total=data.get("total", 0),
        enable=data.get("enable", True),
    )


async def get_config_link(
    config_id: int,
    xui: XUIClient,
    session: AsyncSession,
) -> ConfigLinks:
    """Generate both connection links for an existing config.

    Args:
        config_id: Internal DB config ID.
        xui: Authenticated XUI client.
        session: DB session.

    Returns:
        ConfigLinks with vless_link and subscription_url.

    Raises:
        ValueError: If config not found.
    """
    config_repo = ConfigRepository(session)
    config = await config_repo.get_by_id(config_id)
    if config is None:
        raise ValueError(f"Config with id={config_id} not found")

    inbound = await xui.get_inbound(config.inbound_id)
    vless_link = generate_link_from_inbound(inbound, config.client_id, config.email)
    subscription_url = generate_subscription_url(settings.PANEL_URL, config.client_id)
    return ConfigLinks(vless_link=vless_link, subscription_url=subscription_url)
