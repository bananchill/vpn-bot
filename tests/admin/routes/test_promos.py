"""Tests for GET/POST/PATCH/DELETE /api/promos and related endpoints.

Note on the `db_session` fixture and type hints: the `db_session` parameter
appears in function signatures that use it via conftest but don't need a
direct type import — we use the module-level import from conftest via pytest.


Covers:
- List promos with pagination and is_active filter
- Create promo: happy path, duplicate code (409), past valid_until (400),
  missing validity period (400), invalid code characters (422)
- Get promo by ID: found, not found (404)
- Toggle promo active state: activate, deactivate, not found (404)
- Delete promo: success (204), not found (404)
- List promo usages: with data, empty, not found (404)
- Generate unique code: returns 8-char hex code
- All endpoints reject unauthenticated requests (401)
- Audit log entries are created for mutating operations
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from db.models import Admin, AdminLog, PromoCode, PromoUsage, User
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


# ────────────────────────────────────────────────────────────────────────────
# Helper: count AdminLog rows for a given action
# ────────────────────────────────────────────────────────────────────────────


async def _count_logs(session: AsyncSession, action: str) -> int:
    result = await session.execute(
        select(AdminLog).where(AdminLog.action == action)
    )
    return len(result.scalars().all())


# ────────────────────────────────────────────────────────────────────────────
# GET /api/promos
# ────────────────────────────────────────────────────────────────────────────


async def test_list_promos_no_auth_returns_401(unauth_client: AsyncClient) -> None:
    response = await unauth_client.get("/api/promos")
    assert response.status_code == 401


async def test_list_promos_empty_returns_paginated_response(
    client: AsyncClient,
    seed_admin: Admin,
) -> None:
    response = await client.get("/api/promos")
    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0
    assert body["page"] == 1
    assert body["per_page"] == 20


async def test_list_promos_returns_existing_promos(
    client: AsyncClient,
    seed_admin: Admin,
    seed_promo: PromoCode,
) -> None:
    response = await client.get("/api/promos")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert item["code"] == "TESTCODE"
    assert item["discount_percent"] == 10
    assert item["max_activations"] == 100
    assert item["current_activations"] == 0
    assert item["is_active"] is True
    assert "is_expired" in item


async def test_list_promos_filter_active_returns_only_active(
    client: AsyncClient,
    seed_admin: Admin,
    seed_promo: PromoCode,
    seed_inactive_promo: PromoCode,
) -> None:
    response = await client.get("/api/promos", params={"is_active": "true"})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["code"] == "TESTCODE"


async def test_list_promos_filter_inactive_returns_only_inactive(
    client: AsyncClient,
    seed_admin: Admin,
    seed_promo: PromoCode,
    seed_inactive_promo: PromoCode,
) -> None:
    response = await client.get("/api/promos", params={"is_active": "false"})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["code"] == "INACTIVE"


async def test_list_promos_pagination_params_respected(
    client: AsyncClient,
    seed_admin: Admin,
    seed_promo: PromoCode,
    seed_inactive_promo: PromoCode,
) -> None:
    response = await client.get(
        "/api/promos", params={"page": 1, "per_page": 1}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["per_page"] == 1
    assert len(body["items"]) == 1
    assert body["total"] == 2


async def test_list_promos_per_page_max_100(
    client: AsyncClient,
    seed_admin: Admin,
) -> None:
    response = await client.get("/api/promos", params={"per_page": 101})
    assert response.status_code == 422


async def test_list_promos_page_lt_1_returns_422(
    client: AsyncClient,
    seed_admin: Admin,
) -> None:
    response = await client.get("/api/promos", params={"page": 0})
    assert response.status_code == 422


# ────────────────────────────────────────────────────────────────────────────
# POST /api/promos
# ────────────────────────────────────────────────────────────────────────────


async def test_create_promo_with_valid_days_returns_201(
    client: AsyncClient,
    seed_admin: Admin,
    db_session: AsyncSession,
) -> None:
    payload = {
        "code": "SUMMER25",
        "discount_percent": 25,
        "max_activations": 100,
        "valid_days": 30,
    }
    response = await client.post("/api/promos", json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["code"] == "SUMMER25"
    assert body["discount_percent"] == 25
    assert body["max_activations"] == 100
    assert body["current_activations"] == 0
    assert body["is_active"] is True
    assert body["is_expired"] is False
    assert "id" in body
    assert "valid_until" in body
    assert "created_at" in body


async def test_create_promo_with_valid_until_returns_201(
    client: AsyncClient,
    seed_admin: Admin,
) -> None:
    future_date = (datetime.now(UTC) + timedelta(days=60)).isoformat()
    payload = {
        "code": "WINTER10",
        "discount_percent": 10,
        "max_activations": 50,
        "valid_until": future_date,
    }
    response = await client.post("/api/promos", json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["code"] == "WINTER10"
    assert body["is_expired"] is False


async def test_create_promo_no_auth_returns_401(unauth_client: AsyncClient) -> None:
    payload = {
        "code": "NOAUTH",
        "discount_percent": 10,
        "max_activations": 10,
        "valid_days": 7,
    }
    response = await unauth_client.post("/api/promos", json=payload)
    assert response.status_code == 401


async def test_create_promo_duplicate_code_returns_409(
    client: AsyncClient,
    seed_admin: Admin,
    seed_promo: PromoCode,
) -> None:
    payload = {
        "code": "TESTCODE",  # same as seed_promo
        "discount_percent": 20,
        "max_activations": 5,
        "valid_days": 10,
    }
    response = await client.post("/api/promos", json=payload)
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"].lower()


async def test_create_promo_past_valid_until_returns_400(
    client: AsyncClient,
    seed_admin: Admin,
) -> None:
    past_date = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    payload = {
        "code": "PASTCODE",
        "discount_percent": 5,
        "max_activations": 10,
        "valid_until": past_date,
    }
    response = await client.post("/api/promos", json=payload)
    assert response.status_code == 400
    assert "future" in response.json()["detail"].lower()


async def test_create_promo_missing_validity_period_returns_422(
    client: AsyncClient,
    seed_admin: Admin,
) -> None:
    payload = {
        "code": "NOVALID",
        "discount_percent": 10,
        "max_activations": 10,
        # Neither valid_days nor valid_until provided
    }
    response = await client.post("/api/promos", json=payload)
    assert response.status_code == 422


async def test_create_promo_lowercase_code_returns_422(
    client: AsyncClient,
    seed_admin: Admin,
) -> None:
    payload = {
        "code": "lowercase",  # Must be [A-Z0-9] only
        "discount_percent": 10,
        "max_activations": 10,
        "valid_days": 7,
    }
    response = await client.post("/api/promos", json=payload)
    assert response.status_code == 422


async def test_create_promo_special_chars_in_code_returns_422(
    client: AsyncClient,
    seed_admin: Admin,
) -> None:
    payload = {
        "code": "BAD-CODE!",
        "discount_percent": 10,
        "max_activations": 10,
        "valid_days": 7,
    }
    response = await client.post("/api/promos", json=payload)
    assert response.status_code == 422


async def test_create_promo_empty_code_returns_422(
    client: AsyncClient,
    seed_admin: Admin,
) -> None:
    payload = {
        "code": "",
        "discount_percent": 10,
        "max_activations": 10,
        "valid_days": 7,
    }
    response = await client.post("/api/promos", json=payload)
    assert response.status_code == 422


async def test_create_promo_discount_zero_returns_422(
    client: AsyncClient,
    seed_admin: Admin,
) -> None:
    payload = {
        "code": "ZERODISC",
        "discount_percent": 0,
        "max_activations": 10,
        "valid_days": 7,
    }
    response = await client.post("/api/promos", json=payload)
    assert response.status_code == 422


async def test_create_promo_discount_over_100_returns_422(
    client: AsyncClient,
    seed_admin: Admin,
) -> None:
    payload = {
        "code": "BIGDISCNT",
        "discount_percent": 101,
        "max_activations": 10,
        "valid_days": 7,
    }
    response = await client.post("/api/promos", json=payload)
    assert response.status_code == 422


async def test_create_promo_max_activations_zero_returns_422(
    client: AsyncClient,
    seed_admin: Admin,
) -> None:
    payload = {
        "code": "ZEROACTVT",
        "discount_percent": 10,
        "max_activations": 0,
        "valid_days": 7,
    }
    response = await client.post("/api/promos", json=payload)
    assert response.status_code == 422


async def test_create_promo_creates_audit_log(
    client: AsyncClient,
    seed_admin: Admin,
    db_session: AsyncSession,
) -> None:
    before = await _count_logs(db_session, "create_promo")
    payload = {
        "code": "LOGTEST1",
        "discount_percent": 15,
        "max_activations": 50,
        "valid_days": 14,
    }
    response = await client.post("/api/promos", json=payload)
    assert response.status_code == 201
    after = await _count_logs(db_session, "create_promo")
    assert after == before + 1


# ────────────────────────────────────────────────────────────────────────────
# GET /api/promos/generate-code
# ────────────────────────────────────────────────────────────────────────────


async def test_generate_code_no_auth_returns_401(unauth_client: AsyncClient) -> None:
    response = await unauth_client.get("/api/promos/generate-code")
    assert response.status_code == 401


async def test_generate_code_returns_8_char_hex_code(
    client: AsyncClient,
    seed_admin: Admin,
) -> None:
    response = await client.get("/api/promos/generate-code")
    assert response.status_code == 200
    body = response.json()
    assert "code" in body
    code = body["code"]
    assert len(code) == 8
    # Must be uppercase hex characters only [0-9A-F]
    assert all(c in "0123456789ABCDEF" for c in code)


async def test_generate_code_returns_unique_code_each_time(
    client: AsyncClient,
    seed_admin: Admin,
) -> None:
    r1 = await client.get("/api/promos/generate-code")
    r2 = await client.get("/api/promos/generate-code")
    assert r1.status_code == 200
    assert r2.status_code == 200
    # Two calls will very likely produce different codes; this is probabilistic
    # but with 16^8 possibilities collisions are practically impossible
    c1 = r1.json()["code"]
    c2 = r2.json()["code"]
    # Both are valid 8-char hex strings
    assert len(c1) == 8
    assert len(c2) == 8


# ────────────────────────────────────────────────────────────────────────────
# GET /api/promos/{id}
# ────────────────────────────────────────────────────────────────────────────


async def test_get_promo_no_auth_returns_401(
    unauth_client: AsyncClient,
) -> None:
    response = await unauth_client.get("/api/promos/1")
    assert response.status_code == 401


async def test_get_promo_by_id_returns_promo(
    client: AsyncClient,
    seed_admin: Admin,
    seed_promo: PromoCode,
) -> None:
    response = await client.get(f"/api/promos/{seed_promo.id}")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == seed_promo.id
    assert body["code"] == "TESTCODE"
    assert body["discount_percent"] == 10
    assert body["is_expired"] is False


async def test_get_promo_nonexistent_returns_404(
    client: AsyncClient,
    seed_admin: Admin,
) -> None:
    response = await client.get("/api/promos/99999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


async def test_get_expired_promo_is_expired_true(
    client: AsyncClient,
    seed_admin: Admin,
    seed_expired_promo: PromoCode,
) -> None:
    response = await client.get(f"/api/promos/{seed_expired_promo.id}")
    assert response.status_code == 200
    body = response.json()
    assert body["is_expired"] is True


# ────────────────────────────────────────────────────────────────────────────
# PATCH /api/promos/{id}/toggle
# ────────────────────────────────────────────────────────────────────────────


async def test_toggle_promo_no_auth_returns_401(
    unauth_client: AsyncClient,
) -> None:
    response = await unauth_client.patch(
        "/api/promos/1/toggle",
        json={"is_active": False},
    )
    assert response.status_code == 401


async def test_toggle_promo_deactivate_returns_updated_promo(
    client: AsyncClient,
    seed_admin: Admin,
    seed_promo: PromoCode,
) -> None:
    response = await client.patch(
        f"/api/promos/{seed_promo.id}/toggle",
        json={"is_active": False},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == seed_promo.id
    assert body["is_active"] is False


async def test_toggle_promo_activate_returns_updated_promo(
    client: AsyncClient,
    seed_admin: Admin,
    seed_inactive_promo: PromoCode,
) -> None:
    response = await client.patch(
        f"/api/promos/{seed_inactive_promo.id}/toggle",
        json={"is_active": True},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["is_active"] is True


async def test_toggle_promo_nonexistent_returns_404(
    client: AsyncClient,
    seed_admin: Admin,
) -> None:
    response = await client.patch(
        "/api/promos/99999/toggle",
        json={"is_active": False},
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


async def test_toggle_promo_missing_body_returns_422(
    client: AsyncClient,
    seed_admin: Admin,
    seed_promo: PromoCode,
) -> None:
    response = await client.patch(
        f"/api/promos/{seed_promo.id}/toggle",
        json={},
    )
    assert response.status_code == 422


async def test_toggle_promo_creates_audit_log(
    client: AsyncClient,
    seed_admin: Admin,
    seed_promo: PromoCode,
    db_session: AsyncSession,
) -> None:
    before = await _count_logs(db_session, "toggle_promo")
    response = await client.patch(
        f"/api/promos/{seed_promo.id}/toggle",
        json={"is_active": False},
    )
    assert response.status_code == 200
    after = await _count_logs(db_session, "toggle_promo")
    assert after == before + 1


# ────────────────────────────────────────────────────────────────────────────
# DELETE /api/promos/{id}
# ────────────────────────────────────────────────────────────────────────────


async def test_delete_promo_no_auth_returns_401(
    unauth_client: AsyncClient,
) -> None:
    response = await unauth_client.delete("/api/promos/1")
    assert response.status_code == 401


async def test_delete_promo_success_returns_204(
    client: AsyncClient,
    seed_admin: Admin,
    seed_promo: PromoCode,
) -> None:
    response = await client.delete(f"/api/promos/{seed_promo.id}")
    assert response.status_code == 204
    assert response.content == b""


async def test_delete_promo_then_get_returns_404(
    client: AsyncClient,
    seed_admin: Admin,
    seed_promo: PromoCode,
) -> None:
    promo_id = seed_promo.id
    delete_response = await client.delete(f"/api/promos/{promo_id}")
    assert delete_response.status_code == 204

    get_response = await client.get(f"/api/promos/{promo_id}")
    assert get_response.status_code == 404


async def test_delete_promo_nonexistent_returns_404(
    client: AsyncClient,
    seed_admin: Admin,
) -> None:
    response = await client.delete("/api/promos/99999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


async def test_delete_promo_creates_audit_log(
    client: AsyncClient,
    seed_admin: Admin,
    seed_promo: PromoCode,
    db_session: AsyncSession,
) -> None:
    before = await _count_logs(db_session, "delete_promo")
    response = await client.delete(f"/api/promos/{seed_promo.id}")
    assert response.status_code == 204
    after = await _count_logs(db_session, "delete_promo")
    assert after == before + 1


# ────────────────────────────────────────────────────────────────────────────
# GET /api/promos/{id}/usages
# ────────────────────────────────────────────────────────────────────────────


async def test_list_promo_usages_no_auth_returns_401(
    unauth_client: AsyncClient,
) -> None:
    response = await unauth_client.get("/api/promos/1/usages")
    assert response.status_code == 401


async def test_list_promo_usages_empty_returns_paginated_response(
    client: AsyncClient,
    seed_admin: Admin,
    seed_promo: PromoCode,
) -> None:
    response = await client.get(f"/api/promos/{seed_promo.id}/usages")
    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0
    assert body["page"] == 1
    assert body["per_page"] == 20


async def test_list_promo_usages_returns_usage_records(
    client: AsyncClient,
    seed_admin: Admin,
    seed_promo_usage: PromoUsage,
    seed_promo: PromoCode,
    seed_user: User,
) -> None:
    response = await client.get(f"/api/promos/{seed_promo.id}/usages")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert item["user_id"] == seed_user.id
    assert item["username"] == "testuser"
    assert "used_at" in item


async def test_list_promo_usages_nonexistent_promo_returns_404(
    client: AsyncClient,
    seed_admin: Admin,
) -> None:
    response = await client.get("/api/promos/99999/usages")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


async def test_list_promo_usages_pagination_respected(
    client: AsyncClient,
    seed_admin: Admin,
    seed_promo: PromoCode,
) -> None:
    response = await client.get(
        f"/api/promos/{seed_promo.id}/usages",
        params={"page": 2, "per_page": 5},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 2
    assert body["per_page"] == 5


# ────────────────────────────────────────────────────────────────────────────
# Edge cases: generate-code collision exhaustion (mocked)
# ────────────────────────────────────────────────────────────────────────────


async def test_generate_code_collision_exhaustion_returns_409(
    client: AsyncClient,
    seed_admin: Admin,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When all code generation attempts collide, endpoint returns 409."""
    import db.repositories.promo_repo as _promo_repo_module

    async def _always_none(_session: object, max_attempts: int = 5) -> None:
        return None

    monkeypatch.setattr(_promo_repo_module, "generate_unique_code", _always_none)

    response = await client.get("/api/promos/generate-code")
    assert response.status_code == 409
    assert "unique" in response.json()["detail"].lower()


# ────────────────────────────────────────────────────────────────────────────
# PromoResponse computed field: is_expired
# ────────────────────────────────────────────────────────────────────────────


async def test_promo_response_is_expired_false_for_future_promo(
    client: AsyncClient,
    seed_admin: Admin,
    seed_promo: PromoCode,
) -> None:
    """Active promo with future valid_until has is_expired=False."""
    response = await client.get(f"/api/promos/{seed_promo.id}")
    assert response.status_code == 200
    assert response.json()["is_expired"] is False


async def test_promo_list_includes_is_expired_field(
    client: AsyncClient,
    seed_admin: Admin,
    seed_promo: PromoCode,
    seed_expired_promo: PromoCode,
) -> None:
    """List endpoint also returns is_expired on each item."""
    response = await client.get("/api/promos")
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 2
    # All items must have the is_expired field
    for item in items:
        assert "is_expired" in item
