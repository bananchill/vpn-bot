"""Settings API router.

Provides endpoints for reading, updating, and testing the bot's panel
connection settings.  All endpoints require the ``owner`` role so that
moderators cannot view or modify sensitive credentials.
"""

import logging
import time
from typing import Annotated

from db.models import Admin
from db.repositories import settings_repo
from fastapi import APIRouter, Depends, HTTPException
from panel.client import PanelClient, PanelClientError
from schemas.settings import (
    ConnectionCheckResponse,
    SettingsResponse,
    SettingsUpdate,
)
from sqlalchemy.ext.asyncio import AsyncSession
from utils.crypto import decrypt, encrypt

from api.deps import get_current_admin, get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/settings", tags=["settings"])


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------

async def require_owner(
    admin: Annotated[Admin, Depends(get_current_admin)],
) -> Admin:
    """Gate that restricts access to admins with the 'owner' role.

    Raises:
        HTTPException: 403 if the authenticated admin is not an owner.
    """
    if admin.role != "owner":
        raise HTTPException(status_code=403, detail="Owner access required")
    return admin


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mask_token(encrypted_token: str) -> str:
    """Decrypt a token and return a masked version showing only the last 4 chars."""
    try:
        plaintext = decrypt(encrypted_token)
    except Exception:
        return "****"
    if len(plaintext) <= 4:
        return "****"
    return f"{'*' * 4}{plaintext[-4:]}"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=SettingsResponse)
async def get_settings(
    session: Annotated[AsyncSession, Depends(get_db)],
    _admin: Annotated[Admin, Depends(require_owner)],
) -> SettingsResponse:
    """Return current settings with sensitive fields masked.

    Passwords are reported as a boolean flag; the bot token is masked
    to show only the last four characters.
    """
    settings = await settings_repo.get_settings(session)

    if settings is None:
        return SettingsResponse()

    masked_token: str | None = None
    if settings.client_bot_token:
        masked_token = _mask_token(settings.client_bot_token)

    return SettingsResponse(
        panel_url=settings.panel_url,
        panel_sub_url=settings.panel_sub_url,
        panel_username=settings.panel_username,
        has_password=bool(settings.panel_password),
        owner_id=settings.owner_id,
        client_bot_token_masked=masked_token,
        updated_at=settings.updated_at,
    )


@router.put("", response_model=SettingsResponse)
async def update_settings(
    payload: SettingsUpdate,
    session: Annotated[AsyncSession, Depends(get_db)],
    _admin: Annotated[Admin, Depends(require_owner)],
) -> SettingsResponse:
    """Update settings.  Only non-None fields in the payload are applied.

    Password and bot token are encrypted with Fernet before storage so
    that plaintext secrets never persist in the database.
    """
    update_data: dict[str, str | int | None] = {}

    if payload.panel_url is not None:
        update_data["panel_url"] = payload.panel_url
    if payload.panel_sub_url is not None:
        update_data["panel_sub_url"] = payload.panel_sub_url
    if payload.panel_username is not None:
        update_data["panel_username"] = payload.panel_username
    if payload.panel_password is not None:
        update_data["panel_password"] = encrypt(payload.panel_password)
    if payload.owner_id is not None:
        update_data["owner_id"] = payload.owner_id
    if payload.client_bot_token is not None:
        update_data["client_bot_token"] = encrypt(payload.client_bot_token)

    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    settings = await settings_repo.upsert_settings(session, **update_data)

    masked_token: str | None = None
    if settings.client_bot_token:
        masked_token = _mask_token(settings.client_bot_token)

    return SettingsResponse(
        panel_url=settings.panel_url,
        panel_sub_url=settings.panel_sub_url,
        panel_username=settings.panel_username,
        has_password=bool(settings.panel_password),
        owner_id=settings.owner_id,
        client_bot_token_masked=masked_token,
        updated_at=settings.updated_at,
    )


@router.post("/check", response_model=ConnectionCheckResponse)
async def check_connection(
    session: Annotated[AsyncSession, Depends(get_db)],
    _admin: Annotated[Admin, Depends(require_owner)],
) -> ConnectionCheckResponse:
    """Create a temporary PanelClient from stored settings and test connectivity.

    The check logs in, performs a lightweight API call, and reports the
    round-trip time. A missing or incomplete configuration is treated as
    a failure rather than an HTTP error so the frontend can display a
    friendly message.
    """
    settings = await settings_repo.get_settings(session)

    if settings is None or not settings.panel_url or not settings.panel_username:
        return ConnectionCheckResponse(
            success=False,
            message="Panel settings are not configured",
            response_time_ms=None,
        )

    if not settings.panel_password:
        return ConnectionCheckResponse(
            success=False,
            message="Panel password is not set",
            response_time_ms=None,
        )

    try:
        password = decrypt(settings.panel_password)
    except Exception:
        logger.exception("Failed to decrypt panel password")
        return ConnectionCheckResponse(
            success=False,
            message="Failed to decrypt stored password",
            response_time_ms=None,
        )

    start = time.monotonic()
    try:
        async with PanelClient(
            base_url=settings.panel_url,
            username=settings.panel_username,
            password=password,
        ) as client:
            success, msg = await client.check_connection()
    except PanelClientError as exc:
        elapsed = int((time.monotonic() - start) * 1000)
        return ConnectionCheckResponse(
            success=False,
            message=str(exc),
            response_time_ms=elapsed,
        )

    elapsed = int((time.monotonic() - start) * 1000)
    return ConnectionCheckResponse(
        success=success,
        message=msg,
        response_time_ms=elapsed,
    )
