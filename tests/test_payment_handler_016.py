"""Tests for TASK-016 additions to payment handler:
- _sync_after_payment sets configs_sync_pending=True on failure
- _sync_after_payment sends user message on failure
- renew_subscription handler (pay:menu callback)
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.types import Chat, Message, User

from bot.dto import UserDTO
from bot.handlers.payment import (
    _sync_after_payment,
    renew_subscription,
)

NOW = datetime(2026, 3, 2, 12, 0, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_message(user_id: int = 123456) -> MagicMock:
    msg = MagicMock(spec=Message)
    msg.chat = MagicMock(spec=Chat)
    msg.chat.id = user_id
    msg.from_user = MagicMock(spec=User)
    msg.from_user.id = user_id
    msg.answer = AsyncMock()
    return msg


def _make_user_dto(user_id: int = 1) -> UserDTO:
    return UserDTO(
        id=user_id,
        telegram_id=123456,
        username="testuser",
        is_admin=False,
        created_at=NOW,
    )


def _make_callback(data: str = "pay:menu") -> MagicMock:
    from aiogram.types import CallbackQuery

    cb = MagicMock(spec=CallbackQuery)
    cb.data = data
    cb.from_user = MagicMock(spec=User)
    cb.from_user.id = 123456
    cb.message = MagicMock()
    cb.message.answer = AsyncMock()
    cb.message.edit_text = AsyncMock()
    cb.answer = AsyncMock()
    return cb


# ---------------------------------------------------------------------------
# _sync_after_payment
# ---------------------------------------------------------------------------


class TestSyncAfterPayment:
    @pytest.mark.asyncio
    async def test_no_message_when_sync_succeeds(self) -> None:
        """When sync succeeds (returns True), no pending message should be sent."""
        msg = _make_message()
        session = AsyncMock()
        expires_at = NOW + timedelta(days=30)

        with (
            patch(
                "bot.handlers.payment._get_xui_client",
                new_callable=AsyncMock,
                return_value=AsyncMock(close=AsyncMock()),
            ),
            patch(
                "bot.handlers.payment.sync_configs_expiry",
                new_callable=AsyncMock,
                return_value=True,
            ),
        ):
            await _sync_after_payment(1, 10, expires_at, session, msg)

        msg.answer.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_sets_sync_pending_when_sync_returns_false(self) -> None:
        """When sync_configs_expiry returns False, subscription must be flagged for retry."""
        msg = _make_message()
        session = AsyncMock()
        expires_at = NOW + timedelta(days=30)

        with (
            patch(
                "bot.handlers.payment._get_xui_client",
                new_callable=AsyncMock,
                return_value=AsyncMock(close=AsyncMock()),
            ),
            patch(
                "bot.handlers.payment.sync_configs_expiry",
                new_callable=AsyncMock,
                return_value=False,
            ),
            patch(
                "bot.handlers.payment.SubscriptionRepository",
            ) as mock_repo_cls,
        ):
            mock_repo = mock_repo_cls.return_value
            mock_repo.set_sync_pending = AsyncMock()

            await _sync_after_payment(1, 10, expires_at, session, msg)

        mock_repo.set_sync_pending.assert_awaited_once_with(10, pending=True)

    @pytest.mark.asyncio
    async def test_sends_pending_message_when_sync_returns_false(self) -> None:
        """The user must receive a 'configs updating' message when sync fails."""
        msg = _make_message()
        session = AsyncMock()
        expires_at = NOW + timedelta(days=30)

        with (
            patch(
                "bot.handlers.payment._get_xui_client",
                new_callable=AsyncMock,
                return_value=AsyncMock(close=AsyncMock()),
            ),
            patch(
                "bot.handlers.payment.sync_configs_expiry",
                new_callable=AsyncMock,
                return_value=False,
            ),
            patch(
                "bot.handlers.payment.SubscriptionRepository",
            ) as mock_repo_cls,
        ):
            mock_repo = mock_repo_cls.return_value
            mock_repo.set_sync_pending = AsyncMock()

            await _sync_after_payment(1, 10, expires_at, session, msg)

        msg.answer.assert_awaited_once()
        text = msg.answer.call_args[0][0]
        assert "конфиги" in text.lower() or "обновляются" in text.lower()

    @pytest.mark.asyncio
    async def test_sets_sync_pending_when_xui_raises(self) -> None:
        """If the XUI client itself raises, the subscription must still be flagged."""
        msg = _make_message()
        session = AsyncMock()
        expires_at = NOW + timedelta(days=30)

        with (
            patch(
                "bot.handlers.payment._get_xui_client",
                new_callable=AsyncMock,
                side_effect=Exception("Panel unreachable"),
            ),
            patch(
                "bot.handlers.payment.SubscriptionRepository",
            ) as mock_repo_cls,
        ):
            mock_repo = mock_repo_cls.return_value
            mock_repo.set_sync_pending = AsyncMock()

            await _sync_after_payment(1, 10, expires_at, session, msg)

        mock_repo.set_sync_pending.assert_awaited_once_with(10, pending=True)
        msg.answer.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_xui_closed_even_when_sync_fails(self) -> None:
        """xui.close() must be called even if sync returns False."""
        msg = _make_message()
        session = AsyncMock()
        expires_at = NOW + timedelta(days=30)

        mock_xui = AsyncMock()
        mock_xui.close = AsyncMock()

        with (
            patch(
                "bot.handlers.payment._get_xui_client",
                new_callable=AsyncMock,
                return_value=mock_xui,
            ),
            patch(
                "bot.handlers.payment.sync_configs_expiry",
                new_callable=AsyncMock,
                return_value=False,
            ),
            patch(
                "bot.handlers.payment.SubscriptionRepository",
            ) as mock_repo_cls,
        ):
            mock_repo = mock_repo_cls.return_value
            mock_repo.set_sync_pending = AsyncMock()

            await _sync_after_payment(1, 10, expires_at, session, msg)

        mock_xui.close.assert_awaited_once()


# ---------------------------------------------------------------------------
# renew_subscription (pay:menu callback)
# ---------------------------------------------------------------------------


class TestRenewSubscription:
    @pytest.mark.asyncio
    async def test_shows_payment_menu(self) -> None:
        """pay:menu callback should show a payment menu message."""
        cb = _make_callback("pay:menu")
        user = _make_user_dto()
        session = AsyncMock()

        with patch(
            "bot.handlers.payment.calculate_ton_nanotons",
            new_callable=AsyncMock,
            return_value=1_000_000_000,
        ):
            await renew_subscription(cb, user, session)

        cb.message.answer.assert_awaited_once()
        text = cb.message.answer.call_args[0][0]
        assert "подписка" in text.lower()
        cb.answer.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_includes_keyboard_in_response(self) -> None:
        """The reply from pay:menu must include an inline keyboard."""
        cb = _make_callback("pay:menu")
        user = _make_user_dto()
        session = AsyncMock()

        with patch(
            "bot.handlers.payment.calculate_ton_nanotons",
            new_callable=AsyncMock,
            return_value=500_000_000,
        ):
            await renew_subscription(cb, user, session)

        call_kwargs = cb.message.answer.call_args[1]
        assert call_kwargs.get("reply_markup") is not None
