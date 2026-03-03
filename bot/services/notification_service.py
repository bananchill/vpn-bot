"""Background notification service for subscription expiry alerts.

Runs periodically via APScheduler.  Sends Telegram messages to users
whose subscriptions are about to expire (3-day warning) or have already
expired.  Also retries failed expiryTime syncs to the 3x-ui panel.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from bot.config import settings
from bot.db.repositories.subscription_repo import SubscriptionRepository
from bot.keyboards.menus import renew_button
from bot.services import subscription_service
from bot.services.xui_client import XUIClient

if TYPE_CHECKING:
    from aiogram import Bot
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger(__name__)


async def check_and_notify_expiring(
    bot: Bot,
    session_factory: async_sessionmaker,
) -> None:
    """Run all periodic subscription checks in a single pass.

    1. Warn users whose subscription expires in ~3 days.
    2. Notify users whose subscription has already expired.
    3. Retry pending expiryTime syncs to 3x-ui.
    """
    async with session_factory() as session, session.begin():
        now = datetime.now(tz=UTC)
        sub_repo = SubscriptionRepository(session)

        await _notify_expiring_soon(bot, sub_repo, now)
        await _notify_expired(bot, sub_repo, now)
        await _retry_pending_sync(sub_repo, session)


# ---------------------------------------------------------------------------
# Internal helpers — each handles one concern
# ---------------------------------------------------------------------------


async def _notify_expiring_soon(
    bot: Bot,
    sub_repo: SubscriptionRepository,
    now: datetime,
) -> None:
    """Send a 3-day warning to users whose subscription is about to expire.

    The window is [now + 71h, now + 73h] so that the hourly job does
    not miss anyone and the notified_3d flag prevents duplicates.
    """
    window_start = now + timedelta(hours=71)
    window_end = now + timedelta(hours=73)
    expiring = await sub_repo.get_expiring_soon(window_start, window_end)

    for sub in expiring:
        try:
            expires_str = sub.expires_at.strftime("%d.%m.%Y")
            text = (
                f"\u26a0\ufe0f Ваша подписка истекает {expires_str}. "
                "Продлите сейчас, чтобы не потерять доступ."
            )
            await bot.send_message(
                sub.user.telegram_id,
                text,
                reply_markup=renew_button(),
            )
            await sub_repo.mark_notified_3d(sub.id)
            logger.info("Sent 3-day expiry warning to user_id=%s", sub.user_id)
        except Exception:
            logger.warning(
                "Failed to send 3-day notification to user_id=%s",
                sub.user_id,
                exc_info=True,
            )


async def _notify_expired(
    bot: Bot,
    sub_repo: SubscriptionRepository,
    now: datetime,
) -> None:
    """Notify users whose subscription has already expired."""
    expired = await sub_repo.get_expired_unnotified(now)

    for sub in expired:
        try:
            text = (
                "\u274c Ваша подписка истекла. "
                "Создание конфигов недоступно. "
                "Продлите подписку."
            )
            await bot.send_message(
                sub.user.telegram_id,
                text,
                reply_markup=renew_button(),
            )
            await sub_repo.mark_notified_expired(sub.id)
            logger.info("Sent expired notification to user_id=%s", sub.user_id)
        except Exception:
            logger.warning(
                "Failed to send expired notification to user_id=%s",
                sub.user_id,
                exc_info=True,
            )


async def _retry_pending_sync(
    sub_repo: SubscriptionRepository,
    session: AsyncSession,
) -> None:
    """Retry expiryTime sync for subscriptions that failed earlier."""
    pending = await sub_repo.get_pending_sync()

    for sub in pending:
        try:
            xui = XUIClient(settings.PANEL_URL)
            await xui.login(settings.PANEL_USERNAME, settings.PANEL_PASSWORD)
            try:
                success = await subscription_service.sync_configs_expiry(
                    sub.user_id, sub.expires_at, xui, session,
                )
                if success:
                    await sub_repo.set_sync_pending(sub.id, pending=False)
                    logger.info(
                        "Pending sync completed for sub_id=%s user_id=%s",
                        sub.id, sub.user_id,
                    )
            finally:
                await xui.close()
        except Exception:
            logger.warning(
                "Retry sync failed for sub_id=%s user_id=%s",
                sub.id, sub.user_id,
                exc_info=True,
            )
