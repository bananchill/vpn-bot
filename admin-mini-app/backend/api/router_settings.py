"""Settings API router.

Provides endpoints for per-admin panel credentials (personal settings)
and owner-only global settings.  Personal settings are stored in the
``Admin`` model; global settings remain in ``BotSettings``.

All endpoints require authentication.  Global endpoints additionally
require the ``owner`` role.
"""

import json
import logging
import time
from typing import Annotated

from db.models import Admin
from db.repositories import (
    admin_repo,
    admin_session_repo,
    log_repo,
    settings_repo,
    user_repo,
)
from fastapi import APIRouter, Depends, HTTPException
from panel.client import PanelClient, PanelClientError
from schemas.settings import (
    ConnectionCheckResponse,
    GlobalSettingsResponse,
    GlobalSettingsUpdate,
    PersonalSettingsResponse,
    PersonalSettingsUpdate,
)
from sqlalchemy.ext.asyncio import AsyncSession
from utils.crypto import decrypt, encrypt

from api.deps import get_current_admin, get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/settings", tags=["settings"])


# ---------------------------------------------------------------------------
# Role gates
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


def _build_encrypted_credentials(username: str, password: str) -> str:
    """Build the Fernet-encrypted JSON credentials blob for admin_sessions.

    The format matches ``bot/services/crypto.encrypt_credentials``:
    ``{"username": "...", "password": "..."}``, encrypted with the shared
    ``FERNET_KEY``.
    """
    payload = json.dumps({"username": username, "password": password})
    return encrypt(payload)


# ---------------------------------------------------------------------------
# Personal settings endpoints (per-admin)
# ---------------------------------------------------------------------------


@router.get("", response_model=PersonalSettingsResponse)
async def get_settings(
    admin: Annotated[Admin, Depends(get_current_admin)],
) -> PersonalSettingsResponse:
    """Return per-admin panel settings with sensitive fields masked.

    Passwords and bot tokens are reported as boolean flags; their actual
    values are never exposed.
    """
    return PersonalSettingsResponse(
        panel_url=admin.panel_url,
        panel_sub_url=admin.panel_sub_url,
        panel_username=admin.panel_username,
        has_panel_password=bool(admin.panel_password_encrypted),
        has_config_bot_token=bool(admin.config_bot_token_encrypted),
        updated_at=admin.added_at,
    )


@router.put("", response_model=PersonalSettingsResponse)
async def update_settings(
    payload: PersonalSettingsUpdate,
    session: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[Admin, Depends(get_current_admin)],
) -> PersonalSettingsResponse:
    """Update per-admin panel credentials and config-bot token.

    Non-None fields are applied; password and bot token are encrypted
    before storage.  When panel credentials change the ``admin_sessions``
    table is also updated so the bot picks up the new values.
    """
    update_kwargs = _build_admin_update_kwargs(payload)

    if not update_kwargs:
        raise HTTPException(status_code=400, detail="No fields to update")

    admin = await admin_repo.update_panel_settings(
        session, admin.id, **update_kwargs,
    )

    # Sync panel credentials to admin_sessions if panel data is present
    await _sync_admin_session(session, admin, payload)

    # Audit log
    await log_repo.log_action(
        session,
        admin_telegram_id=admin.telegram_id,
        admin_username=admin.username,
        action="update_settings",
        target=None,
        details={"changed_fields": list(update_kwargs.keys())},
    )

    return PersonalSettingsResponse(
        panel_url=admin.panel_url,
        panel_sub_url=admin.panel_sub_url,
        panel_username=admin.panel_username,
        has_panel_password=bool(admin.panel_password_encrypted),
        has_config_bot_token=bool(admin.config_bot_token_encrypted),
        updated_at=admin.added_at,
    )


def _build_admin_update_kwargs(
    payload: PersonalSettingsUpdate,
) -> dict[str, str]:
    """Convert the update payload into keyword arguments for the repo."""
    kwargs: dict[str, str] = {}

    if payload.panel_url is not None:
        kwargs["panel_url"] = payload.panel_url
    if payload.panel_sub_url is not None:
        kwargs["panel_sub_url"] = payload.panel_sub_url
    if payload.panel_username is not None:
        kwargs["panel_username"] = payload.panel_username
    if payload.panel_password is not None:
        kwargs["panel_password_encrypted"] = encrypt(payload.panel_password)
    if payload.config_bot_token is not None:
        kwargs["config_bot_token_encrypted"] = encrypt(payload.config_bot_token)

    return kwargs


