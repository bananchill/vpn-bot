"""APScheduler setup for periodic background tasks.

Provides a module-level ``scheduler`` instance and a ``setup_scheduler``
helper to wire it to the bot and DB session factory.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from bot.services.notification_service import check_and_notify_expiring

if TYPE_CHECKING:
    from aiogram import Bot
    from sqlalchemy.ext.asyncio import async_sessionmaker

scheduler = AsyncIOScheduler()


def setup_scheduler(bot: Bot, session_factory: async_sessionmaker) -> None:
    """Register periodic jobs on the global scheduler.

    Must be called before ``scheduler.start()``.
    """
    scheduler.add_job(
        check_and_notify_expiring,
        IntervalTrigger(hours=1),
        args=[bot, session_factory],
        id="notify_expiring",
        # Safe on repeated calls: silently replaces the existing job
        # instead of raising ConflictingIdError.
        replace_existing=True,
    )
