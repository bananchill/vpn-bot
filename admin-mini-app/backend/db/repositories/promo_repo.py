"""Repository for PromoCode CRUD and atomic usage operations.

All database access for promo codes is encapsulated here.
Functions accept an AsyncSession and return ORM model instances;
the API layer is responsible for converting them to Pydantic DTOs.
"""

import secrets
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.models import PromoCode, PromoUsage


async def get_promos(
    session: AsyncSession,
    *,
    page: int = 1,
    per_page: int = 20,
    is_active: bool | None = None,
) -> tuple[list[PromoCode], int]:
    """Return a paginated list of promo codes with optional active filter.

    Args:
        session: Active database session.
        page: 1-based page number.
        per_page: Number of items per page.
        is_active: Filter by active status, or None for all.

    Returns:
        A tuple of (promo_list, total_count).
    """
    base = select(PromoCode)
    count_base = select(func.count()).select_from(PromoCode)

    if is_active is not None:
        base = base.where(PromoCode.is_active == is_active)
        count_base = count_base.where(PromoCode.is_active == is_active)

    # Total count
    total_result = await session.execute(count_base)
    total = total_result.scalar_one()

    # Paginated results
    offset = (page - 1) * per_page
    base = base.order_by(PromoCode.created_at.desc()).offset(offset).limit(per_page)
    result = await session.execute(base)
    promos = list(result.scalars().all())

    return promos, total


async def get_promo_by_id(
    session: AsyncSession,
    promo_id: int,
) -> PromoCode | None:
    """Return a single promo code by its primary key, or None."""
    stmt = select(PromoCode).where(PromoCode.id == promo_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_promo_by_code(
    session: AsyncSession,
    code: str,
) -> PromoCode | None:
    """Return a single promo code by its unique code string, or None."""
    stmt = select(PromoCode).where(PromoCode.code == code)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create_promo(
    session: AsyncSession,
    *,
    code: str,
    discount_percent: int,
    max_activations: int,
    valid_until: datetime,
) -> PromoCode:
    """Create a new promo code and return it.

    The caller must ensure code uniqueness before calling this function.
    """
    promo = PromoCode(
        code=code,
        discount_percent=discount_percent,
        max_activations=max_activations,
        valid_until=valid_until,
    )
    session.add(promo)
    await session.flush()
    await session.refresh(promo)
    return promo


async def toggle_promo(
    session: AsyncSession,
    promo_id: int,
    is_active: bool,
) -> PromoCode | None:
    """Toggle the active flag on a promo code. Returns updated promo or None."""
    promo = await get_promo_by_id(session, promo_id)
    if promo is None:
        return None

    promo.is_active = is_active
    await session.flush()
    await session.refresh(promo)
    return promo


async def delete_promo(
    session: AsyncSession,
    promo_id: int,
    *,
    promo: PromoCode | None = None,
) -> bool:
    """Delete a promo code by ID. Returns True if deleted, False if not found.

    If a pre-fetched ``promo`` instance is provided, it is deleted directly
    without an extra SELECT, saving a round-trip when the caller already has it.
    """
    if promo is None:
        promo = await get_promo_by_id(session, promo_id)
    if promo is None:
        return False

    await session.delete(promo)
    await session.flush()
    return True


async def get_promo_usages(
    session: AsyncSession,
    promo_id: int,
    *,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[PromoUsage], int]:
    """Return paginated usage records for a promo code with user info.

    Each PromoUsage has its `user` relationship eagerly loaded so the
    caller can access username and first_name without extra queries.
    """
    count_stmt = (
        select(func.count())
        .select_from(PromoUsage)
        .where(PromoUsage.promo_id == promo_id)
    )
    total_result = await session.execute(count_stmt)
    total = total_result.scalar_one()

    offset = (page - 1) * per_page
    stmt = (
        select(PromoUsage)
        .where(PromoUsage.promo_id == promo_id)
        .options(selectinload(PromoUsage.user))
        .order_by(PromoUsage.used_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    result = await session.execute(stmt)
    usages = list(result.scalars().all())

    return usages, total


async def generate_unique_code(
    session: AsyncSession,
    max_attempts: int = 5,
) -> str | None:
    """Generate a random 8-character alphanumeric code that is unique in DB.

    Uses secrets.token_hex(4) to produce 8 hex digits [0-9A-F].
    Retries up to `max_attempts` times on collision.

    Returns the generated code, or None if all attempts collide.
    """
    for _ in range(max_attempts):
        code = secrets.token_hex(4).upper()
        existing = await get_promo_by_code(session, code)
        if existing is None:
            return code
    return None


async def code_exists(session: AsyncSession, code: str) -> bool:
    """Check whether a promo code with the given code string already exists."""
    stmt = (
        select(func.count())
        .select_from(PromoCode)
        .where(PromoCode.code == code)
    )
    result = await session.execute(stmt)
    return result.scalar_one() > 0
