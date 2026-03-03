"""Tests for bot.services.subscription_service -- subscription business logic."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from bot.dto import PromoCodeDTO, SubscriptionDTO
from bot.services.subscription_service import (
    PromoCodeAlreadyUsedError,
    PromoCodeNotFoundError,
    activate,
    activate_promo,
    get_active,
)

NOW = datetime(2026, 3, 1, tzinfo=UTC)


def _make_sub_dto(
    user_id: int = 1,
    source: str = "stars",
    promo_code: str | None = None,
) -> SubscriptionDTO:
    return SubscriptionDTO(
        id=1,
        user_id=user_id,
        started_at=NOW,
        expires_at=NOW + timedelta(days=30),
        source=source,
        promo_code=promo_code,
        created_at=NOW,
    )


def _make_promo_dto(
    code: str = "testpromo",
    is_active: bool = True,
    use_count: int = 0,
) -> PromoCodeDTO:
    return PromoCodeDTO(
        id=1,
        code=code,
        is_active=is_active,
        use_count=use_count,
        created_at=NOW,
    )


# ---------------------------------------------------------------------------
# get_active
# ---------------------------------------------------------------------------


class TestGetActive:
    @pytest.mark.asyncio
    async def test_returns_active_subscription(self) -> None:
        session = AsyncMock()
        sub = _make_sub_dto()

        with patch(
            "bot.services.subscription_service.SubscriptionRepository"
        ) as mock_cls:
            mock_repo = mock_cls.return_value
            mock_repo.get_active = AsyncMock(return_value=sub)

            result = await get_active(1, session)

        assert result is not None
        assert result.source == "stars"

    @pytest.mark.asyncio
    async def test_returns_none_when_no_active(self) -> None:
        session = AsyncMock()

        with patch(
            "bot.services.subscription_service.SubscriptionRepository"
        ) as mock_cls:
            mock_repo = mock_cls.return_value
            mock_repo.get_active = AsyncMock(return_value=None)

            result = await get_active(1, session)

        assert result is None


# ---------------------------------------------------------------------------
# activate
# ---------------------------------------------------------------------------


class TestActivate:
    @pytest.mark.asyncio
    async def test_creates_subscription_with_correct_source(self) -> None:
        session = AsyncMock()
        sub = _make_sub_dto(source="stars")

        with patch(
            "bot.services.subscription_service.SubscriptionRepository"
        ) as mock_cls:
            mock_repo = mock_cls.return_value
            # No active subscription — fresh activation
            mock_repo.get_active = AsyncMock(return_value=None)
            mock_repo.create = AsyncMock(return_value=sub)

            result = await activate(1, "stars", session)

        assert result.source == "stars"
        mock_repo.create.assert_called_once()
        call_kwargs = mock_repo.create.call_args[1]
        assert call_kwargs["user_id"] == 1
        assert call_kwargs["source"] == "stars"

    @pytest.mark.asyncio
    async def test_sets_30_day_expiry(self) -> None:
        session = AsyncMock()
        sub = _make_sub_dto()

        with patch(
            "bot.services.subscription_service.SubscriptionRepository"
        ) as mock_cls:
            mock_repo = mock_cls.return_value
            mock_repo.get_active = AsyncMock(return_value=None)
            mock_repo.create = AsyncMock(return_value=sub)

            await activate(1, "ton", session)

        call_kwargs = mock_repo.create.call_args[1]
        delta = call_kwargs["expires_at"] - call_kwargs["started_at"]
        assert delta == timedelta(days=30)

    @pytest.mark.asyncio
    async def test_stacks_on_existing_subscription(self) -> None:
        """When user has an active subscription, new period starts from existing expires_at."""
        session = AsyncMock()
        existing_sub = _make_sub_dto(source="stars")
        new_sub = _make_sub_dto(source="stars")

        with patch(
            "bot.services.subscription_service.SubscriptionRepository"
        ) as mock_cls:
            mock_repo = mock_cls.return_value
            mock_repo.get_active = AsyncMock(return_value=existing_sub)
            mock_repo.create = AsyncMock(return_value=new_sub)

            await activate(1, "stars", session)

        call_kwargs = mock_repo.create.call_args[1]
        # New subscription should start from existing expiry
        assert call_kwargs["started_at"] == existing_sub.expires_at
        expected_expires = existing_sub.expires_at + timedelta(days=30)
        assert call_kwargs["expires_at"] == expected_expires


# ---------------------------------------------------------------------------
# activate_promo
# ---------------------------------------------------------------------------


class TestActivatePromo:
    @pytest.mark.asyncio
    async def test_activates_valid_promo(self) -> None:
        session = AsyncMock()
        promo = _make_promo_dto(code="testcode")
        sub = _make_sub_dto(source="promo", promo_code="testcode")

        with (
            patch(
                "bot.services.subscription_service.PromoCodeRepository"
            ) as mock_promo_cls,
            patch(
                "bot.services.subscription_service.SubscriptionRepository"
            ) as mock_sub_cls,
        ):
            mock_promo_repo = mock_promo_cls.return_value
            mock_promo_repo.get_by_code = AsyncMock(return_value=promo)
            mock_promo_repo.increment_use_count = AsyncMock()

            mock_sub_repo = mock_sub_cls.return_value
            mock_sub_repo.has_used_promo = AsyncMock(return_value=False)
            mock_sub_repo.get_active = AsyncMock(return_value=None)
            mock_sub_repo.create = AsyncMock(return_value=sub)

            result = await activate_promo(1, "TESTCODE", session)

        assert result.source == "promo"
        assert result.promo_code == "testcode"
        mock_promo_repo.increment_use_count.assert_called_once_with("testcode")

    @pytest.mark.asyncio
    async def test_raises_not_found_for_nonexistent_code(self) -> None:
        session = AsyncMock()

        with patch(
            "bot.services.subscription_service.PromoCodeRepository"
        ) as mock_promo_cls:
            mock_promo_repo = mock_promo_cls.return_value
            mock_promo_repo.get_by_code = AsyncMock(return_value=None)

            with pytest.raises(PromoCodeNotFoundError):
                await activate_promo(1, "badcode", session)

    @pytest.mark.asyncio
    async def test_raises_not_found_for_inactive_code(self) -> None:
        session = AsyncMock()
        promo = _make_promo_dto(code="disabled", is_active=False)

        with patch(
            "bot.services.subscription_service.PromoCodeRepository"
        ) as mock_promo_cls:
            mock_promo_repo = mock_promo_cls.return_value
            mock_promo_repo.get_by_code = AsyncMock(return_value=promo)

            with pytest.raises(PromoCodeNotFoundError):
                await activate_promo(1, "disabled", session)

    @pytest.mark.asyncio
    async def test_raises_already_used(self) -> None:
        session = AsyncMock()
        promo = _make_promo_dto(code="usedcode")

        with (
            patch(
                "bot.services.subscription_service.PromoCodeRepository"
            ) as mock_promo_cls,
            patch(
                "bot.services.subscription_service.SubscriptionRepository"
            ) as mock_sub_cls,
        ):
            mock_promo_repo = mock_promo_cls.return_value
            mock_promo_repo.get_by_code = AsyncMock(return_value=promo)

            mock_sub_repo = mock_sub_cls.return_value
            mock_sub_repo.has_used_promo = AsyncMock(return_value=True)

            with pytest.raises(PromoCodeAlreadyUsedError):
                await activate_promo(1, "usedcode", session)

    @pytest.mark.asyncio
    async def test_normalizes_code_to_lowercase(self) -> None:
        session = AsyncMock()
        promo = _make_promo_dto(code="mycode")
        sub = _make_sub_dto(source="promo", promo_code="mycode")

        with (
            patch(
                "bot.services.subscription_service.PromoCodeRepository"
            ) as mock_promo_cls,
            patch(
                "bot.services.subscription_service.SubscriptionRepository"
            ) as mock_sub_cls,
        ):
            mock_promo_repo = mock_promo_cls.return_value
            mock_promo_repo.get_by_code = AsyncMock(return_value=promo)
            mock_promo_repo.increment_use_count = AsyncMock()

            mock_sub_repo = mock_sub_cls.return_value
            mock_sub_repo.has_used_promo = AsyncMock(return_value=False)
            mock_sub_repo.get_active = AsyncMock(return_value=None)
            mock_sub_repo.create = AsyncMock(return_value=sub)

            await activate_promo(1, "  MYCODE  ", session)

        # Should be called with normalized lowercase code
        mock_promo_repo.get_by_code.assert_called_once_with("mycode")
        mock_sub_repo.has_used_promo.assert_called_once_with(1, "mycode")
