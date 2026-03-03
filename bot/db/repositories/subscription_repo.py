"""Repository for Subscription CRUD operations."""

from datetime import datetime

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from bot.db.models import Subscription
from bot.dto import SubscriptionDTO


class SubscriptionRepository:
    """Data-access layer for the subscriptions table."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_active(self, user_id: int, now: datetime) -> SubscriptionDTO | None:
        """Return the most recent active subscription for a user, or None."""
        stmt = (
            select(Subscription)
            .where(
                and_(
                    Subscription.user_id == user_id,
                    Subscription.expires_at > now,
                )
            )
            .order_by(Subscription.expires_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        sub = result.scalar_one_or_none()
        if sub is None:
            return None
        return SubscriptionDTO.model_validate(sub)

    async def create(
        self,
        user_id: int,
        source: str,
        started_at: datetime,
        expires_at: datetime,
        promo_code: str | None = None,
    ) -> SubscriptionDTO:
        """Create a new subscription record."""
        sub = Subscription(
            user_id=user_id,
            started_at=started_at,
            expires_at=expires_at,
            source=source,
            promo_code=promo_code,
        )
        self._session.add(sub)
        await self._session.flush()
        await self._session.refresh(sub)
        return SubscriptionDTO.model_validate(sub)

    async def has_used_promo(self, user_id: int, code: str) -> bool:
        """Check if a user has already used a specific promo code."""
        stmt = (
            select(Subscription.id)
            .where(
                and_(
                    Subscription.user_id == user_id,
                    Subscription.promo_code == code,
                )
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    # -- Notification-related queries ----------------------------------------

    async def get_expiring_soon(
        self,
        window_start: datetime,
        window_end: datetime,
    ) -> list[Subscription]:
        """Return subscriptions expiring within [window_start, window_end] not yet notified.

        Eagerly loads the related User so that callers can access
        ``sub.user.telegram_id`` without a lazy load.
        """
        stmt = (
            select(Subscription)
            .options(joinedload(Subscription.user))
            .where(
                and_(
                    Subscription.expires_at >= window_start,
                    Subscription.expires_at <= window_end,
                    Subscription.notified_3d.is_(False),
                )
            )
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().unique().all())

    async def get_expired_unnotified(self, now: datetime) -> list[Subscription]:
        """Return expired subscriptions that have not been notified yet.

        Eagerly loads User for telegram_id access.
        """
        stmt = (
            select(Subscription)
            .options(joinedload(Subscription.user))
            .where(
                and_(
                    Subscription.expires_at <= now,
                    Subscription.notified_expired.is_(False),
                )
            )
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().unique().all())

    async def get_pending_sync(self) -> list[Subscription]:
        """Return subscriptions awaiting expiryTime sync retry."""
        stmt = (
            select(Subscription)
            .where(Subscription.configs_sync_pending.is_(True))
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def mark_notified_3d(self, sub_id: int) -> None:
        """Set notified_3d = True for the given subscription."""
        stmt = (
            update(Subscription)
            .where(Subscription.id == sub_id)
            .values(notified_3d=True)
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def mark_notified_expired(self, sub_id: int) -> None:
        """Set notified_expired = True for the given subscription."""
        stmt = (
            update(Subscription)
            .where(Subscription.id == sub_id)
            .values(notified_expired=True)
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def set_sync_pending(self, sub_id: int, *, pending: bool) -> None:
        """Set or clear the configs_sync_pending flag."""
        stmt = (
            update(Subscription)
            .where(Subscription.id == sub_id)
            .values(configs_sync_pending=pending)
        )
        await self._session.execute(stmt)
        await self._session.flush()
