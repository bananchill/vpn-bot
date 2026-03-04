"""Users API router.

Provides endpoints for listing, viewing, blocking, annotating, and
extending subscriptions of VPN service users.  All endpoints require
admin authentication.
"""

import logging
import math
from typing import Annotated

from db.models import Admin
from db.repositories import user_repo
from fastapi import APIRouter, Depends, HTTPException, Query
from schemas.config import ConfigResponse
from schemas.user import (
    SortField,
    SortOrder,
    SubscriptionFilter,
    UserBlockRequest,
    UserDetail,
    UserExtendRequest,
    UserListResponse,
    UserNoteRequest,
    UserShort,
)
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_admin, get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/users", tags=["users"])


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=UserListResponse)
async def list_users(
    session: Annotated[AsyncSession, Depends(get_db)],
    _admin: Annotated[Admin, Depends(get_current_admin)],
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=100)] = 20,
    search: str | None = None,
    is_paid: bool | None = None,
    subscription: SubscriptionFilter | None = None,
    sort_by: SortField = "created_at",
    sort_order: SortOrder = "desc",
) -> UserListResponse:
    """Return a paginated, filtered list of users.

    Supports search by username/first_name/telegram_id, filters by
    payment status and subscription state, and configurable sorting.
    """
    users, total = await user_repo.get_users(
        session,
        page=page,
        per_page=per_page,
        search=search,
        is_paid=is_paid,
        subscription=subscription,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    pages = max(1, math.ceil(total / per_page))

    items = [
        UserShort(
            id=u.id,
            telegram_id=u.telegram_id,
            username=u.username,
            first_name=u.first_name,
            photo_url=u.photo_url,
            is_paid=u.is_paid,
            is_blocked=u.is_blocked,
            subscription_expires=u.subscription_expires,
        )
        for u in users
    ]

    return UserListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.get("/{user_id}", response_model=UserDetail)
async def get_user(
    user_id: int,
    session: Annotated[AsyncSession, Depends(get_db)],
    _admin: Annotated[Admin, Depends(get_current_admin)],
) -> UserDetail:
    """Return full details for a single user including their VPN configs."""
    user = await user_repo.get_user_by_id(session, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    configs = [
        ConfigResponse(
            id=c.id,
            client_id=c.client_id,
            email=c.email,
            protocol=c.protocol,
            created_at=c.created_at,
        )
        for c in user.configs
    ]

    return UserDetail(
        id=user.id,
        telegram_id=user.telegram_id,
        username=user.username,
        first_name=user.first_name,
        photo_url=user.photo_url,
        is_paid=user.is_paid,
        is_blocked=user.is_blocked,
        subscription_expires=user.subscription_expires,
        subscribed_since=user.subscribed_since,
        admin_note=user.admin_note,
        configs=configs,
        promo_usages=[],
    )


@router.patch("/{user_id}/block", response_model=UserShort)
async def toggle_block(
    user_id: int,
    payload: UserBlockRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
    _admin: Annotated[Admin, Depends(get_current_admin)],
) -> UserShort:
    """Block or unblock a user."""
    user = await user_repo.update_user_blocked(
        session, user_id, payload.is_blocked
    )
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    action = "blocked" if payload.is_blocked else "unblocked"
    logger.info("User %d %s by admin", user_id, action)

    return UserShort(
        id=user.id,
        telegram_id=user.telegram_id,
        username=user.username,
        first_name=user.first_name,
        photo_url=user.photo_url,
        is_paid=user.is_paid,
        is_blocked=user.is_blocked,
        subscription_expires=user.subscription_expires,
    )


@router.patch("/{user_id}/note", response_model=UserShort)
async def update_note(
    user_id: int,
    payload: UserNoteRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
    _admin: Annotated[Admin, Depends(get_current_admin)],
) -> UserShort:
    """Update the admin note on a user."""
    user = await user_repo.update_user_note(session, user_id, payload.note)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return UserShort(
        id=user.id,
        telegram_id=user.telegram_id,
        username=user.username,
        first_name=user.first_name,
        photo_url=user.photo_url,
        is_paid=user.is_paid,
        is_blocked=user.is_blocked,
        subscription_expires=user.subscription_expires,
    )


@router.patch("/{user_id}/extend", response_model=UserDetail)
async def extend_subscription(
    user_id: int,
    payload: UserExtendRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
    _admin: Annotated[Admin, Depends(get_current_admin)],
) -> UserDetail:
    """Extend a user's subscription by the specified number of days.

    Returns the full user detail so the frontend can refresh all fields
    (is_paid, subscription_expires, subscribed_since may all change).
    """
    if payload.days <= 0:
        raise HTTPException(
            status_code=400, detail="Days must be a positive integer"
        )

    user = await user_repo.extend_subscription(session, user_id, payload.days)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    logger.info("Subscription extended by %d days for user %d", payload.days, user_id)

    # Reload configs since extend_subscription uses get_user_by_id with selectinload
    configs = [
        ConfigResponse(
            id=c.id,
            client_id=c.client_id,
            email=c.email,
            protocol=c.protocol,
            created_at=c.created_at,
        )
        for c in user.configs
    ]

    return UserDetail(
        id=user.id,
        telegram_id=user.telegram_id,
        username=user.username,
        first_name=user.first_name,
        photo_url=user.photo_url,
        is_paid=user.is_paid,
        is_blocked=user.is_blocked,
        subscription_expires=user.subscription_expires,
        subscribed_since=user.subscribed_since,
        admin_note=user.admin_note,
        configs=configs,
        promo_usages=[],
    )
