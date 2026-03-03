"""Repository for PromoCode CRUD operations."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import PromoCode
from bot.dto import PromoCodeDTO


class PromoCodeRepository:
    """Data-access layer for the promo_codes table."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_code(self, code: str) -> PromoCodeDTO | None:
        """Return a promo code by its code string (case-insensitive via lowercase)."""
        stmt = select(PromoCode).where(PromoCode.code == code.lower())
        result = await self._session.execute(stmt)
        promo = result.scalar_one_or_none()
        if promo is None:
            return None
        return PromoCodeDTO.model_validate(promo)

    async def create(self, code: str) -> PromoCodeDTO:
        """Create a new promo code (stored lowercase)."""
        promo = PromoCode(code=code.lower())
        self._session.add(promo)
        await self._session.flush()
        await self._session.refresh(promo)
        return PromoCodeDTO.model_validate(promo)

    async def increment_use_count(self, code: str) -> None:
        """Increment the use_count for a promo code."""
        stmt = select(PromoCode).where(PromoCode.code == code.lower())
        result = await self._session.execute(stmt)
        promo = result.scalar_one_or_none()
        if promo is not None:
            promo.use_count += 1
            await self._session.flush()

    async def deactivate(self, code: str) -> bool:
        """Deactivate a promo code. Returns True if found and deactivated."""
        stmt = select(PromoCode).where(PromoCode.code == code.lower())
        result = await self._session.execute(stmt)
        promo = result.scalar_one_or_none()
        if promo is None:
            return False
        promo.is_active = False
        await self._session.flush()
        return True

    async def list_all(self) -> list[PromoCodeDTO]:
        """Return all promo codes ordered by creation date."""
        stmt = select(PromoCode).order_by(PromoCode.created_at.desc())
        result = await self._session.execute(stmt)
        return [PromoCodeDTO.model_validate(p) for p in result.scalars().all()]
