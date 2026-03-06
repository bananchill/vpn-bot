"""Admin API test fixtures.

Sets up an in-memory SQLite test database and an HTTPX AsyncClient
pointed at the admin FastAPI app.  All tables are created fresh for
each test session and rolled back between tests using nested transactions.

Auth is handled by enabling DEV_MODE so that X-Telegram-Init-Data
validation is skipped and a deterministic fake admin ID is used.
"""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

# -- Environment variables must be set BEFORE any admin package is imported --
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("ADMIN_BOT_TOKEN", "123456789:AAFakeTokenForTesting")
os.environ.setdefault("FERNET_KEY", "uD1gNjS5zNNNWL0fthTbmqp_0MO--Wpc3K-be1seUCY=")
os.environ.setdefault("WEBAPP_URL", "http://localhost:5173")
os.environ["ADMIN_DEV_MODE"] = "true"
os.environ["ADMIN_DEV_TELEGRAM_ID"] = "111111111"

import contextlib
import sys
import types
from unittest.mock import AsyncMock

# Absolute path to the admin-mini-app backend directory
BACKEND_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "admin-mini-app", "backend")
)

# Project root path (where the real `bot` package lives)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Step 1: Ensure the project root is already in sys.path so that the real
# `bot` package is importable when the bot test suite runs alongside admin tests.
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# Step 2: Import (and thus cache) the real project-root `bot` package BEFORE
# adding the admin backend path, so Python will always find the real `bot`
# package first when other test modules import it.
# We do this only if `bot` is not yet in sys.modules.
if "bot" not in sys.modules:
    with contextlib.suppress(Exception):
        import bot as _real_bot_module  # noqa: F401

# Step 3: Now add the admin-mini-app backend to sys.path so admin modules
# (api, db, schemas, config) are importable.  We append rather than insert(0)
# so the project-root `bot` package (already cached) takes precedence.
if BACKEND_PATH not in sys.path:
    sys.path.append(BACKEND_PATH)

# Step 4: Stub out bot.bot (the admin-mini-app's internal bot module) so that
# `from bot.bot import start_polling, stop_polling` in main.py doesn't try to
# instantiate a real Telegram Bot object.
_bot_bot_stub = types.ModuleType("bot.bot")
_bot_bot_stub.start_polling = AsyncMock()  # type: ignore[attr-defined]
_bot_bot_stub.stop_polling = AsyncMock()  # type: ignore[attr-defined]
sys.modules["bot.bot"] = _bot_bot_stub

# Now import from admin backend — these resolve through the appended BACKEND_PATH.
# We use the full import path to avoid ambiguity with any top-level `db` package.
from db.engine import Base  # noqa: E402  # admin-mini-app's db.engine
from db.models import Admin, AdminLog, PromoCode, PromoUsage, User  # noqa: E402

# SQLite engine for tests (shared in-memory instance)
_TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

_engine = create_async_engine(
    _TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
)

_session_factory = async_sessionmaker(
    _engine, class_=AsyncSession, expire_on_commit=False
)

# ────────────────────────────────────────────────────────────────────────────
# Session-scoped fixtures
# ────────────────────────────────────────────────────────────────────────────


@pytest.fixture(scope="session", autouse=True)
async def create_tables() -> AsyncGenerator[None, None]:
    """Create all tables once for the test session."""
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ────────────────────────────────────────────────────────────────────────────
# Per-test database session with rollback
# ────────────────────────────────────────────────────────────────────────────


