"""Pydantic v2 schemas for the VPN config API.

These DTOs transfer config data between the API layer and clients.
Config state is synchronized with the external 3x-ui panel.
"""

from datetime import datetime

from pydantic import BaseModel


class ConfigResponse(BaseModel):
    """Single VPN configuration returned to the client."""

    id: int
    client_id: str
    email: str
    protocol: str
    created_at: datetime


class ConfigToggle(BaseModel):
    """Payload for toggling a single config's enabled state."""

    enabled: bool


class ConfigToggleAllRequest(BaseModel):
    """Payload for toggling all configs of a user at once."""

    enabled: bool


class ConfigToggleAllResponse(BaseModel):
    """Result of a bulk config toggle operation."""

    updated_count: int
    success: bool
