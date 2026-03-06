"""Repository for dashboard aggregation queries.

All database access for dashboard statistics is encapsulated here.
Functions accept an AsyncSession and return plain scalar values;
the API layer assembles them into Pydantic DTOs.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import PromoCode, User, VPNConfig


class UserCounts:
    """Container for aggregated user statistics from a single query."""

    __slots__ = (
        "total_users",
        "paid_users",
        "unpaid_users",
        "expiring_soon",
        "new_users_30d",
    )

    def __init__(
        self,
        *,
        total_users: int,
        paid_users: int,
        unpaid_users: int,
        expiring_soon: int,
        new_users_30d: int,
    ) -> None:
        self.total_users = total_users
        self.paid_users = paid_users
        self.unpaid_users = unpaid_users
        self.expiring_soon = expiring_soon
        self.new_users_30d = new_users_30d


async def get_user_counts(session: AsyncSession) -> UserCounts:
    """Return all user-related dashboard counts in a single query.

    Consolidates total_users, paid_users, unpaid_users, expiring_soon,
    and new_users_30d into one SELECT to reduce round-trips.
    """
    now = datetime.now(UTC)
    week_later = now + timedelta(days=7)
    thirty_days_ago = now - timedelta(days=30)

    stmt = select(
        func.count().label("total_users"),
        func.count().filter(User.is_paid.is_(True)).label("paid_users"),
        func.count().filter(User.is_paid.is_(False)).label("unpaid_users"),
        func.count().filter(
            User.subscription_expires.between(now, week_later)
        ).label("expiring_soon"),
        func.count().filter(User.created_at >= thirty_days_ago).label(
            "new_users_30d"
        ),
    ).select_from(User)

    result = await session.execute(stmt)
    row = result.one()

    return UserCounts(
        total_users=row.total_users,
        paid_users=row.paid_users,
        unpaid_users=row.unpaid_users,
        expiring_soon=row.expiring_soon,
        new_users_30d=row.new_users_30d,
    )


async def count_active_configs(session: AsyncSession) -> int:
    """Return the total number of VPN configs."""
    result = await session.execute(
        select(func.count()).select_from(VPNConfig)
    )
    return result.scalar_one()


async def count_active_promos(session: AsyncSession) -> int:
    """Return the number of promo codes that are active and not expired."""
    now = datetime.now(UTC)
    result = await session.execute(
        select(func.count())
        .select_from(PromoCode)
        .where(PromoCode.is_active.is_(True), PromoCode.valid_until > now)
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
