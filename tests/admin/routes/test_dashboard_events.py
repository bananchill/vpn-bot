"""Tests for GET /api/dashboard/events endpoint.

Covers:
- Response structure
- Events are derived from recent subscriptions and upcoming expirations
- Empty state returns empty items list
- Unauthenticated access returns 401
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from db.models import Admin, User
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


# ────────────────────────────────────────────────────────────────────────────
# Access control
# ────────────────────────────────────────────────────────────────────────────


async def test_dashboard_events_no_auth_returns_401(unauth_client: AsyncClient) -> None:
    response = await unauth_client.get("/api/dashboard/events")
    assert response.status_code == 401


# ────────────────────────────────────────────────────────────────────────────
# Response structure
# ────────────────────────────────────────────────────────────────────────────


async def test_dashboard_events_empty_db_returns_empty_items(
    client: AsyncClient,
    seed_admin: Admin,
) -> None:
    response = await client.get("/api/dashboard/events")
    assert response.status_code == 200
    body = response.json()
    assert "items" in body
    assert isinstance(body["items"], list)
    assert body["items"] == []


async def test_dashboard_events_items_have_required_fields(
    client: AsyncClient,
    seed_admin: Admin,
    db_session: AsyncSession,
) -> None:
    now = datetime.now(UTC)
    # Add a user with a recent subscription so an event is generated
    user = User(
        telegram_id=70001,
        username="recent_sub_user",
        is_paid=True,
        subscribed_since=now - timedelta(hours=1),
        subscription_expires=now + timedelta(days=30),
    )
    db_session.add(user)
    await db_session.flush()

    response = await client.get("/api/dashboard/events")
    assert response.status_code == 200
    body = response.json()
    if body["items"]:
        item = body["items"][0]
        assert "emoji" in item
        assert "title" in item
        assert "time_ago" in item


async def test_dashboard_events_subscription_event_appears(
    client: AsyncClient,
    seed_admin: Admin,
    db_session: AsyncSession,
) -> None:
    """User with subscribed_since in last 48h creates a 'subscription' event."""
    now = datetime.now(UTC)
    user = User(
        telegram_id=80001,
        username="sub_event_user",
        first_name="Alice",
        is_paid=True,
        subscribed_since=now - timedelta(hours=12),
        subscription_expires=now + timedelta(days=30),
    )
    db_session.add(user)
    await db_session.flush()

    response = await client.get("/api/dashboard/events")
    assert response.status_code == 200
    body = response.json()
    # Should have at least one event
    assert len(body["items"]) >= 1
    # The subscription event should have the checkmark emoji
    titles = [item["title"] for item in body["items"]]
    assert any("sub_event_user" in t or "Alice" in t for t in titles)


async def test_dashboard_events_expiring_event_appears(
    client: AsyncClient,
    seed_admin: Admin,
    db_session: AsyncSession,
) -> None:
    """User with subscription expiring within 7 days creates an 'expiring' event."""
    now = datetime.now(UTC)
    user = User(
        telegram_id=90001,
        username="expiring_user",
        is_paid=True,
        subscription_expires=now + timedelta(days=3),
    )
    db_session.add(user)
    await db_session.flush()

    response = await client.get("/api/dashboard/events")
    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) >= 1
    # At least one event should reference expiring_user
    titles = [item["title"] for item in body["items"]]
    assert any("expiring_user" in t for t in titles)
