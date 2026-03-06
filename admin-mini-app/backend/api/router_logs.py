"""Admin logs API router.

Provides an endpoint for viewing the admin action audit log with
filtering and pagination.  Requires admin authentication.
"""

import logging
from typing import Annotated

from db.models import Admin
from db.repositories import log_repo
from fastapi import APIRouter, Depends, Query
from schemas.log import LogEntry, LogListResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_admin, get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/logs", tags=["logs"])


@router.get("", response_model=LogListResponse)
async def list_logs(
    session: Annotated[AsyncSession, Depends(get_db)],
    _admin: Annotated[Admin, Depends(get_current_admin)],
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=100)] = 20,
    action: str | None = None,
    admin_id: int | None = None,
) -> LogListResponse:
    """Return a paginated list of admin action logs with optional filters.

    Includes `available_actions` — a list of all distinct action types
    present in the log, so the frontend can populate a filter dropdown.
    """
    logs, total = await log_repo.get_logs(
        session,
        page=page,
        per_page=per_page,
        action=action,
        admin_id=admin_id,
    )

    available_actions = await log_repo.get_available_actions(session)

    items = [
        LogEntry(
            id=log.id,
            admin_telegram_id=log.admin_telegram_id,
            admin_username=log.admin_username,
            action=log.action,
            target=log.target,
            details=log.details,
            created_at=log.created_at,
        )
        for log in logs
    ]

    return LogListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        available_actions=available_actions,
    )
