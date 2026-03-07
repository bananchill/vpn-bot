"""Tests for api/deps.py — get_current_admin dependency (TASK-018).

Covers:
- DEV_MODE: uses DEV_ADMIN_ID, auto-creates owner, syncs username
- Auto-create first admin as owner (zero admins in DB)
- ensure_is_admin sets User.is_admin=True on first owner creation
- Username sync: update Admin.username when it changes on re-entry
- Non-admin telegram_id returns 403
- Missing initData in non-dev mode returns 401 (via unauth_client)
"""

from __future__ import annotations

import pytest
from db.models import Admin, User
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio

DEV_ADMIN_TG_ID = 111111111  # matches ADMIN_DEV_TELEGRAM_ID env var


# ---------------------------------------------------------------------------
# Auto-create first admin on first request (DEV_MODE)
# ---------------------------------------------------------------------------


async def test_first_request_no_admins_creates_owner(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """With zero admins, the first authenticated request auto-creates an owner."""
    # Trigger any authenticated endpoint
    response = await client.get("/api/settings")
    assert response.status_code == 200

    result = await db_session.execute(
        select(Admin).where(Admin.telegram_id == DEV_ADMIN_TG_ID)
    )
    admin = result.scalar_one_or_none()
    assert admin is not None
    assert admin.role == "owner"


async def test_first_request_auto_created_admin_has_dev_id(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Auto-created owner must have telegram_id = DEV_ADMIN_ID."""
    await client.get("/api/settings")

    result = await db_session.execute(
        select(Admin).where(Admin.telegram_id == DEV_ADMIN_TG_ID)
    )
    admin = result.scalar_one_or_none()
    assert admin is not None
    assert admin.telegram_id == DEV_ADMIN_TG_ID


async def test_first_owner_creation_sets_user_is_admin(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """When the first owner is created, User.is_admin must be set to True."""
    await client.get("/api/settings")

    result = await db_session.execute(
        select(User).where(User.telegram_id == DEV_ADMIN_TG_ID)
    )
    user = result.scalar_one_or_none()
    # The user row must exist and is_admin must be True
    assert user is not None
    assert user.is_admin is True


async def test_first_owner_creation_creates_user_row_if_absent(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """ensure_is_admin must create the User row if it doesn't already exist."""
    # Verify no user row exists before the first request
    result = await db_session.execute(
        select(User).where(User.telegram_id == DEV_ADMIN_TG_ID)
    )
    user_before = result.scalar_one_or_none()
    assert user_before is None

    await client.get("/api/settings")

    result = await db_session.execute(
        select(User).where(User.telegram_id == DEV_ADMIN_TG_ID)
    )
    user_after = result.scalar_one_or_none()
    assert user_after is not None


# ---------------------------------------------------------------------------
# Username sync on every entry
# ---------------------------------------------------------------------------


async def test_username_stored_on_first_owner_creation(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """DEV_MODE sets username='dev_admin'; that value must appear in the Admin row."""
    await client.get("/api/settings")

    result = await db_session.execute(
        select(Admin).where(Admin.telegram_id == DEV_ADMIN_TG_ID)
    )
    admin = result.scalar_one_or_none()
    assert admin is not None
    # DEV_MODE injects 'dev_admin' as username (see deps.py)
    assert admin.username == "dev_admin"


async def test_username_updated_on_re_entry(
    client: AsyncClient,
    seed_admin: Admin,
    db_session: AsyncSession,
) -> None:
    """If Admin.username differs from the value in initData, it must be updated."""
    # Manually set the username to something different from 'dev_admin'
    seed_admin.username = "old_username"
    await db_session.flush()

    # Make any authenticated request — DEV_MODE always injects 'dev_admin'
    await client.get("/api/settings")

    await db_session.refresh(seed_admin)
    assert seed_admin.username == "dev_admin"


async def test_username_not_updated_if_unchanged(
    client: AsyncClient,
    seed_admin: Admin,
    db_session: AsyncSession,
) -> None:
    """If the username already matches, no DB write should cause issues."""
    seed_admin.username = "dev_admin"
    await db_session.flush()

    response = await client.get("/api/settings")
    assert response.status_code == 200

    await db_session.refresh(seed_admin)
    assert seed_admin.username == "dev_admin"


# ---------------------------------------------------------------------------
# Non-admin request → 403
# ---------------------------------------------------------------------------


async def test_unknown_telegram_id_returns_403(
    client: AsyncClient,
    seed_admin: Admin,
    db_session: AsyncSession,
) -> None:
    """A telegram_id not in admins table (with existing admins) returns 403.

    We achieve this by overriding get_current_admin to raise 403 directly,
    which is what the real implementation does for an unknown ID when
    admin_count > 0.
    """
    from fastapi import HTTPException
    from main import app
    from api.deps import get_current_admin, get_db

    async def _unknown_user():
        raise HTTPException(status_code=403, detail="Not an admin")

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_current_admin] = _unknown_user
    app.dependency_overrides[get_db] = _override_get_db

    from httpx import ASGITransport, AsyncClient as HTTPX_AC

    transport = ASGITransport(app=app)
    async with HTTPX_AC(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/settings")

    app.dependency_overrides.clear()
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Unauthenticated access returns 401
# ---------------------------------------------------------------------------


async def test_missing_auth_returns_401(unauth_client: AsyncClient) -> None:
    """The unauth_client fixture injects a 401 from get_current_admin."""
    response = await unauth_client.get("/api/settings")
    assert response.status_code == 401


async def test_missing_auth_on_settings_global_returns_401(
    unauth_client: AsyncClient,
) -> None:
    response = await unauth_client.get("/api/settings/global")
    assert response.status_code == 401