@pytest.fixture()
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a clean database session that rolls back after each test."""
    async with _engine.connect() as conn, conn.begin() as outer_tx:
        # Use a nested SAVEPOINT to allow rollback without breaking outer tx
        session = AsyncSession(bind=conn, expire_on_commit=False)
        try:
            yield session
        finally:
            await session.close()
        await outer_tx.rollback()


# ────────────────────────────────────────────────────────────────────────────
# FastAPI app + HTTPX client
# ────────────────────────────────────────────────────────────────────────────


@pytest.fixture()
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Return an AsyncClient backed by the admin FastAPI app (authenticated).

    The app's `get_db` dependency is overridden so all requests share the
    test database session and changes can be inspected mid-test.
    DEV_MODE=true means the app uses DEV_ADMIN_ID without header validation.
    """
    # Import here to avoid circular import at module level
    from api.deps import get_db
    from main import app

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture()
async def unauth_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Return a client where get_current_admin raises 401 (simulates no valid auth).

    Overrides get_current_admin directly so we can test unauthenticated behavior
    regardless of DEV_MODE.
    """
    from api.deps import get_current_admin, get_db
    from fastapi import HTTPException
    from main import app

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    async def _no_auth() -> None:
        raise HTTPException(status_code=401, detail="Missing initData")

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_admin] = _no_auth

    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# ────────────────────────────────────────────────────────────────────────────
# Seed helpers
# ────────────────────────────────────────────────────────────────────────────

DEV_ADMIN_TG_ID = 111111111  # matches ADMIN_DEV_TELEGRAM_ID env var


@pytest.fixture()
async def seed_admin(db_session: AsyncSession) -> Admin:
    """Insert the dev admin into the database so get_current_admin succeeds."""
    admin = Admin(telegram_id=DEV_ADMIN_TG_ID, role="owner")
    db_session.add(admin)
    await db_session.flush()
    await db_session.refresh(admin)
    return admin


@pytest.fixture()
async def seed_user(db_session: AsyncSession) -> User:
    """Insert a basic (unpaid) user and return the ORM object."""
    user = User(
        telegram_id=987654321,
        username="testuser",
        first_name="Test",
        is_paid=False,
        is_blocked=False,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest.fixture()
async def seed_promo(db_session: AsyncSession) -> PromoCode:
    """Insert a valid active promo code and return the ORM object."""
    promo = PromoCode(
        code="TESTCODE",
        discount_percent=10,
        max_activations=100,
        current_activations=0,
        valid_until=datetime.now(UTC) + timedelta(days=30),
        is_active=True,
    )
    db_session.add(promo)
    await db_session.flush()
    await db_session.refresh(promo)
    return promo


@pytest.fixture()
async def seed_inactive_promo(db_session: AsyncSession) -> PromoCode:
    """Insert an inactive promo code and return the ORM object."""
    promo = PromoCode(
        code="INACTIVE",
        discount_percent=5,
        max_activations=50,
        current_activations=0,
        valid_until=datetime.now(UTC) + timedelta(days=10),
        is_active=False,
    )
    db_session.add(promo)
    await db_session.flush()
    await db_session.refresh(promo)
    return promo


@pytest.fixture()
async def seed_expired_promo(db_session: AsyncSession) -> PromoCode:
    """Insert an expired (past valid_until) active promo and return the ORM object."""
    promo = PromoCode(
        code="EXPIRED",
        discount_percent=15,
        max_activations=10,
        current_activations=3,
        valid_until=datetime.now(UTC) - timedelta(days=1),
        is_active=True,
    )
    db_session.add(promo)
    await db_session.flush()
    await db_session.refresh(promo)
    return promo


@pytest.fixture()
async def seed_promo_usage(
    db_session: AsyncSession,
    seed_promo: PromoCode,
    seed_user: User,
) -> PromoUsage:
    """Create a PromoUsage linking seed_promo to seed_user."""
    usage = PromoUsage(
        promo_id=seed_promo.id,
        user_id=seed_user.id,
        used_at=datetime.now(UTC),
    )
    db_session.add(usage)
    await db_session.flush()
    await db_session.refresh(usage)
    return usage


@pytest.fixture()
async def seed_log(db_session: AsyncSession) -> AdminLog:
    """Insert a single audit log entry and return the ORM object."""
    log = AdminLog(
        admin_telegram_id=DEV_ADMIN_TG_ID,
        admin_username="admin_user",
        action="block_user",
        target="@testuser",
        details='{"reason": "spam"}',
    )
    db_session.add(log)
    await db_session.flush()
    await db_session.refresh(log)
    return log
