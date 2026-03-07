"""Repository for BotSettings CRUD operations."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import BotSettings


async def get_settings(session: AsyncSession) -> BotSettings | None:
    """Return the singleton settings row, or None if not yet created."""
    stmt = select(BotSettings).where(BotSettings.id == 1)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def upsert_settings(
    session: AsyncSession,
    **kwargs: str | int | None,
) -> BotSettings:
    """Create or update the singleton settings row.

    Accepts arbitrary keyword arguments matching BotSettings columns.
    Only non-None values are applied so callers can do partial updates.
    """
    settings = await get_settings(session)

    if settings is None:
        settings = BotSettings(id=1)
        session.add(settings)

    for key, value in kwargs.items():
        # Guard against invalid column names
        if not hasattr(BotSettings, key):
            raise ValueError(f"BotSettings has no column '{key}'")
        if value is not None:
            setattr(settings, key, value)

    await session.flush()
    await session.refresh(settings)
    return settings
