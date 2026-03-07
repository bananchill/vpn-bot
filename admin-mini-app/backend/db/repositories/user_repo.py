"""Repository for User CRUD and query operations.

All database access for the User model is encapsulated here.
Functions accept an AsyncSession and return ORM model instances;
the API layer is responsible for converting them to Pydantic DTOs.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.models import PromoUsage, User
from sqlalchemy import text


async def get_users(
    session: AsyncSession,
    *,
    page: int = 1,
    per_page: int = 20,
    search: str | None = None,
    is_paid: bool | None = None,
    subscription: str | None = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> tuple[list[User], int]:
    """Return a paginated, filtered, and sorted list of users.

    Args:
        session: Active database session.
        page: 1-based page number.
        per_page: Number of items per page.
        search: Filter by username, first_name, or telegram_id (ILIKE / exact).
        is_paid: Filter by payment status.
        subscription: One of "active", "expired", "expiring_7d".
        sort_by: Column to sort on.
        sort_order: "asc" or "desc".

    Returns:
        A tuple of (users_list, total_count).
    """
    base = select(User)
    count_base = select(func.count()).select_from(User)

    # -- search filter -------------------------------------------------------
    if search:
        search_stripped = search.strip()
        like_pattern = f"%{search_stripped}%"
        search_condition = or_(
            User.username.ilike(like_pattern),
            User.first_name.ilike(like_pattern),
            # Allow exact match on telegram_id (cast to string for ILIKE)
            cast(User.telegram_id, String).ilike(like_pattern),
        )
        base = base.where(search_condition)
        count_base = count_base.where(search_condition)

    # -- is_paid filter ------------------------------------------------------
    if is_paid is not None:
        base = base.where(User.is_paid == is_paid)
        count_base = count_base.where(User.is_paid == is_paid)

    # -- subscription filter -------------------------------------------------
    now = datetime.now(UTC)
    if subscription == "active":
        base = base.where(User.subscription_expires > now)
        count_base = count_base.where(User.subscription_expires > now)
    elif subscription == "expired":
        expired_cond = or_(
            User.subscription_expires.is_(None),
            User.subscription_expires <= now,
        )
        base = base.where(expired_cond)
        count_base = count_base.where(expired_cond)
    elif subscription == "expiring_7d":
        week_later = now + timedelta(days=7)
        expiring_cond = (
            User.subscription_expires.between(now, week_later)
        )
        base = base.where(expiring_cond)
        count_base = count_base.where(expiring_cond)

    # -- sorting -------------------------------------------------------------
    sort_column_map = {
        "created_at": User.created_at,
        "first_name": User.first_name,
        "subscription_expires": User.subscription_expires,
    }
    sort_col = sort_column_map.get(sort_by, User.created_at)
    # Push nulls to the end regardless of sort direction
    if sort_order == "asc":
        base = base.order_by(sort_col.asc().nulls_last())
    else:
        base = base.order_by(sort_col.desc().nulls_last())

    # -- total count ---------------------------------------------------------
    total_result = await session.execute(count_base)
    total = total_result.scalar_one()

    # -- pagination ----------------------------------------------------------
    offset = (page - 1) * per_page
    base = base.offset(offset).limit(per_page)

    result = await session.execute(base)
    users = list(result.scalars().all())

    return users, total


async def get_user_by_id(
    session: AsyncSession,
    user_id: int,
) -> User | None:
    """Return a single user with eagerly loaded configs, or None."""
    stmt = (
        select(User)
        .where(User.id == user_id)
        .options(
            selectinload(User.configs),
            selectinload(User.promo_usages).selectinload(PromoUsage.promo),
        )
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def update_user_blocked(
    session: AsyncSession,
    user_id: int,
    is_blocked: bool,
) -> User | None:
    """Toggle the blocked flag on a user. Returns the updated user or None."""
    user = await get_user_by_id(session, user_id)
    if user is None:
        return None

    user.is_blocked = is_blocked
    await session.flush()
    await session.refresh(user)
    return user


async def update_user_note(
    session: AsyncSession,
    user_id: int,
    note: str | None,
) -> User | None:
    """Update the admin note on a user. Pass None to clear the note.

    Returns the updated user or None if the user does not exist.
    """
    user = await get_user_by_id(session, user_id)
    if user is None:
        return None

    # None clears the note; empty string is also allowed
    user.admin_note = note
    await session.flush()
    await session.refresh(user)
    return user


async def extend_subscription(
    session: AsyncSession,
    user_id: int,
    days: int,
) -> User | None:
    """Extend a user's subscription by the given number of days.

    If the subscription has already expired or was never set, the
    extension starts from the current moment. If it is still active,
    the days are added to the current expiry date.

    Returns the updated user or None if the user does not exist.
    """
    user = await get_user_by_id(session, user_id)
    if user is None:
        return None

    now = datetime.now(UTC)

    if user.subscription_expires and user.subscription_expires > now:
        started_at = user.subscription_expires
        user.subscription_expires += timedelta(days=days)
    else:
        started_at = now
        user.subscription_expires = now + timedelta(days=days)

    user.is_paid = True
    if user.subscribed_since is None:
        user.subscribed_since = now

    # Create a record in the subscriptions table so the bot recognizes the subscription
    await session.execute(
        text(
            "INSERT INTO subscriptions (user_id, started_at, expires_at, source) "
            "VALUES (:user_id, :started_at, :expires_at, 'admin')"
        ),
        {
            "user_id": user_id,
            "started_at": started_at,
            "expires_at": user.subscription_expires,
        },
    )

    await session.flush()
    await session.refresh(user)
    return user
