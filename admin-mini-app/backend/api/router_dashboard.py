"""Dashboard API router.

Provides endpoints for aggregated statistics and recent events displayed
on the admin panel's main dashboard.  All endpoints require admin authentication.
"""

from datetime import UTC, datetime
from typing import Annotated

from db.models import Admin
from db.repositories import dashboard_repo
from fastapi import APIRouter, Depends
from schemas.dashboard import (
    DashboardEvent,
    DashboardEventsResponse,
    DashboardStatsResponse,
)
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_admin, get_db

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

EVENT_TYPE_CONFIG = {
    "subscription": {"emoji": "\u2705", "template": "Новая подписка — {name}"},
    "expiring": {"emoji": "\u26A0\uFE0F", "template": "Истекает подписка — {name}"},
}


def _format_time_ago(dt: datetime) -> str:
    """Format a datetime as a human-readable Russian 'time ago' string."""
    now = datetime.now(UTC)
    if dt.tzinfo is None:
        diff = now.replace(tzinfo=None) - dt
    else:
        diff = now - dt

    total_seconds = int(diff.total_seconds())

    if total_seconds < 0:
        # Future event — show how soon
        total_seconds = abs(total_seconds)
        if total_seconds < 3600:
            minutes = max(1, total_seconds // 60)
            return f"через {minutes} мин."
        if total_seconds < 86400:
            hours = total_seconds // 3600
            return f"через {hours} ч."
        days = total_seconds // 86400
        return f"через {days} дн."

    if total_seconds < 60:
        return "только что"
    if total_seconds < 3600:
        minutes = total_seconds // 60
        return f"{minutes} мин. назад"
    if total_seconds < 86400:
        hours = total_seconds // 3600
        return f"{hours} ч. назад"
    days = total_seconds // 86400
    return f"{days} дн. назад"


@router.get("/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    session: Annotated[AsyncSession, Depends(get_db)],
    _admin: Annotated[Admin, Depends(get_current_admin)],
) -> DashboardStatsResponse:
    """Return aggregated statistics for the admin dashboard."""
    total_users = await dashboard_repo.count_total_users(session)
    paid_users = await dashboard_repo.count_paid_users(session)
    expiring_soon = await dashboard_repo.count_expiring_soon(session)
    active_configs = await dashboard_repo.count_active_configs(session)

    return DashboardStatsResponse(
        total_users=total_users,
        paid_users=paid_users,
        expiring_soon=expiring_soon,
        active_configs=active_configs,
    )


@router.get("/events", response_model=DashboardEventsResponse)
async def get_dashboard_events(
    session: Annotated[AsyncSession, Depends(get_db)],
    _admin: Annotated[Admin, Depends(get_current_admin)],
) -> DashboardEventsResponse:
    """Return recent activity events for the dashboard feed.

    Derives events from user subscription and expiration data.
    """
    raw_events = await dashboard_repo.get_recent_events(session)

    items: list[DashboardEvent] = []
    for event in raw_events:
        cfg = EVENT_TYPE_CONFIG.get(event["event_type"])
        if not cfg:
            continue
        items.append(
            DashboardEvent(
                emoji=cfg["emoji"],
                title=cfg["template"].format(name=event["display_name"]),
                time_ago=_format_time_ago(event["event_time"]),
            )
        )

    return DashboardEventsResponse(items=items)
