"""Pydantic v2 schemas for the settings API.

These DTOs transfer settings data between the API layer and clients.
Sensitive fields (password, bot token) are never exposed in plaintext;
the response schema uses boolean flags and masked strings instead.
"""

from datetime import datetime

from pydantic import BaseModel


class SettingsResponse(BaseModel):
    """Settings data returned to the client with sensitive fields masked."""

    panel_url: str | None = None
    panel_sub_url: str | None = None
    panel_username: str | None = None
    # True when an encrypted password is stored, never exposes the actual value
    has_password: bool = False
    owner_id: int | None = None
    # Masked token like "••••ab3f", or None if not set
    client_bot_token_masked: str | None = None
    updated_at: datetime | None = None


class SettingsUpdate(BaseModel):
    """Partial update payload — only non-None fields are applied.

    Password and bot token arrive as plaintext; the API layer encrypts
    them with Fernet before persisting.
    """

    panel_url: str | None = None
    panel_sub_url: str | None = None
    panel_username: str | None = None
    panel_password: str | None = None
    owner_id: int | None = None
    client_bot_token: str | None = None


class ConnectionCheckResponse(BaseModel):
    """Result of a panel connectivity check."""

    success: bool
    message: str
    response_time_ms: int | None = None
