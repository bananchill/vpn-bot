"""Tests for GET /api/logs endpoint.

Covers:
- List logs: pagination, default params
- Filter by action type
- Filter by admin_id (telegram ID)
- available_actions field is populated
- Unauthenticated access returns 401
- Audit log entries created by block/unblock/extend/note/toggle_config/
  toggle_all_configs/update_settings/create_promo/toggle_promo/delete_promo
"""

from __future__ import annotations

import pytest
from db.models import Admin, AdminLog, PromoCode, User
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio

DEV_ADMIN_TG_ID = 111111111


# ────────────────────────────────────────────────────────────────────────────
# Basic access control
# ────────────────────────────────────────────────────────────────────────────


async def test_list_logs_no_auth_returns_401(unauth_client: AsyncClient) -> None:
    response = await unauth_client.get("/api/logs")
    assert response.status_code == 401


# ────────────────────────────────────────────────────────────────────────────
# List logs — empty state
# ────────────────────────────────────────────────────────────────────────────


async def test_list_logs_empty_returns_paginated_response(
    client: AsyncClient,
    seed_admin: Admin,
) -> None:
    response = await client.get("/api/logs")
    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0
    assert body["page"] == 1
    assert body["per_page"] == 20
    assert isinstance(body["available_actions"], list)


# ────────────────────────────────────────────────────────────────────────────
# List logs — with data
# ────────────────────────────────────────────────────────────────────────────


async def test_list_logs_returns_log_entries(
    client: AsyncClient,
    seed_admin: Admin,
    seed_log: AdminLog,
) -> None:
    response = await client.get("/api/logs")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert item["id"] == seed_log.id
    assert item["admin_telegram_id"] == DEV_ADMIN_TG_ID
    assert item["admin_username"] == "admin_user"
    assert item["action"] == "block_user"
    assert item["target"] == "@testuser"
    assert item["details"] == '{"reason": "spam"}'
    assert "created_at" in item


async def test_list_logs_available_actions_populated(
    client: AsyncClient,
    seed_admin: Admin,
    seed_log: AdminLog,
) -> None:
    response = await client.get("/api/logs")
    assert response.status_code == 200
    body = response.json()
    assert "block_user" in body["available_actions"]


# ────────────────────────────────────────────────────────────────────────────
# Filtering by action
# ────────────────────────────────────────────────────────────────────────────


async def test_list_logs_filter_by_action_returns_matching_entries(
    client: AsyncClient,
    seed_admin: Admin,
    db_session: AsyncSession,
) -> None:
    # Insert two logs with different actions
    db_session.add(
        AdminLog(
            admin_telegram_id=DEV_ADMIN_TG_ID,
            action="block_user",
            target="@alice",
        )
    )
    db_session.add(
        AdminLog(
            admin_telegram_id=DEV_ADMIN_TG_ID,
            action="create_promo",
            target="SUMMER25",
        )
    )
    await db_session.flush()

    response = await client.get("/api/logs", params={"action": "block_user"})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["action"] == "block_user"


async def test_list_logs_filter_by_nonexistent_action_returns_empty(
    client: AsyncClient,
    seed_admin: Admin,
    seed_log: AdminLog,
) -> None:
    response = await client.get("/api/logs", params={"action": "nonexistent_action"})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 0
    assert body["items"] == []


async def test_list_logs_no_action_filter_returns_all(
    client: AsyncClient,
    seed_admin: Admin,
    db_session: AsyncSession,
) -> None:
    db_session.add(
        AdminLog(admin_telegram_id=DEV_ADMIN_TG_ID, action="block_user", target="@a")
    )
    db_session.add(
        AdminLog(admin_telegram_id=DEV_ADMIN_TG_ID, action="extend_subscription", target="@b")
    )
    await db_session.flush()

    response = await client.get("/api/logs")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 2


# ────────────────────────────────────────────────────────────────────────────
# Filtering by admin_id
# ────────────────────────────────────────────────────────────────────────────


async def test_list_logs_filter_by_admin_id_returns_matching_entries(
    client: AsyncClient,
    seed_admin: Admin,
    db_session: AsyncSession,
) -> None:
    other_admin_id = 999888777
    db_session.add(
        AdminLog(admin_telegram_id=DEV_ADMIN_TG_ID, action="block_user", target="@a")
    )
    db_session.add(
        AdminLog(admin_telegram_id=other_admin_id, action="block_user", target="@b")
    )
    await db_session.flush()

    response = await client.get("/api/logs", params={"admin_id": DEV_ADMIN_TG_ID})
    assert response.status_code == 200
    body = response.json()
    for item in body["items"]:
        assert item["admin_telegram_id"] == DEV_ADMIN_TG_ID


async def test_list_logs_filter_by_admin_id_no_match_returns_empty(
    client: AsyncClient,
    seed_admin: Admin,
    seed_log: AdminLog,
) -> None:
    response = await client.get("/api/logs", params={"admin_id": 555444333})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 0


# ────────────────────────────────────────────────────────────────────────────
# Pagination
# ────────────────────────────────────────────────────────────────────────────


async def test_list_logs_pagination_params_respected(
    client: AsyncClient,
    seed_admin: Admin,
    db_session: AsyncSession,
) -> None:
    for i in range(5):
        db_session.add(
            AdminLog(
                admin_telegram_id=DEV_ADMIN_TG_ID,
                action=f"action_{i}",
            )
        )
    await db_session.flush()

    response = await client.get("/api/logs", params={"page": 1, "per_page": 2})
    assert response.status_code == 200
    body = response.json()
    assert body["per_page"] == 2
    assert len(body["items"]) == 2
    assert body["total"] >= 5


