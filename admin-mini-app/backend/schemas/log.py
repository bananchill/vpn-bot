"""Pydantic v2 schemas for the admin logs API.

These DTOs transfer audit log entries between the API layer and clients.
"""

from datetime import datetime

from pydantic import BaseModel


class LogEntry(BaseModel):
    """Single admin action log entry."""

    id: int
    admin_telegram_id: int
    admin_username: str | None = None
    action: str
    target: str | None = None
    details: str | None = None
    created_at: datetime


class LogListResponse(BaseModel):
    """Paginated list of admin log entries with available action filters."""

    items: list[LogEntry]
    total: int
    page: int
    per_page: int
    available_actions: list[str]
