"""Repository for AdminLog operations.

Provides audit logging and log retrieval with filtering and pagination.
All database access for admin action logs is encapsulated here.
"""

import json

from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import AdminLog

# Type alias for JSON-serializable detail values
_DetailValue = str | int | float | bool | list[str] | None


async def log_action(
    session: AsyncSession,
    *,
    admin_telegram_id: int,
    admin_username: str | None,
    action: str,
    target: str | None = None,
    details: dict[str, _DetailValue] | None = None,
) -> AdminLog:
    """Record an admin action in the audit log.

    The log entry is created within the caller's transaction so it
    commits (or rolls back) together with the main operation.

    Args:
        session: Active database session (within a transaction).
        admin_telegram_id: Telegram ID of the admin performing the action.
        admin_username: Telegram username of the admin (may be None).
        action: Action identifier (e.g. "block_user", "create_promo").
        target: Human-readable target of the action (e.g. "@ivan", "SUMMER25").
        details: Optional dict with action-specific context, stored as JSON.

    Returns:
        The created AdminLog instance.
    """
    details_str: str | None = None
    if details is not None:
        details_str = json.dumps(details, ensure_ascii=False)

    log = AdminLog(
        admin_telegram_id=admin_telegram_id,
        admin_username=admin_username,
        action=action,
        target=target,
        details=details_str,
    )
    session.add(log)
    await session.flush()
    return log


async def get_logs(
    session: AsyncSession,
    *,
    page: int = 1,
    per_page: int = 20,
    action: str | None = None,
    admin_id: int | None = None,
) -> tuple[list[AdminLog], int]:
    """Return a paginated list of admin log entries with optional filters.

    Args:
        session: Active database session.
        page: 1-based page number.
        per_page: Number of items per page.
        action: Filter by action type.
        admin_id: Filter by admin's Telegram ID.

    Returns:
        A tuple of (log_entries, total_count).
    """
    base = select(AdminLog)
    count_base = select(func.count()).select_from(AdminLog)

    if action is not None:
        base = base.where(AdminLog.action == action)
        count_base = count_base.where(AdminLog.action == action)

    if admin_id is not None:
        base = base.where(AdminLog.admin_telegram_id == admin_id)
        count_base = count_base.where(AdminLog.admin_telegram_id == admin_id)

    # Total count
    total_result = await session.execute(count_base)
    total = total_result.scalar_one()

    # Paginated results ordered by most recent first
    offset = (page - 1) * per_page
    base = base.order_by(AdminLog.created_at.desc()).offset(offset).limit(per_page)
    result = await session.execute(base)
    logs = list(result.scalars().all())

    return logs, total


async def get_available_actions(session: AsyncSession) -> list[str]:
    """Return a sorted list of distinct action types present in the log."""
    stmt = select(distinct(AdminLog.action)).order_by(AdminLog.action)
    result = await session.execute(stmt)
    return list(result.scalars().all())