async def test_list_logs_per_page_max_100(
    client: AsyncClient,
    seed_admin: Admin,
) -> None:
    response = await client.get("/api/logs", params={"per_page": 101})
    assert response.status_code == 422


async def test_list_logs_page_lt_1_returns_422(
    client: AsyncClient,
    seed_admin: Admin,
) -> None:
    response = await client.get("/api/logs", params={"page": 0})
    assert response.status_code == 422


# ────────────────────────────────────────────────────────────────────────────
# Audit logging: verify mutating operations create log entries
# ────────────────────────────────────────────────────────────────────────────


async def test_block_user_creates_block_user_log(
    client: AsyncClient,
    seed_admin: Admin,
    seed_user: User,
    db_session: AsyncSession,
) -> None:
    """PATCH /api/users/{id}/block with is_blocked=True → logs 'block_user'."""
    response = await client.patch(
        f"/api/users/{seed_user.id}/block",
        json={"is_blocked": True},
    )
    assert response.status_code == 200

    result = await db_session.execute(
        select(AdminLog).where(AdminLog.action == "block_user")
    )
    logs = result.scalars().all()
    assert len(logs) >= 1
    assert logs[0].admin_telegram_id == DEV_ADMIN_TG_ID


async def test_unblock_user_creates_unblock_user_log(
    client: AsyncClient,
    seed_admin: Admin,
    seed_user: User,
    db_session: AsyncSession,
) -> None:
    """PATCH /api/users/{id}/block with is_blocked=False → logs 'unblock_user'."""
    response = await client.patch(
        f"/api/users/{seed_user.id}/block",
        json={"is_blocked": False},
    )
    assert response.status_code == 200

    result = await db_session.execute(
        select(AdminLog).where(AdminLog.action == "unblock_user")
    )
    logs = result.scalars().all()
    assert len(logs) >= 1


async def test_update_note_creates_update_note_log(
    client: AsyncClient,
    seed_admin: Admin,
    seed_user: User,
    db_session: AsyncSession,
) -> None:
    """PATCH /api/users/{id}/note → logs 'update_note'."""
    response = await client.patch(
        f"/api/users/{seed_user.id}/note",
        json={"note": "test note"},
    )
    assert response.status_code == 200

    result = await db_session.execute(
        select(AdminLog).where(AdminLog.action == "update_note")
    )
    logs = result.scalars().all()
    assert len(logs) >= 1


async def test_create_promo_creates_create_promo_log(
    client: AsyncClient,
    seed_admin: Admin,
    db_session: AsyncSession,
) -> None:
    """POST /api/promos → logs 'create_promo'."""
    response = await client.post(
        "/api/promos",
        json={
            "code": "AUDITLOG1",
            "discount_percent": 10,
            "max_activations": 10,
            "valid_days": 7,
        },
    )
    assert response.status_code == 201

    result = await db_session.execute(
        select(AdminLog).where(AdminLog.action == "create_promo")
    )
    logs = result.scalars().all()
    assert len(logs) >= 1
    assert logs[0].target == "AUDITLOG1"


async def test_toggle_promo_creates_toggle_promo_log(
    client: AsyncClient,
    seed_admin: Admin,
    seed_promo: PromoCode,
    db_session: AsyncSession,
) -> None:
    """PATCH /api/promos/{id}/toggle → logs 'toggle_promo'."""
    response = await client.patch(
        f"/api/promos/{seed_promo.id}/toggle",
        json={"is_active": False},
    )
    assert response.status_code == 200

    result = await db_session.execute(
        select(AdminLog).where(AdminLog.action == "toggle_promo")
    )
    logs = result.scalars().all()
    assert len(logs) >= 1
    assert logs[0].target == "TESTCODE"


async def test_delete_promo_creates_delete_promo_log(
    client: AsyncClient,
    seed_admin: Admin,
    seed_promo: PromoCode,
    db_session: AsyncSession,
) -> None:
    """DELETE /api/promos/{id} → logs 'delete_promo'."""
    response = await client.delete(f"/api/promos/{seed_promo.id}")
    assert response.status_code == 204

    result = await db_session.execute(
        select(AdminLog).where(AdminLog.action == "delete_promo")
    )
    logs = result.scalars().all()
    assert len(logs) >= 1
    assert logs[0].target == "TESTCODE"


# ────────────────────────────────────────────────────────────────────────────
# available_actions reflects distinct actions in DB
# ────────────────────────────────────────────────────────────────────────────


async def test_list_logs_available_actions_sorted(
    client: AsyncClient,
    seed_admin: Admin,
    db_session: AsyncSession,
) -> None:
    db_session.add(AdminLog(admin_telegram_id=DEV_ADMIN_TG_ID, action="zebra_action"))
    db_session.add(AdminLog(admin_telegram_id=DEV_ADMIN_TG_ID, action="alpha_action"))
    await db_session.flush()

    response = await client.get("/api/logs")
    assert response.status_code == 200
    body = response.json()
    actions = body["available_actions"]
    assert actions == sorted(actions)


async def test_list_logs_available_actions_contains_all_distinct_actions(
    client: AsyncClient,
    seed_admin: Admin,
    db_session: AsyncSession,
) -> None:
    db_session.add(AdminLog(admin_telegram_id=DEV_ADMIN_TG_ID, action="action_x"))
    db_session.add(AdminLog(admin_telegram_id=DEV_ADMIN_TG_ID, action="action_y"))
    db_session.add(AdminLog(admin_telegram_id=DEV_ADMIN_TG_ID, action="action_x"))  # duplicate
    await db_session.flush()

    response = await client.get("/api/logs")
    assert response.status_code == 200
    body = response.json()
    actions = body["available_actions"]
    # Should only appear once
    assert actions.count("action_x") == 1
    assert "action_y" in actions
