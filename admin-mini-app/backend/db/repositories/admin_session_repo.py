"""Repository for writing to the bot's ``admin_sessions`` table.

The admin-mini-app uses this repository when an admin saves panel
credentials via ``PUT /api/settings``.  It performs an upsert so the bot
can read the credentials on its next panel request without any HTTP API
between the two services.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import AdminSession


async def upsert(
    session: AsyncSession,
    *,
    user_id: int,
    panel_url: str,
    encrypted_credentials: str,
) -> AdminSession:
    """Create or update an admin_sessions row for the given user.

    The ``session_cookie`` and ``cookie_expires_at`` fields are cleared on
    every upsert because the stored credentials have changed and the
    cached cookie is no longer valid.

    Args:
        session: Active database session (within a transaction).
        user_id: Internal ``users.id`` (NOT telegram_id).
        panel_url: Full URL of the 3x-ui panel.
        encrypted_credentials: Fernet-encrypted JSON ``{"username": ..., "password": ...}``.

    Returns:
        The created or updated AdminSession instance.
    """
    stmt = select(AdminSession).where(AdminSession.user_id == user_id)
    result = await session.execute(stmt)
    admin_session = result.scalar_one_or_none()

    if admin_session is None:
        admin_session = AdminSession(
            user_id=user_id,
            panel_url=panel_url,
            encrypted_credentials=encrypted_credentials,
            session_cookie=None,
            cookie_expires_at=None,
        )
        session.add(admin_session)
    else:
        admin_session.panel_url = panel_url
        admin_session.encrypted_credentials = encrypted_credentials
        # Invalidate cached session cookie since credentials changed
        admin_session.session_cookie = None
        admin_session.cookie_expires_at = None

    await session.flush()
    return admin_session