async def _sync_admin_session(
    session: AsyncSession,
    admin: Admin,
    payload: PersonalSettingsUpdate,
) -> None:
    """Write panel credentials to the bot's ``admin_sessions`` table.

    The upsert only runs when the admin has a complete set of panel
    credentials (url + username + password).  The password may come from
    the current payload or already be stored in the admin record.
    """
    panel_url = admin.panel_url
    panel_username = admin.panel_username
    panel_password_enc = admin.panel_password_encrypted

    if not panel_url or not panel_username or not panel_password_enc:
        return

    # Decrypt password to build the credentials blob
    try:
        panel_password = decrypt(panel_password_enc)
    except Exception:
        logger.warning("Cannot decrypt panel_password for admin %d", admin.id)
        return

    encrypted_creds = _build_encrypted_credentials(panel_username, panel_password)

    # Find the User row (users.id) for this admin's telegram_id
    user = await user_repo.get_or_create_by_telegram_id(
        session, admin.telegram_id,
    )

    await admin_session_repo.upsert(
        session,
        user_id=user.id,
        panel_url=panel_url,
        encrypted_credentials=encrypted_creds,
    )


# ---------------------------------------------------------------------------
# Connection check
# ---------------------------------------------------------------------------


@router.post("/check", response_model=ConnectionCheckResponse)
async def check_connection(
    admin: Annotated[Admin, Depends(get_current_admin)],
) -> ConnectionCheckResponse:
    """Test connectivity using the current admin's panel credentials.

    Logs in to the 3x-ui panel and performs a lightweight API call.
    Returns success status and round-trip time.
    """
    if not admin.panel_url or not admin.panel_username:
        return ConnectionCheckResponse(
            success=False,
            message="Panel settings are not configured",
            response_time_ms=None,
        )

    if not admin.panel_password_encrypted:
        return ConnectionCheckResponse(
            success=False,
            message="Panel password is not set",
            response_time_ms=None,
        )

    try:
        password = decrypt(admin.panel_password_encrypted)
    except Exception:
        logger.exception("Failed to decrypt panel password for admin %d", admin.id)
        return ConnectionCheckResponse(
            success=False,
            message="Failed to decrypt stored password",
            response_time_ms=None,
        )

    start = time.monotonic()
    try:
        async with PanelClient(
            base_url=admin.panel_url,
            username=admin.panel_username,
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


# ---------------------------------------------------------------------------
# Global settings endpoints (owner-only)
# ---------------------------------------------------------------------------


@router.get("/global", response_model=GlobalSettingsResponse)
async def get_global_settings(
    session: Annotated[AsyncSession, Depends(get_db)],
    _admin: Annotated[Admin, Depends(require_owner)],
) -> GlobalSettingsResponse:
    """Return global settings (owner_id, masked client bot token).

    Only accessible to admins with the ``owner`` role.
    """
    settings = await settings_repo.get_settings(session)

    if settings is None:
        return GlobalSettingsResponse()

    masked_token: str | None = None
    if settings.client_bot_token:
        masked_token = _mask_token(settings.client_bot_token)

    return GlobalSettingsResponse(
        owner_id=settings.owner_id,
        client_bot_token_masked=masked_token,
        updated_at=settings.updated_at,
    )


@router.put("/global", response_model=GlobalSettingsResponse)
async def update_global_settings(
    payload: GlobalSettingsUpdate,
    session: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[Admin, Depends(require_owner)],
) -> GlobalSettingsResponse:
    """Update global settings (owner_id, client bot token).

    Only accessible to admins with the ``owner`` role.
    """
    update_data: dict[str, str | int] = {}

    if payload.owner_id is not None:
        update_data["owner_id"] = payload.owner_id
    if payload.client_bot_token is not None:
        update_data["client_bot_token"] = encrypt(payload.client_bot_token)

    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    settings = await settings_repo.upsert_settings(session, **update_data)

    # Audit log
    await log_repo.log_action(
        session,
        admin_telegram_id=admin.telegram_id,
        admin_username=admin.username,
        action="update_global_settings",
        target=None,
        details={"changed_fields": list(update_data.keys())},
    )

    masked_token: str | None = None
    if settings.client_bot_token:
        masked_token = _mask_token(settings.client_bot_token)

    return GlobalSettingsResponse(
        owner_id=settings.owner_id,
        client_bot_token_masked=masked_token,
        updated_at=settings.updated_at,
    )
