"""Repository for Admin CRUD operations."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Admin


async def get_by_telegram_id(
    session: AsyncSession,
    telegram_id: int,
) -> Admin | None:
    """Return an admin by their Telegram ID, or None."""
    stmt = select(Admin).where(Admin.telegram_id == telegram_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def count(session: AsyncSession) -> int:
    """Return the total number of admin records."""
    stmt = select(func.count()).select_from(Admin)
    result = await session.execute(stmt)
    return result.scalar_one()


async def create(
    session: AsyncSession,
    telegram_id: int,
    role: str = "owner",
) -> Admin:
    """Create a new admin record and return it.

    The first admin auto-created during initial setup receives the 'owner' role.
    Subsequent admins added through the UI default to 'moderator'.
    """
    admin = Admin(telegram_id=telegram_id, role=role)
    session.add(admin)
    await session.flush()
    await session.refresh(admin)
    return admin
