"""Repository for User CRUD operations."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import User


class UserRepository:
    """Data-access layer for the users table."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        """Return a user by their Telegram ID, or None."""
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create(self, telegram_id: int, username: str | None = None) -> User:
        """Return existing user or create a new one."""
        user = await self.get_by_telegram_id(telegram_id)
        if user is None:
            user = User(telegram_id=telegram_id, username=username)
            self._session.add(user)
            await self._session.flush()
        return user

    async def set_admin(self, telegram_id: int, is_admin: bool = True) -> User:
        """Mark a user as admin (or revoke admin)."""
        user = await self.get_by_telegram_id(telegram_id)
        if user is None:
            msg = f"User with telegram_id={telegram_id} not found"
            raise ValueError(msg)
        user.is_admin = is_admin
        await self._session.flush()
        return user

    async def list_admins(self) -> list[User]:
        """Return all admin users."""
        stmt = select(User).where(User.is_admin.is_(True))
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
