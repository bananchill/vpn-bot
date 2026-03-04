"""Repository for dashboard aggregation queries.

All database access for dashboard statistics is encapsulated here.
Functions accept an AsyncSession and return plain scalar values;
the API layer assembles them into Pydantic DTOs.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select, union_all, literal, case
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import User, VPNConfig


async def count_total_users(session: AsyncSession) -> int:
    """Return the total number of registered users."""
    result = await session.execute(select(func.count()).select_from(User))
    return result.scalar_one()


async def count_paid_users(session: AsyncSession) -> int:
    """Return the number of users with is_paid=True."""
    result = await session.execute(
        select(func.count()).select_from(User).where(User.is_paid.is_(True))
    )
    return result.scalar_one()


async def count_expiring_soon(session: AsyncSession) -> int:
    """Return the number of users whose subscription expires within 7 days.

    Only includes users whose subscription is still active (expires in the
    future) but will run out within the next 7 days.
    """
    now = datetime.now(UTC)
    week_later = now + timedelta(days=7)
    result = await session.execute(
        select(func.count())
        .select_from(User)
        .where(User.subscription_expires.between(now, week_later))
    )
    return result.scalar_one()


async def count_active_configs(session: AsyncSession) -> int:
    """Return the total number of VPN configs."""
    result = await session.execute(
        select(func.count()).select_from(VPNConfig)
    )
    return result.scalar_one()


async def get_recent_events(
    session: AsyncSession, limit: int = 10
) -> list[dict[str, datetime | str]]:
    """Build a list of recent activity events derived from user data.

    Combines:
    - Recent subscriptions (subscribed_since within last 48h)
    - Upcoming expirations (subscription_expires within next 7 days)
    - Recently blocked users

    Returns dicts with keys: event_type, username, first_name, event_time.
    """
    now = datetime.now(UTC)
    two_days_ago = now - timedelta(hours=48)
    week_later = now + timedelta(days=7)

    # Recent subscriptions
    recent_subs = await session.execute(
        select(
            User.username,
            User.first_name,
            User.subscribed_since.label("event_time"),
        )
        .where(
            User.subscribed_since.isnot(None),
            User.subscribed_since >= two_days_ago,
        )
        .order_by(User.subscribed_since.desc())
        .limit(limit)
    )

    # Upcoming expirations
    expiring = await session.execute(
        select(
            User.username,
            User.first_name,
            User.subscription_expires.label("event_time"),
        )
        .where(
            User.subscription_expires.isnot(None),
            User.subscription_expires.between(now, week_later),
        )
        .order_by(User.subscription_expires.asc())
        .limit(limit)
    )

    events: list[dict[str, datetime | str]] = []

    for row in recent_subs.all():
        name = f"@{row.username}" if row.username else (row.first_name or "user")
        events.append({
            "event_type": "subscription",
            "display_name": name,
            "event_time": row.event_time,
        })

    for row in expiring.all():
        name = f"@{row.username}" if row.username else (row.first_name or "user")
        events.append({
            "event_type": "expiring",
            "display_name": name,
            "event_time": row.event_time,
        })

    # Sort combined list by event_time descending (most recent first)
    events.sort(key=lambda e: e["event_time"], reverse=True)

    return events[:limit]
