"""Repository for VPNConfig CRUD operations.

Handles all database access for VPN configuration records.
Panel-side synchronization is handled at the API router layer,
keeping this repository focused on local DB state only.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import VPNConfig


async def get_user_configs(
    session: AsyncSession,
    user_id: int,
) -> list[VPNConfig]:
    """Return all VPN configs belonging to the given user."""
    stmt = (
        select(VPNConfig)
        .where(VPNConfig.user_id == user_id)
        .order_by(VPNConfig.created_at.asc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_config_by_id(
    session: AsyncSession,
    config_id: int,
) -> VPNConfig | None:
    """Return a single config by its primary key, or None."""
    stmt = select(VPNConfig).where(VPNConfig.id == config_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()
