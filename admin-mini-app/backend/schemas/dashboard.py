"""Pydantic v2 schemas for the dashboard API.

These DTOs transfer aggregated statistics to the admin panel frontend.
"""

from pydantic import BaseModel


class DashboardStatsResponse(BaseModel):
    """Aggregated dashboard statistics."""

    total_users: int
    paid_users: int
    expiring_soon: int
    active_configs: int


class DashboardEvent(BaseModel):
    """Single activity event on the dashboard."""

    emoji: str
    title: str
    time_ago: str


class DashboardEventsResponse(BaseModel):
    """List of recent dashboard events."""

    items: list[DashboardEvent]
