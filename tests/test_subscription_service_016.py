"""Tests for TASK-016 additions to subscription_service:
- Smart renewal logic (stacking on active subscription)
- sync_configs_expiry: success, partial failure, empty configs
- _find_client_by_uuid helper
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from bot.dto import ConfigDTO, SubscriptionDTO
from bot.services.subscription_service import (
    _find_client_by_uuid,
    sync_configs_expiry,
)

NOW = datetime(2026, 3, 2, 12, 0, 0, tzinfo=UTC)
EXPIRES_ACTIVE = NOW + timedelta(days=15)  # subscription still active
NEW_EXPIRES = EXPIRES_ACTIVE + timedelta(days=30)  # after renewal


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_sub_dto(
    user_id: int = 1,
    source: str = "stars",
    expires_at: datetime | None = None,
) -> SubscriptionDTO:
    exp = expires_at or (NOW + timedelta(days=30))
    return SubscriptionDTO(
        id=1,
        user_id=user_id,
        started_at=NOW,
        expires_at=exp,
        source=source,
        promo_code=None,
        created_at=NOW,
    )


def _make_config_dto(
    config_id: int = 1,
    client_id: str = "uuid-aaa",
    inbound_id: int = 1,
    email: str = "testcfg",
) -> ConfigDTO:
    return ConfigDTO(
        id=config_id,
        user_id=1,
        inbound_id=inbound_id,
        client_id=client_id,
        sub_id="abcdef1234567890",
        email=email,
        protocol="vless",
        created_at=NOW,
    )


# ---------------------------------------------------------------------------
# Smart renewal: activate() stacking logic
# (tests for the SubscriptionRepository path through service)
# ---------------------------------------------------------------------------


class TestActivateSmartRenewal:
    @pytest.mark.asyncio
    async def test_active_sub_starts_from_existing_expires_at(self) -> None:
        """When a subscription is active, new started_at == existing expires_at."""
        from bot.services.subscription_service import activate

        session = AsyncMock()
        existing = _make_sub_dto(expires_at=EXPIRES_ACTIVE)
        new_sub = _make_sub_dto(expires_at=NEW_EXPIRES)

        with patch(
            "bot.services.subscription_service.SubscriptionRepository"
        ) as mock_cls:
            mock_repo = mock_cls.return_value
            mock_repo.get_active = AsyncMock(return_value=existing)
            mock_repo.create = AsyncMock(return_value=new_sub)

            await activate(1, "stars", session)

        kwargs = mock_repo.create.call_args[1]
        assert kwargs["started_at"] == EXPIRES_ACTIVE
        assert kwargs["expires_at"] == EXPIRES_ACTIVE + timedelta(days=30)

    @pytest.mark.asyncio
    async def test_expired_sub_starts_from_now(self) -> None:
        """When no active subscription exists, new period starts from now."""
        from bot.services.subscription_service import activate

        session = AsyncMock()
        new_sub = _make_sub_dto()

        with patch(
            "bot.services.subscription_service.SubscriptionRepository"
        ) as mock_cls:
            mock_repo = mock_cls.return_value
            mock_repo.get_active = AsyncMock(return_value=None)
            mock_repo.create = AsyncMock(return_value=new_sub)

            await activate(1, "stars", session)

        kwargs = mock_repo.create.call_args[1]
        # started_at should be approximately now (within a few seconds)
        delta = abs((kwargs["started_at"] - datetime.now(tz=UTC)).total_seconds())
        assert delta < 5
        assert kwargs["expires_at"] == kwargs["started_at"] + timedelta(days=30)

    @pytest.mark.asyncio
    async def test_stacking_adds_30_days_to_existing_expiry(self) -> None:
        """New expires_at must be exactly 30 days after the old expires_at."""
        from bot.services.subscription_service import activate

        session = AsyncMock()
        existing = _make_sub_dto(expires_at=EXPIRES_ACTIVE)
        new_sub = _make_sub_dto()

        with patch(
            "bot.services.subscription_service.SubscriptionRepository"
        ) as mock_cls:
            mock_repo = mock_cls.return_value
            mock_repo.get_active = AsyncMock(return_value=existing)
            mock_repo.create = AsyncMock(return_value=new_sub)

            await activate(1, "ton", session)

        kwargs = mock_repo.create.call_args[1]
        assert kwargs["expires_at"] - kwargs["started_at"] == timedelta(days=30)


# ---------------------------------------------------------------------------
# sync_configs_expiry
# ---------------------------------------------------------------------------


class TestSyncConfigsExpiry:
    @pytest.mark.asyncio
    async def test_returns_true_when_no_configs(self) -> None:
        """If the user has no configs, sync should succeed with True."""
        xui = AsyncMock()
        session = AsyncMock()

        with patch(
            "bot.services.subscription_service.ConfigRepository"
        ) as mock_cls:
            mock_repo = mock_cls.return_value
            mock_repo.get_by_user_id = AsyncMock(return_value=[])

            result = await sync_configs_expiry(1, NEW_EXPIRES, xui, session)

        assert result is True
        xui.get_inbound.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_updates_expiry_time_in_ms(self) -> None:
        """expiryTime sent to xui.update_client must be expires_at in milliseconds."""
        xui = AsyncMock()
        session = AsyncMock()

        cfg = _make_config_dto(client_id="uuid-abc", inbound_id=2)
        client_data = {"id": "uuid-abc", "expiryTime": 0, "enable": True}
        inbound = {
            "settings": json.dumps({"clients": [client_data]}),
        }
        xui.get_inbound = AsyncMock(return_value=inbound)
        xui.update_client = AsyncMock()

        with patch(
            "bot.services.subscription_service.ConfigRepository"
        ) as mock_cls:
            mock_repo = mock_cls.return_value
            mock_repo.get_by_user_id = AsyncMock(return_value=[cfg])

            result = await sync_configs_expiry(1, NEW_EXPIRES, xui, session)

        assert result is True
        xui.update_client.assert_awaited_once()
        sent_data = xui.update_client.call_args[0][2]
        expected_ms = int(NEW_EXPIRES.timestamp() * 1000)
        assert sent_data["expiryTime"] == expected_ms

    @pytest.mark.asyncio
    async def test_returns_false_when_client_not_in_inbound(self) -> None:
        """If the client UUID is not found in the inbound settings, return False."""
        xui = AsyncMock()
        session = AsyncMock()

        cfg = _make_config_dto(client_id="missing-uuid", inbound_id=1)
        inbound = {
            "settings": json.dumps({"clients": [{"id": "other-uuid", "expiryTime": 0}]}),
        }
        xui.get_inbound = AsyncMock(return_value=inbound)
        xui.update_client = AsyncMock()

        with patch(
            "bot.services.subscription_service.ConfigRepository"
        ) as mock_cls:
            mock_repo = mock_cls.return_value
            mock_repo.get_by_user_id = AsyncMock(return_value=[cfg])

            result = await sync_configs_expiry(1, NEW_EXPIRES, xui, session)

        assert result is False
        xui.update_client.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_returns_false_when_xui_raises(self) -> None:
        """If xui.get_inbound raises, the function returns False (not re-raised)."""
        xui = AsyncMock()
        xui.get_inbound = AsyncMock(side_effect=Exception("Connection error"))
        session = AsyncMock()

        cfg = _make_config_dto(client_id="uuid-xyz", inbound_id=1)

        with patch(
            "bot.services.subscription_service.ConfigRepository"
        ) as mock_cls:
            mock_repo = mock_cls.return_value
            mock_repo.get_by_user_id = AsyncMock(return_value=[cfg])

            result = await sync_configs_expiry(1, NEW_EXPIRES, xui, session)

        assert result is False

    @pytest.mark.asyncio
    async def test_partial_failure_returns_false(self) -> None:
        """If one config fails but another succeeds, overall result is False."""
        xui = AsyncMock()
        session = AsyncMock()

        cfg_ok = _make_config_dto(config_id=1, client_id="uuid-ok", inbound_id=1)
        cfg_bad = _make_config_dto(config_id=2, client_id="uuid-bad", inbound_id=2)

        good_inbound = {
            "settings": json.dumps({"clients": [{"id": "uuid-ok", "expiryTime": 0}]}),
        }
        bad_inbound = {
            "settings": json.dumps({"clients": [{"id": "other", "expiryTime": 0}]}),
        }

        xui.get_inbound = AsyncMock(side_effect=[good_inbound, bad_inbound])
        xui.update_client = AsyncMock()

        with patch(
            "bot.services.subscription_service.ConfigRepository"
        ) as mock_cls:
            mock_repo = mock_cls.return_value
            mock_repo.get_by_user_id = AsyncMock(return_value=[cfg_ok, cfg_bad])

            result = await sync_configs_expiry(1, NEW_EXPIRES, xui, session)

        assert result is False
        # The successful config was still updated
        xui.update_client.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_settings_as_dict_not_string(self) -> None:
        """If inbound settings is already a dict (not a JSON string), it is handled correctly."""
        xui = AsyncMock()
        session = AsyncMock()

        cfg = _make_config_dto(client_id="uuid-dict", inbound_id=3)
        inbound = {
            "settings": {"clients": [{"id": "uuid-dict", "expiryTime": 0}]},
        }
        xui.get_inbound = AsyncMock(return_value=inbound)
        xui.update_client = AsyncMock()

        with patch(
            "bot.services.subscription_service.ConfigRepository"
        ) as mock_cls:
            mock_repo = mock_cls.return_value
            mock_repo.get_by_user_id = AsyncMock(return_value=[cfg])

            result = await sync_configs_expiry(1, NEW_EXPIRES, xui, session)

        assert result is True
        xui.update_client.assert_awaited_once()


# ---------------------------------------------------------------------------
# _find_client_by_uuid
# ---------------------------------------------------------------------------


class TestFindClientByUuid:
    def test_returns_matching_client(self) -> None:
        clients = [
            {"id": "aaa", "expiryTime": 0},
            {"id": "bbb", "expiryTime": 100},
        ]
        result = _find_client_by_uuid(clients, "bbb")
        assert result is not None
        assert result["id"] == "bbb"

    def test_returns_none_when_not_found(self) -> None:
        clients = [{"id": "aaa"}, {"id": "bbb"}]
        result = _find_client_by_uuid(clients, "zzz")
        assert result is None

    def test_returns_none_for_empty_list(self) -> None:
        result = _find_client_by_uuid([], "any-uuid")
        assert result is None

    def test_returns_first_match_only(self) -> None:
        """If two entries have the same id (data bug), the first is returned."""
        clients = [
            {"id": "dup", "label": "first"},
            {"id": "dup", "label": "second"},
        ]
        result = _find_client_by_uuid(clients, "dup")
        assert result is not None
        assert result["label"] == "first"
