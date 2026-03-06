"""Promo codes API router.

Provides endpoints for creating, listing, toggling, deleting promo codes,
generating unique codes, and viewing usage history.  All endpoints require
admin authentication.  Mutating operations are recorded in the audit log.
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Annotated

from db.models import Admin, PromoCode
from db.repositories import log_repo, promo_repo
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from schemas.promo import (
    GenerateCodeResponse,
    PromoCreate,
    PromoListResponse,
    PromoResponse,
    PromoToggleRequest,
    PromoUsageListResponse,
    PromoUsageResponse,
)
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_admin, get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/promos", tags=["promos"])

# TODO: admin_username is None because Admin model doesn't store Telegram username.
# Future: extract username from initData in deps.py and pass through.


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _promo_to_response(promo: PromoCode) -> PromoResponse:
    """Convert an ORM PromoCode instance to a response schema."""
    return PromoResponse(
        id=promo.id,
        code=promo.code,
        discount_percent=promo.discount_percent,
        max_activations=promo.max_activations,
        current_activations=promo.current_activations,
        valid_until=promo.valid_until,
        is_active=promo.is_active,
        created_at=promo.created_at,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=PromoListResponse)
async def list_promos(
    session: Annotated[AsyncSession, Depends(get_db)],
    _admin: Annotated[Admin, Depends(get_current_admin)],
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=100)] = 20,
    is_active: bool | None = None,
) -> PromoListResponse:
    """Return a paginated list of promo codes with optional active filter."""
    promos, total = await promo_repo.get_promos(
        session, page=page, per_page=per_page, is_active=is_active
    )

    return PromoListResponse(
        items=[_promo_to_response(p) for p in promos],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.post("", response_model=PromoResponse, status_code=201)
async def create_promo(
    payload: PromoCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[Admin, Depends(get_current_admin)],
) -> PromoResponse:
    """Create a new promo code.

    Validates code uniqueness and computes ``valid_until`` from
    ``valid_days`` if an absolute timestamp is not provided.
    """
    # Check code uniqueness
    if await promo_repo.code_exists(session, payload.code):
        raise HTTPException(status_code=409, detail="Promo code already exists")

    # Compute valid_until from valid_days if needed
    if payload.valid_until is not None:
        valid_until = payload.valid_until
        if valid_until.astimezone(UTC) < datetime.now(UTC):
            raise HTTPException(
                status_code=400, detail="valid_until must be in the future"
            )
    else:
        # valid_days is guaranteed non-None by the model validator
        valid_until = datetime.now(UTC) + timedelta(days=payload.valid_days)  # type: ignore[arg-type]

    promo = await promo_repo.create_promo(
        session,
        code=payload.code,
        discount_percent=payload.discount_percent,
        max_activations=payload.max_activations,
        valid_until=valid_until,
    )

    # Audit log
    await log_repo.log_action(
        session,
        admin_telegram_id=admin.telegram_id,
        admin_username=None,
        action="create_promo",
        target=promo.code,
        details={
            "discount_percent": payload.discount_percent,
            "max_activations": payload.max_activations,
        },
    )

    logger.info("Promo code %s created by admin %d", promo.code, admin.telegram_id)
    return _promo_to_response(promo)


@router.get("/generate-code", response_model=GenerateCodeResponse)
async def generate_code(
    session: Annotated[AsyncSession, Depends(get_db)],
    _admin: Annotated[Admin, Depends(get_current_admin)],
) -> GenerateCodeResponse:
    """Generate a unique random 8-character promo code [0-9A-F]."""
    code = await promo_repo.generate_unique_code(session)
    if code is None:
        raise HTTPException(
            status_code=409,
            detail="Failed to generate a unique code after multiple attempts",
        )
    return GenerateCodeResponse(code=code)


@router.get("/{promo_id}", response_model=PromoResponse)
async def get_promo(
    promo_id: int,
    session: Annotated[AsyncSession, Depends(get_db)],
    _admin: Annotated[Admin, Depends(get_current_admin)],
) -> PromoResponse:
    """Return full details for a single promo code."""
    promo = await promo_repo.get_promo_by_id(session, promo_id)
    if promo is None:
        raise HTTPException(status_code=404, detail="Promo code not found")
    return _promo_to_response(promo)


@router.patch("/{promo_id}/toggle", response_model=PromoResponse)
async def toggle_promo(
    promo_id: int,
    payload: PromoToggleRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[Admin, Depends(get_current_admin)],
) -> PromoResponse:
    """Toggle the active state of a promo code."""
    promo = await promo_repo.toggle_promo(session, promo_id, payload.is_active)
    if promo is None:
        raise HTTPException(status_code=404, detail="Promo code not found")

    # Audit log
    await log_repo.log_action(
        session,
        admin_telegram_id=admin.telegram_id,
        admin_username=None,
        action="toggle_promo",
        target=promo.code,
        details={"is_active": payload.is_active},
    )

    logger.info(
        "Promo code %s toggled to %s by admin %d",
        promo.code,
        payload.is_active,
        admin.telegram_id,
    )
    return _promo_to_response(promo)


@router.delete("/{promo_id}", status_code=204)
async def delete_promo(
    promo_id: int,
    session: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[Admin, Depends(get_current_admin)],
) -> Response:
    """Delete a promo code. Returns 204 on success."""
    # Fetch first to get the code for the audit log
    promo = await promo_repo.get_promo_by_id(session, promo_id)
    if promo is None:
        raise HTTPException(status_code=404, detail="Promo code not found")

    promo_code = promo.code
    await promo_repo.delete_promo(session, promo_id, promo=promo)

    # Audit log
    await log_repo.log_action(
        session,
        admin_telegram_id=admin.telegram_id,
        admin_username=None,
        action="delete_promo",
        target=promo_code,
    )

    logger.info("Promo code %s deleted by admin %d", promo_code, admin.telegram_id)
    return Response(status_code=204)


@router.get("/{promo_id}/usages", response_model=PromoUsageListResponse)
async def list_promo_usages(
    promo_id: int,
    session: Annotated[AsyncSession, Depends(get_db)],
    _admin: Annotated[Admin, Depends(get_current_admin)],
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PromoUsageListResponse:
    """Return paginated usage history for a promo code with user info."""
    # Verify promo exists
    promo = await promo_repo.get_promo_by_id(session, promo_id)
    if promo is None:
        raise HTTPException(status_code=404, detail="Promo code not found")

    usages, total = await promo_repo.get_promo_usages(
        session, promo_id, page=page, per_page=per_page
    )

    items = [
        PromoUsageResponse(
            user_id=u.user_id,
            username=u.user.username if u.user else None,
            first_name=u.user.first_name if u.user else None,
            used_at=u.used_at,
        )
        for u in usages
    ]

    return PromoUsageListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
    )
