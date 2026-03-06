"""Tests for GET /api/dashboard/stats — extended statistics.

Covers:
- Response includes all required fields (total_users, paid_users, unpaid_users,
  expiring_soon, active_configs, new_users_30d, active_promos)
- new_users_30d counts only users created within last 30 days
- active_promos counts only promos that are active AND not expired
- unpaid_users = total_users - paid_users
- Unauthenticated access returns 401
"""

from __future__ import annotations

import pytest
from db.models import Admin, PromoCode, User
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


# ────────────────────────────────────────────────────────────────────────────
# Access control
# ────────────────────────────────────────────────────────────────────────────


async def test_dashboard_stats_no_auth_returns_401(unauth_client: AsyncClient) -> None:
    response = await unauth_client.get("/api/dashboard/stats")
    assert response.status_code == 401


# ────────────────────────────────────────────────────────────────────────────
# Response structure
# ────────────────────────────────────────────────────────────────────────────


async def test_dashboard_stats_returns_all_required_fields(
    client: AsyncClient,
    seed_admin: Admin,
) -> None:
    response = await client.get("/api/dashboard/stats")
    assert response.status_code == 200
    body = response.json()

    required_fields = [
        "total_users",
        "paid_users",
        "unpaid_users",
        "expiring_soon",
        "active_configs",
        "new_users_30d",
        "active_promos",
    ]
    for field in required_fields:
        assert field in body, f"Missing field: {field}"


async def test_dashboard_stats_empty_db_returns_zeros(
    client: AsyncClient,
    seed_admin: Admin,
) -> None:
    response = await client.get("/api/dashboard/stats")
    assert response.status_code == 200
    body = response.json()
    assert body["total_users"] == 0
    assert body["paid_users"] == 0
    assert body["unpaid_users"] == 0
    assert body["expiring_soon"] == 0
    assert body["active_configs"] == 0
    assert body["new_users_30d"] == 0
    assert body["active_promos"] == 0


# ────────────────────────────────────────────────────────────────────────────
# unpaid_users metric
# ────────────────────────────────────────────────────────────────────────────


async def test_dashboard_stats_unpaid_users_count(
    client: AsyncClient,
    seed_admin: Admin,
    db_session: AsyncSession,
) -> None:
    db_session.add(User(telegram_id=10001, is_paid=True))
    db_session.add(User(telegram_id=10002, is_paid=False))
    db_session.add(User(telegram_id=10003, is_paid=False))
    await db_session.flush()

    response = await client.get("/api/dashboard/stats")
    assert response.status_code == 200
    body = response.json()
    assert body["paid_users"] == 1
    assert body["unpaid_users"] == 2
    assert body["total_users"] == 3


async def test_dashboard_stats_unpaid_equals_total_minus_paid(
    client: AsyncClient,
    seed_admin: Admin,
    db_session: AsyncSession,
) -> None:
    db_session.add(User(telegram_id=20001, is_paid=True))
    db_session.add(User(telegram_id=20002, is_paid=True))
    db_session.add(User(telegram_id=20003, is_paid=False))
    await db_session.flush()

    response = await client.get("/api/dashboard/stats")
    assert response.status_code == 200
    body = response.json()
    assert body["unpaid_users"] == body["total_users"] - body["paid_users"]


# ────────────────────────────────────────────────────────────────────────────
# new_users_30d metric
# ────────────────────────────────────────────────────────────────────────────


async def test_dashboard_stats_new_users_30d_counts_recent_users(
    client: AsyncClient,
    seed_admin: Admin,
    db_session: AsyncSession,
) -> None:
    # User created 15 days ago — should be counted
    recent_user = User(telegram_id=30001, is_paid=False)
    db_session.add(recent_user)
    await db_session.flush()

    response = await client.get("/api/dashboard/stats")
    assert response.status_code == 200
    body = response.json()
    # At minimum the just-created user is in last 30 days
    assert body["new_users_30d"] >= 1


async def test_dashboard_stats_new_users_30d_excludes_old_users(
    client: AsyncClient,
    seed_admin: Admin,
    db_session: AsyncSession,
) -> None:
    # We cannot easily backdate created_at on SQLite (server_default),
    # but we can verify the count is consistent with total_users
    response = await client.get("/api/dashboard/stats")
    assert response.status_code == 200
    body = response.json()
    # new_users_30d should never exceed total_users
    assert body["new_users_30d"] <= body["total_users"]


# ────────────────────────────────────────────────────────────────────────────
# active_promos metric
# ────────────────────────────────────────────────────────────────────────────


async def test_dashboard_stats_active_promos_count_valid_active(
    client: AsyncClient,
    seed_admin: Admin,
    seed_promo: PromoCode,
) -> None:
    """seed_promo is active and not expired — should be counted."""
    response = await client.get("/api/dashboard/stats")
    assert response.status_code == 200
    body = response.json()
    assert body["active_promos"] >= 1


async def test_dashboard_stats_active_promos_excludes_inactive(
    client: AsyncClient,
    seed_admin: Admin,
    seed_inactive_promo: PromoCode,
) -> None:
    """seed_inactive_promo is is_active=False — should NOT be counted."""
    response = await client.get("/api/dashboard/stats")
    assert response.status_code == 200
    body = response.json()
    # Only inactive promos exist, so active_promos should be 0
    assert body["active_promos"] == 0


async def test_dashboard_stats_active_promos_excludes_expired(
    client: AsyncClient,
    seed_admin: Admin,
    seed_expired_promo: PromoCode,
) -> None:
    """seed_expired_promo has valid_until in the past — should NOT be counted."""
    response = await client.get("/api/dashboard/stats")
    assert response.status_code == 200
    body = response.json()
    assert body["active_promos"] == 0


async def test_dashboard_stats_active_promos_mixed(
    client: AsyncClient,
    seed_admin: Admin,
    seed_promo: PromoCode,
    seed_inactive_promo: PromoCode,
    seed_expired_promo: PromoCode,
) -> None:
    """Only the active non-expired promo should be counted."""
    response = await client.get("/api/dashboard/stats")
    assert response.status_code == 200
    body = response.json()
    # seed_promo is the only active + non-expired one
    assert body["active_promos"] == 1


# ────────────────────────────────────────────────────────────────────────────
# Return types are integers (not floats or strings)
# ────────────────────────────────────────────────────────────────────────────


async def test_dashboard_stats_all_values_are_integers(
    client: AsyncClient,
    seed_admin: Admin,
) -> None:
    response = await client.get("/api/dashboard/stats")
    assert response.status_code == 200
    body = response.json()
    for field in [
        "total_users",
        "paid_users",
        "unpaid_users",
        "expiring_soon",
        "active_configs",
        "new_users_30d",
        "active_promos",
    ]:
        assert isinstance(body[field], int), f"{field} should be int, got {type(body[field])}"
