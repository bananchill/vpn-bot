"""Tests for the settings API endpoints (TASK-018).

Covers:
- GET /api/settings — per-admin personal settings
- PUT /api/settings — update personal settings + sync to admin_sessions
- POST /api/settings/check — connection check using admin's credentials
- GET /api/settings/global — global settings, owner-only
- PUT /api/settings/global — update global settings, owner-only

Access control:
- All endpoints return 401 without auth
- GET/PUT /api/settings/global return 403 for non-owner

Business rules:
- PUT /api/settings with no fields returns 400
- PUT /api/settings persists encrypted password (not plaintext)
- PUT /api/settings writes to admin_sessions when full panel creds present
- GET /api/settings never exposes password in plaintext
- PUT /api/settings/global with no fields returns 400
- GET /api/settings returns has_panel_password=True after password saved
- Username is stored on admin creation (via DEV_MODE fixture)
"""

from __future__ import annotations

import json

import pytest
from db.models import Admin, AdminSession, BotSettings
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FULL_SETTINGS_PAYLOAD = {
    "panel_url": "https://panel.example.com",
    "panel_sub_url": "https://panel.example.com:2096",
    "panel_username": "admin_user",
    "panel_password": "secret123",
}

_PARTIAL_SETTINGS_PAYLOAD = {
    "panel_url": "https://panel.example.com",
}


# ---------------------------------------------------------------------------
# GET /api/settings — access control
# ---------------------------------------------------------------------------


async def test_get_settings_no_auth_returns_401(unauth_client: AsyncClient) -> None:
    response = await unauth_client.get("/api/settings")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/settings — happy path (admin with no data yet)
# ---------------------------------------------------------------------------


async def test_get_settings_empty_returns_null_fields(
    client: AsyncClient,
    seed_admin: Admin,
) -> None:
    """Freshly created admin has no panel settings — all fields should be None/False."""
    response = await client.get("/api/settings")
    assert response.status_code == 200
    body = response.json()

    assert body["panel_url"] is None
    assert body["panel_sub_url"] is None
    assert body["panel_username"] is None
    assert body["has_panel_password"] is False
    assert body["has_config_bot_token"] is False
    assert "updated_at" in body


async def test_get_settings_response_has_all_required_fields(
    client: AsyncClient,
    seed_admin: Admin,
) -> None:
    response = await client.get("/api/settings")
    assert response.status_code == 200
    body = response.json()

    required = [
        "panel_url",
        "panel_sub_url",
        "panel_username",
        "has_panel_password",
        "has_config_bot_token",
        "updated_at",
    ]
    for field in required:
        assert field in body, f"Missing field in response: {field}"


async def test_get_settings_password_never_exposed_as_plaintext(
    client: AsyncClient,
    seed_admin: Admin,
) -> None:
    """Response must NOT contain a 'panel_password' key."""
    response = await client.get("/api/settings")
    assert response.status_code == 200
    body = response.json()
    assert "panel_password" not in body


# ---------------------------------------------------------------------------
# PUT /api/settings — access control
# ---------------------------------------------------------------------------


async def test_put_settings_no_auth_returns_401(unauth_client: AsyncClient) -> None:
    response = await unauth_client.put("/api/settings", json=_FULL_SETTINGS_PAYLOAD)
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# PUT /api/settings — happy path
# ---------------------------------------------------------------------------


