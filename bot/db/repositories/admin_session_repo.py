"""Repository for AdminSession CRUD operations."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from bot.db.models import AdminSession


class AdminSessionRepository:
    """Data-access layer for the admin_sessions table."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_user_id(self, user_id: int) -> AdminSession | None:
        """Return admin session for a given internal user ID."""
        stmt = (
            select(AdminSession)
            .options(joinedload(AdminSession.user))
            .where(AdminSession.user_id == user_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert(
        self,
        user_id: int,
        panel_url: str,
        encrypted_credentials: str,
        session_cookie: str | None = None,
        cookie_expires_at: datetime | None = None,
    ) -> AdminSession:
        """Create or update an admin session for the user."""
        admin_session = await self.get_by_user_id(user_id)
        if admin_session is None:
            admin_session = AdminSession(
                user_id=user_id,
                panel_url=panel_url,
                encrypted_credentials=encrypted_credentials,
                session_cookie=session_cookie,
                cookie_expires_at=cookie_expires_at,
            )
            self._session.add(admin_session)
        else:
            admin_session.panel_url = panel_url
            admin_session.encrypted_credentials = encrypted_credentials
            admin_session.session_cookie = session_cookie
            admin_session.cookie_expires_at = cookie_expires_at
        await self._session.flush()
        return admin_session

    async def update_cookie(
        self,
        user_id: int,
        session_cookie: str,
        cookie_expires_at: datetime | None = None,
    ) -> AdminSession | None:
        """Update only the session cookie for an existing admin session."""
        admin_session = await self.get_by_user_id(user_id)
        if admin_session is None:
            return None
        admin_session.session_cookie = session_cookie
        admin_session.cookie_expires_at = cookie_expires_at
        await self._session.flush()
        return admin_session

    async def delete_by_user_id(self, user_id: int) -> bool:
        """Delete admin session. Returns True if it existed."""
        admin_session = await self.get_by_user_id(user_id)
        if admin_session is None:
            return False
        await self._session.delete(admin_session)
        await self._session.flush()
        return True
