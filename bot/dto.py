"""Pydantic DTOs for data transfer between layers.

ORM models stay inside the db layer; handlers and services
only see these lightweight Pydantic objects.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    telegram_id: int
    username: str | None
    is_admin: bool
    created_at: datetime


class ConfigDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    inbound_id: int
    client_id: str
    sub_id: str
    email: str
    protocol: str
    created_at: datetime


class ConfigSummaryDTO(BaseModel):
    """Lightweight DTO for config list display."""

    id: int
    email: str


class SubscriptionDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    started_at: datetime
    expires_at: datetime
    source: str
    promo_code: str | None
    notified_3d: bool = False
    notified_expired: bool = False
    configs_sync_pending: bool = False
    created_at: datetime


class PromoCodeDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    is_active: bool
    use_count: int
    created_at: datetime
