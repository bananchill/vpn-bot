"""VPN configs API router.

Provides endpoints for listing, toggling, and bulk-toggling VPN
configurations. Config changes are propagated to the external 3x-ui
panel; the local DB does not track enabled state — that lives on
the panel only.
"""

import logging
from typing import Annotated

from db.models import Admin, VPNConfig
from db.repositories import config_repo, log_repo, settings_repo
from fastapi import APIRouter, Depends, HTTPException
from panel.client import PanelClient, PanelClientError
from schemas.config import (
    ConfigResponse,
    ConfigToggle,
    ConfigToggleAllRequest,
    ConfigToggleAllResponse,
    ConfigToggleResponse,
)
from sqlalchemy.ext.asyncio import AsyncSession
from utils.crypto import decrypt

from api.deps import get_current_admin, get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["configs"])

# TODO: admin_username is None because Admin model doesn't store Telegram username.
# Future: extract username from initData in deps.py and pass through.


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_panel_client(
    session: AsyncSession,
) -> PanelClient | None:
    """Build a PanelClient from stored settings, or None if not configured."""
    settings = await settings_repo.get_settings(session)
    if not settings or not settings.panel_url or not settings.panel_username:
        return None
    if not settings.panel_password:
        return None

    try:
        password = decrypt(settings.panel_password)
    except Exception:
        logger.exception("Failed to decrypt panel password for config toggle")
        return None

    return PanelClient(
        base_url=settings.panel_url,
        username=settings.panel_username,
        password=password,
    )


async def _sync_toggle_to_panel(
    session: AsyncSession,
    client_id: str,
    enabled: bool,
) -> str | None:
    """Propagate a single config toggle to the panel.

    Returns a warning message if the panel call fails, or None on success.
    """
    client = await _get_panel_client(session)
    if client is None:
        return "Panel not configured"

    try:
        async with client:
            if enabled:
                await client.enable_config(client_id)
            else:
                await client.disable_config(client_id)
    except PanelClientError as exc:
        logger.warning("Panel toggle failed for config %s: %s", client_id, exc)
        return f"Panel error: {exc}"

    return None


async def _sync_toggle_all_to_panel(
    session: AsyncSession,
    configs: list[VPNConfig],
    enabled: bool,
) -> str | None:
    """Propagate a bulk toggle to the panel for each config."""
    client = await _get_panel_client(session)
    if client is None:
        return "Panel not configured"

    warnings: list[str] = []
    try:
        async with client:
            for cfg in configs:
                try:
                    if enabled:
                        await client.enable_config(cfg.client_id)
                    else:
                        await client.disable_config(cfg.client_id)
                except PanelClientError as exc:
                    logger.warning(
                        "Panel toggle failed for config %s: %s",
                        cfg.client_id,
                        exc,
                    )
                    warnings.append(str(exc))
    except PanelClientError as exc:
        return f"Panel connection error: {exc}"

    if warnings:
        return f"Some panel calls failed: {'; '.join(warnings)}"
    return None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/users/{user_id}/configs", response_model=list[ConfigResponse])
async def get_user_configs(
    user_id: int,
    session: Annotated[AsyncSession, Depends(get_db)],
    _admin: Annotated[Admin, Depends(get_current_admin)],
) -> list[ConfigResponse]:
    """Return all VPN configs belonging to a user."""
    configs = await config_repo.get_user_configs(session, user_id)
    return [
        ConfigResponse(
            id=c.id,
            client_id=c.client_id,
            email=c.email,
            protocol=c.protocol,
            created_at=c.created_at,
        )
        for c in configs
    ]


@router.patch("/configs/{config_id}/toggle", response_model=ConfigToggleResponse)
async def toggle_config(
    config_id: int,
    payload: ConfigToggle,
    session: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[Admin, Depends(get_current_admin)],
) -> ConfigToggleResponse:
    """Toggle a single VPN config on the 3x-ui panel.

    The enabled state is only managed on the panel side.
    """
    config = await config_repo.get_config_by_id(session, config_id)
    if config is None:
        raise HTTPException(status_code=404, detail="Config not found")

    warning = await _sync_toggle_to_panel(
        session, config.client_id, payload.enabled
    )
    if warning:
        logger.warning("Config %d toggle panel warning: %s", config_id, warning)

    await log_repo.log_action(
        session,
        admin_telegram_id=admin.telegram_id,
        admin_username=None,
        action="toggle_config",
        target=config.email,
        details={"enabled": payload.enabled, "config_id": config_id},
    )

    return ConfigToggleResponse(success=True, warning=warning)


@router.post(
    "/users/{user_id}/configs/toggle-all",
    response_model=ConfigToggleAllResponse,
)
async def toggle_all_configs(
    user_id: int,
    payload: ConfigToggleAllRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[Admin, Depends(get_current_admin)],
) -> ConfigToggleAllResponse:
    """Toggle all VPN configs for a user on the 3x-ui panel."""
    configs = await config_repo.get_user_configs(session, user_id)

    warning = await _sync_toggle_all_to_panel(session, configs, payload.enabled)
    if warning:
        logger.warning(
            "Toggle-all for user %d panel warning: %s", user_id, warning
        )

    await log_repo.log_action(
        session,
        admin_telegram_id=admin.telegram_id,
        admin_username=None,
        action="toggle_all_configs",
        target=str(user_id),
        details={"enabled": payload.enabled, "count": len(configs)},
    )

    return ConfigToggleAllResponse(
        updated_count=len(configs),
        success=True,
    )
