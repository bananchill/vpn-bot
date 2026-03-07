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
    username: str | None = None,
) -> Admin:
    """Create a new admin record and return it.

    The first admin auto-created during initial setup receives the 'owner' role.
    Subsequent admins added through the UI default to 'moderator'.
    """
    admin = Admin(telegram_id=telegram_id, role=role, username=username)
    session.add(admin)
    await session.flush()
    await session.refresh(admin)
    return admin


async def update_username(
    session: AsyncSession,
    admin_id: int,
    username: str,
) -> None:
    """Update the Telegram username for an admin record.

    Called on every authentication to keep the username in sync with
    the value from initData.
    """
    stmt = select(Admin).where(Admin.id == admin_id)
    result = await session.execute(stmt)
    admin = result.scalar_one_or_none()
    if admin is not None:
        admin.username = username
        await session.flush()


async def update_panel_settings(
    session: AsyncSession,
    admin_id: int,
    *,
    panel_url: str | None = None,
    panel_sub_url: str | None = None,
    panel_username: str | None = None,
    panel_password_encrypted: str | None = None,
    config_bot_token_encrypted: str | None = None,
) -> Admin:
    """Update per-admin panel credentials and config-bot token.

    Only non-None arguments are applied so callers can do partial updates.
    Returns the refreshed Admin instance.

    Raises:
        ValueError: If the admin_id does not exist.
    """
    stmt = select(Admin).where(Admin.id == admin_id)
    result = await session.execute(stmt)
    admin = result.scalar_one_or_none()
    if admin is None:
        raise ValueError(f"Admin with id={admin_id} not found")

    if panel_url is not None:
        admin.panel_url = panel_url
    if panel_sub_url is not None:
        admin.panel_sub_url = panel_sub_url
    if panel_username is not None:
        admin.panel_username = panel_username
    if panel_password_encrypted is not None:
        admin.panel_password_encrypted = panel_password_encrypted
    if config_bot_token_encrypted is not None:
        admin.config_bot_token_encrypted = config_bot_token_encrypted

    await session.flush()
    await session.refresh(admin)
    return admin
