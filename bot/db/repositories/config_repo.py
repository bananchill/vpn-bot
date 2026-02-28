"""Repository for Config CRUD operations."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import Config


class ConfigRepository:
    """Data-access layer for the configs table."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        user_id: int,
        inbound_id: int,
        client_id: str,
        email: str,
        protocol: str,
    ) -> Config:
        """Create a new VPN config record."""
        config = Config(
            user_id=user_id,
            inbound_id=inbound_id,
            client_id=client_id,
            email=email,
            protocol=protocol,
        )
        self._session.add(config)
        await self._session.flush()
        return config

    async def get_by_id(self, config_id: int) -> Config | None:
        """Return a config by its primary key."""
        stmt = select(Config).where(Config.id == config_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_user_id(self, user_id: int) -> list[Config]:
        """Return all configs for a user."""
        stmt = select(Config).where(Config.user_id == user_id).order_by(Config.created_at.desc())
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_email(self, email: str) -> Config | None:
        """Return a config by its email (client identifier in 3x-ui)."""
        stmt = select(Config).where(Config.email == email)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete(self, config_id: int) -> None:
        """Delete a config by its primary key."""
        config = await self.get_by_id(config_id)
        if config is not None:
            await self._session.delete(config)
            await self._session.flush()
