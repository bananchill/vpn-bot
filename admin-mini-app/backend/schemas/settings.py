"""Pydantic v2 schemas for the settings API.

Split into two groups:
- **Personal** (per-admin panel credentials and config-bot token)
- **Global** (owner-only: owner_id, client_bot_token for the admin bot)

Sensitive fields are never exposed in plaintext; boolean flags and masked
strings are used instead.
"""

from datetime import datetime

from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Personal settings (per-admin)
# ---------------------------------------------------------------------------


class PersonalSettingsResponse(BaseModel):
    """Per-admin settings returned by ``GET /api/settings``."""

    panel_url: str | None = None
    panel_sub_url: str | None = None
    panel_username: str | None = None
    has_panel_password: bool = False
    has_config_bot_token: bool = False
    updated_at: datetime | None = None


class PersonalSettingsUpdate(BaseModel):
    """Partial update payload for ``PUT /api/settings``.

    Password and bot token arrive as plaintext; the API layer encrypts
    them with Fernet before persisting.  Only non-None fields are applied.
    """

    panel_url: str | None = None
    panel_sub_url: str | None = None
    panel_username: str | None = None
    panel_password: str | None = None
    config_bot_token: str | None = None


# ---------------------------------------------------------------------------
# Global settings (owner-only)
# ---------------------------------------------------------------------------


class GlobalSettingsResponse(BaseModel):
    """Global settings returned by ``GET /api/settings/global``."""

    owner_id: int | None = None
    client_bot_token_masked: str | None = None
    updated_at: datetime | None = None


class GlobalSettingsUpdate(BaseModel):
    """Update payload for ``PUT /api/settings/global``.

    Only the owner can change these values.
    """

    owner_id: int | None = None
    client_bot_token: str | None = None


# ---------------------------------------------------------------------------
# Connection check (shared)
# ---------------------------------------------------------------------------


class ConnectionCheckResponse(BaseModel):
    """Result of a panel connectivity check."""

    success: bool
    message: str
    response_time_ms: int | None = None