async def test_put_settings_updates_panel_url(
    client: AsyncClient,
    seed_admin: Admin,
) -> None:
    response = await client.put(
        "/api/settings",
        json={"panel_url": "https://new-panel.example.com"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["panel_url"] == "https://new-panel.example.com"


async def test_put_settings_full_payload_returns_200_with_correct_body(
    client: AsyncClient,
    seed_admin: Admin,
) -> None:
    response = await client.put("/api/settings", json=_FULL_SETTINGS_PAYLOAD)
    assert response.status_code == 200
    body = response.json()

    assert body["panel_url"] == "https://panel.example.com"
    assert body["panel_sub_url"] == "https://panel.example.com:2096"
    assert body["panel_username"] == "admin_user"
    assert body["has_panel_password"] is True
    assert "panel_password" not in body


async def test_put_settings_password_stored_encrypted(
    client: AsyncClient,
    seed_admin: Admin,
    db_session: AsyncSession,
) -> None:
    """After PUT, the Admin row should have an encrypted (not plaintext) password."""
    await client.put(
        "/api/settings",
        json={"panel_url": "https://p.example.com", "panel_password": "verysecret"},
    )

    result = await db_session.execute(
        select(Admin).where(Admin.telegram_id == seed_admin.telegram_id)
    )
    admin = result.scalar_one_or_none()
    assert admin is not None
    assert admin.panel_password_encrypted is not None
    # Must NOT store plaintext
    assert admin.panel_password_encrypted != "verysecret"
    # Must be a Fernet token (starts with "gA")
    assert admin.panel_password_encrypted.startswith("gA")


async def test_put_settings_config_bot_token_stored_encrypted(
    client: AsyncClient,
    seed_admin: Admin,
    db_session: AsyncSession,
) -> None:
    """config_bot_token must be Fernet-encrypted in the Admin row."""
    await client.put(
        "/api/settings",
        json={"config_bot_token": "1234567890:AABBBCCC"},
    )

    result = await db_session.execute(
        select(Admin).where(Admin.telegram_id == seed_admin.telegram_id)
    )
    admin = result.scalar_one_or_none()
    assert admin is not None
    assert admin.config_bot_token_encrypted is not None
    assert admin.config_bot_token_encrypted != "1234567890:AABBBCCC"
    assert admin.config_bot_token_encrypted.startswith("gA")


async def test_put_settings_has_config_bot_token_true_after_save(
    client: AsyncClient,
    seed_admin: Admin,
) -> None:
    response = await client.put(
        "/api/settings",
        json={"config_bot_token": "9876543210:ZZ"},
    )
    assert response.status_code == 200
    assert response.json()["has_config_bot_token"] is True


async def test_put_settings_partial_update_preserves_existing_fields(
    client: AsyncClient,
    seed_admin: Admin,
) -> None:
    """Updating only panel_url must not erase panel_username if it was set earlier."""
    # First set the username
    await client.put("/api/settings", json={"panel_username": "first_user"})

    # Then update only panel_url
    response = await client.put(
        "/api/settings",
        json={"panel_url": "https://updated.example.com"},
    )
    assert response.status_code == 200
    body = response.json()
    # The earlier-set username should still be reflected via GET
    get_response = await client.get("/api/settings")
    get_body = get_response.json()
    assert get_body["panel_username"] == "first_user"
    assert get_body["panel_url"] == "https://updated.example.com"


# ---------------------------------------------------------------------------
# PUT /api/settings — empty payload returns 400
# ---------------------------------------------------------------------------


async def test_put_settings_no_fields_returns_400(
    client: AsyncClient,
    seed_admin: Admin,
) -> None:
    """Sending a payload with all null values should return 400."""
    response = await client.put("/api/settings", json={})
    assert response.status_code == 400
    assert "no fields" in response.json()["detail"].lower()


async def test_put_settings_all_null_fields_returns_400(
    client: AsyncClient,
    seed_admin: Admin,
) -> None:
    response = await client.put(
        "/api/settings",
        json={
            "panel_url": None,
            "panel_sub_url": None,
            "panel_username": None,
            "panel_password": None,
            "config_bot_token": None,
        },
    )
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# PUT /api/settings — admin_sessions sync
# ---------------------------------------------------------------------------


async def test_put_settings_full_creds_creates_admin_session(
    client: AsyncClient,
    seed_admin: Admin,
    db_session: AsyncSession,
) -> None:
    """With full panel creds, admin_sessions row must be created/updated."""
    response = await client.put("/api/settings", json=_FULL_SETTINGS_PAYLOAD)
    assert response.status_code == 200

    result = await db_session.execute(select(AdminSession))
    sessions = result.scalars().all()
    assert len(sessions) == 1
    session_row = sessions[0]
    assert session_row.panel_url == "https://panel.example.com"
    # encrypted_credentials must be a non-empty Fernet token
    assert session_row.encrypted_credentials.startswith("gA")


async def test_put_settings_full_creds_admin_session_credentials_format(
    client: AsyncClient,
    seed_admin: Admin,
    db_session: AsyncSession,
) -> None:
    """admin_sessions.encrypted_credentials must decrypt to {username, password} JSON."""
    from utils.crypto import decrypt

    await client.put("/api/settings", json=_FULL_SETTINGS_PAYLOAD)

    result = await db_session.execute(select(AdminSession))
    session_row = result.scalars().first()
    assert session_row is not None

    plaintext = decrypt(session_row.encrypted_credentials)
    creds = json.loads(plaintext)
    assert creds["username"] == "admin_user"
    assert creds["password"] == "secret123"


async def test_put_settings_updates_existing_admin_session(
    client: AsyncClient,
    seed_admin: Admin,
    db_session: AsyncSession,
) -> None:
    """Second PUT with new password must update the existing admin_sessions row."""
    await client.put("/api/settings", json=_FULL_SETTINGS_PAYLOAD)

    # Update with new password
    await client.put(
        "/api/settings",
        json={
            "panel_url": "https://panel.example.com",
            "panel_username": "admin_user",
            "panel_password": "newpassword",
        },
    )

    result = await db_session.execute(select(AdminSession))
    sessions = result.scalars().all()
    assert len(sessions) == 1  # Still only one row, not two


async def test_put_settings_admin_session_cookie_cleared_on_update(
    client: AsyncClient,
    seed_admin: Admin,
    db_session: AsyncSession,
) -> None:
    """Existing session cookie must be cleared when credentials change."""
    from utils.crypto import decrypt

    # First save
    await client.put("/api/settings", json=_FULL_SETTINGS_PAYLOAD)

    # Manually set a cookie on the session row
    result = await db_session.execute(select(AdminSession))
    session_row = result.scalars().first()
    assert session_row is not None
    session_row.session_cookie = "old_cookie_value"
    await db_session.flush()

    # Update credentials again
    await client.put(
        "/api/settings",
        json={
            "panel_url": "https://panel.example.com",
            "panel_username": "admin_user",
            "panel_password": "refreshedpassword",
        },
    )

    await db_session.refresh(session_row)
    assert session_row.session_cookie is None


async def test_put_settings_partial_no_password_skips_admin_session(
    client: AsyncClient,
    seed_admin: Admin,
    db_session: AsyncSession,
) -> None:
    """Without a password (no existing one either), admin_sessions must NOT be touched."""
    # Only panel_url, no password
    await client.put(
        "/api/settings",
        json={"panel_url": "https://nopwd.example.com", "panel_username": "nouser"},
    )

    result = await db_session.execute(select(AdminSession))
    sessions = result.scalars().all()
    assert len(sessions) == 0


# ---------------------------------------------------------------------------
# PUT /api/settings — creates audit log
# ---------------------------------------------------------------------------


async def test_put_settings_creates_audit_log(
    client: AsyncClient,
    seed_admin: Admin,
    db_session: AsyncSession,
) -> None:
    from db.models import AdminLog

    response = await client.put("/api/settings", json=_FULL_SETTINGS_PAYLOAD)
    assert response.status_code == 200

    result = await db_session.execute(
        select(AdminLog).where(AdminLog.action == "update_settings")
    )
    logs = result.scalars().all()
    assert len(logs) >= 1
    assert logs[0].admin_telegram_id == seed_admin.telegram_id


# ---------------------------------------------------------------------------
# POST /api/settings/check — access control
# ---------------------------------------------------------------------------


async def test_check_connection_no_auth_returns_401(unauth_client: AsyncClient) -> None:
    response = await unauth_client.post("/api/settings/check")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# POST /api/settings/check — missing credentials
# ---------------------------------------------------------------------------


async def test_check_connection_no_credentials_returns_success_false(
    client: AsyncClient,
    seed_admin: Admin,
) -> None:
    """Admin with no panel settings configured should get success=False."""
    response = await client.post("/api/settings/check")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is False
    assert "not configured" in body["message"].lower() or "not set" in body["message"].lower()


async def test_check_connection_missing_password_returns_success_false(
    client: AsyncClient,
    seed_admin: Admin,
) -> None:
    """Admin with url+username but no password should get success=False."""
    await client.put(
        "/api/settings",
        json={"panel_url": "https://panel.example.com", "panel_username": "admin"},
    )
    response = await client.post("/api/settings/check")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is False


async def test_check_connection_response_has_required_fields(
    client: AsyncClient,
    seed_admin: Admin,
) -> None:
    response = await client.post("/api/settings/check")
    assert response.status_code == 200
    body = response.json()
    assert "success" in body
    assert "message" in body
    assert "response_time_ms" in body


# ---------------------------------------------------------------------------
# GET /api/settings/global — access control
# ---------------------------------------------------------------------------


async def test_get_global_settings_no_auth_returns_401(
    unauth_client: AsyncClient,
) -> None:
    response = await unauth_client.get("/api/settings/global")
    assert response.status_code == 401


async def test_get_global_settings_non_owner_returns_403(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """A non-owner admin (moderator) must get 403 on global settings."""
    from db.models import Admin as AdminModel

    moderator = AdminModel(telegram_id=999111222, role="moderator")
    db_session.add(moderator)
    await db_session.flush()

    # The DEV_MODE admin is 111111111 and is always 'owner' via seed_admin.
    # To test a non-owner, we override get_current_admin to return the moderator.
    import sys
    from fastapi import HTTPException
    from main import app
    from api.deps import get_current_admin, get_db

    async def _moderator_admin() -> AdminModel:
        return moderator

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_current_admin] = _moderator_admin
    app.dependency_overrides[get_db] = _override_get_db

    from httpx import ASGITransport, AsyncClient as HTTPX_AC

    transport = ASGITransport(app=app)
    async with HTTPX_AC(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/settings/global")

    app.dependency_overrides.clear()

    assert response.status_code == 403
    assert "owner" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# GET /api/settings/global — happy path (owner)
# ---------------------------------------------------------------------------


async def test_get_global_settings_empty_returns_defaults(
    client: AsyncClient,
    seed_admin: Admin,
) -> None:
    """When no BotSettings row exists, global settings should return null values."""
    response = await client.get("/api/settings/global")
    assert response.status_code == 200
    body = response.json()
    assert body["owner_id"] is None
    assert body["client_bot_token_masked"] is None
    assert "updated_at" in body


async def test_get_global_settings_response_has_all_required_fields(
    client: AsyncClient,
    seed_admin: Admin,
) -> None:
    response = await client.get("/api/settings/global")
    assert response.status_code == 200
    body = response.json()

    required = ["owner_id", "client_bot_token_masked", "updated_at"]
    for field in required:
        assert field in body, f"Missing field: {field}"


# ---------------------------------------------------------------------------
# PUT /api/settings/global — access control
# ---------------------------------------------------------------------------


async def test_put_global_settings_no_auth_returns_401(
    unauth_client: AsyncClient,
) -> None:
    response = await unauth_client.put(
        "/api/settings/global",
        json={"owner_id": 12345},
    )
    assert response.status_code == 401


async def test_put_global_settings_non_owner_returns_403(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """A moderator must get 403 when trying to update global settings."""
    from db.models import Admin as AdminModel
    from main import app
    from api.deps import get_current_admin, get_db

    moderator = AdminModel(telegram_id=888111222, role="moderator")
    db_session.add(moderator)
    await db_session.flush()

    async def _moderator_admin() -> AdminModel:
        return moderator

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_current_admin] = _moderator_admin
    app.dependency_overrides[get_db] = _override_get_db

    from httpx import ASGITransport, AsyncClient as HTTPX_AC

    transport = ASGITransport(app=app)
    async with HTTPX_AC(transport=transport, base_url="http://test") as ac:
        response = await ac.put("/api/settings/global", json={"owner_id": 12345})

    app.dependency_overrides.clear()

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# PUT /api/settings/global — happy path (owner)
# ---------------------------------------------------------------------------


async def test_put_global_settings_owner_id_returns_200(
    client: AsyncClient,
    seed_admin: Admin,
) -> None:
    response = await client.put(
        "/api/settings/global",
        json={"owner_id": 123456789},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["owner_id"] == 123456789


async def test_put_global_settings_client_bot_token_returns_masked(
    client: AsyncClient,
    seed_admin: Admin,
) -> None:
    """client_bot_token must be masked in the response, never in plaintext."""
    response = await client.put(
        "/api/settings/global",
        json={"client_bot_token": "1234567890:SomeRealToken"},
    )
    assert response.status_code == 200
    body = response.json()
    # Must be masked (last 4 chars of plaintext with leading asterisks)
    assert body["client_bot_token_masked"] is not None
    assert "****" in body["client_bot_token_masked"]
    # Must NOT return the plaintext
    assert "SomeRealToken" not in body["client_bot_token_masked"]


async def test_put_global_settings_token_stored_encrypted(
    client: AsyncClient,
    seed_admin: Admin,
    db_session: AsyncSession,
) -> None:
    """client_bot_token must be Fernet-encrypted in the BotSettings row."""
    await client.put(
        "/api/settings/global",
        json={"client_bot_token": "111:PlainToken"},
    )

    result = await db_session.execute(
        select(BotSettings).where(BotSettings.id == 1)
    )
    settings = result.scalar_one_or_none()
    assert settings is not None
    assert settings.client_bot_token is not None
    assert settings.client_bot_token != "111:PlainToken"
    assert settings.client_bot_token.startswith("gA")


# ---------------------------------------------------------------------------
# PUT /api/settings/global — no fields returns 400
# ---------------------------------------------------------------------------


async def test_put_global_settings_no_fields_returns_400(
    client: AsyncClient,
    seed_admin: Admin,
) -> None:
    response = await client.put("/api/settings/global", json={})
    assert response.status_code == 400
    assert "no fields" in response.json()["detail"].lower()


async def test_put_global_settings_all_null_returns_400(
    client: AsyncClient,
    seed_admin: Admin,
) -> None:
    response = await client.put(
        "/api/settings/global",
        json={"owner_id": None, "client_bot_token": None},
    )
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# PUT /api/settings/global — creates audit log
# ---------------------------------------------------------------------------


async def test_put_global_settings_creates_audit_log(
    client: AsyncClient,
    seed_admin: Admin,
    db_session: AsyncSession,
) -> None:
    from db.models import AdminLog

    response = await client.put(
        "/api/settings/global",
        json={"owner_id": 777888999},
    )
    assert response.status_code == 200

    result = await db_session.execute(
        select(AdminLog).where(AdminLog.action == "update_global_settings")
    )
    logs = result.scalars().all()
    assert len(logs) >= 1
    assert logs[0].admin_telegram_id == seed_admin.telegram_id


# ---------------------------------------------------------------------------
# GET /api/settings — reflects data saved by PUT
# ---------------------------------------------------------------------------


async def test_get_settings_reflects_put_changes(
    client: AsyncClient,
    seed_admin: Admin,
) -> None:
    """After a successful PUT, GET must return the updated values."""
    await client.put(
        "/api/settings",
        json={
            "panel_url": "https://reflect.example.com",
            "panel_sub_url": "https://reflect.example.com:2096",
            "panel_username": "reflect_user",
            "panel_password": "reflect_pass",
        },
    )

    response = await client.get("/api/settings")
    assert response.status_code == 200
    body = response.json()
    assert body["panel_url"] == "https://reflect.example.com"
    assert body["panel_sub_url"] == "https://reflect.example.com:2096"
    assert body["panel_username"] == "reflect_user"
    assert body["has_panel_password"] is True


# ---------------------------------------------------------------------------
# GET /api/settings/global — reflects data saved by PUT
# ---------------------------------------------------------------------------


async def test_get_global_settings_reflects_put_changes(
    client: AsyncClient,
    seed_admin: Admin,
) -> None:
    await client.put(
        "/api/settings/global",
        json={"owner_id": 555444333},
    )

    response = await client.get("/api/settings/global")
    assert response.status_code == 200
    body = response.json()
    assert body["owner_id"] == 555444333
