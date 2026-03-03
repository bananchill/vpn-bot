"""Tests for bot.services.notification_service -- expiry notifications and sync retry."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bot.services.notification_service import (
    _notify_expired,
    _notify_expiring_soon,
    _retry_pending_sync,
    check_and_notify_expiring,
)

NOW = datetime(2026, 3, 2, 12, 0, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_sub_orm(
    sub_id: int = 1,
    user_id: int = 100,
    telegram_id: int = 555555,
    expires_at: datetime | None = None,
    notified_3d: bool = False,
    notified_expired: bool = False,
    configs_sync_pending: bool = False,
) -> MagicMock:
    """Build a mock ORM Subscription with related User loaded."""
    sub = MagicMock()
    sub.id = sub_id
    sub.user_id = user_id
    sub.expires_at = expires_at or (NOW + timedelta(days=3))
    sub.notified_3d = notified_3d
    sub.notified_expired = notified_expired
    sub.configs_sync_pending = configs_sync_pending

    user = MagicMock()
    user.telegram_id = telegram_id
    sub.user = user

    return sub


# ---------------------------------------------------------------------------
# check_and_notify_expiring — integration (session-level)
# ---------------------------------------------------------------------------


class TestCheckAndNotifyExpiring:
    @pytest.mark.asyncio
    async def test_opens_session_and_calls_all_helpers(self) -> None:
        """The public entry point must open a session and delegate to all three helpers."""
        bot = AsyncMock()

        # Build a mock session_factory that returns an async context manager
        session = AsyncMock()
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=False)
        session.begin = MagicMock()
        session.begin.return_value.__aenter__ = AsyncMock(return_value=None)
        session.begin.return_value.__aexit__ = AsyncMock(return_value=False)

        session_factory = MagicMock(return_value=session)

        with (
            patch(
                "bot.services.notification_service._notify_expiring_soon",
                new_callable=AsyncMock,
            ) as mock_soon,
            patch(
                "bot.services.notification_service._notify_expired",
                new_callable=AsyncMock,
            ) as mock_expired,
            patch(
                "bot.services.notification_service._retry_pending_sync",
                new_callable=AsyncMock,
            ) as mock_retry,
        ):
            await check_and_notify_expiring(bot, session_factory)

        mock_soon.assert_awaited_once()
        mock_expired.assert_awaited_once()
        mock_retry.assert_awaited_once()


# ---------------------------------------------------------------------------
# _notify_expiring_soon
# ---------------------------------------------------------------------------


class TestNotifyExpiringSoon:
    @pytest.mark.asyncio
    async def test_sends_message_and_marks_flag(self) -> None:
        """For each expiring subscription, send a message and mark notified_3d=True."""
        bot = AsyncMock()
        sub = _make_sub_orm(sub_id=1, telegram_id=111111)

        sub_repo = AsyncMock()
        sub_repo.get_expiring_soon = AsyncMock(return_value=[sub])
        sub_repo.mark_notified_3d = AsyncMock()

        await _notify_expiring_soon(bot, sub_repo, NOW)

        bot.send_message.assert_awaited_once()
        call_args = bot.send_message.call_args
        assert call_args[0][0] == 111111
        text = call_args[0][1]
        assert "истекает" in text.lower()
        # Keyboard should be present
        assert call_args[1].get("reply_markup") is not None
        sub_repo.mark_notified_3d.assert_awaited_once_with(1)

    @pytest.mark.asyncio
    async def test_uses_71h_to_73h_window(self) -> None:
        """The query window must be [now+71h, now+73h]."""
        bot = AsyncMock()
        sub_repo = AsyncMock()
        sub_repo.get_expiring_soon = AsyncMock(return_value=[])

        await _notify_expiring_soon(bot, sub_repo, NOW)

        call_kwargs = sub_repo.get_expiring_soon.call_args[1]
        window_start = call_kwargs.get("window_start") or sub_repo.get_expiring_soon.call_args[0][0]
        window_end = call_kwargs.get("window_end") or sub_repo.get_expiring_soon.call_args[0][1]

        expected_start = NOW + timedelta(hours=71)
        expected_end = NOW + timedelta(hours=73)
        assert window_start == expected_start
        assert window_end == expected_end

    @pytest.mark.asyncio
    async def test_no_message_when_no_expiring_subs(self) -> None:
        """When the query returns no subscriptions, no messages should be sent."""
        bot = AsyncMock()
        sub_repo = AsyncMock()
        sub_repo.get_expiring_soon = AsyncMock(return_value=[])

        await _notify_expiring_soon(bot, sub_repo, NOW)

        bot.send_message.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_continues_after_send_error(self) -> None:
        """If bot.send_message raises, the loop continues to the next subscription."""
        bot = AsyncMock()
        bot.send_message = AsyncMock(side_effect=Exception("Bot blocked"))

        sub1 = _make_sub_orm(sub_id=1, telegram_id=111111)
        sub2 = _make_sub_orm(sub_id=2, telegram_id=222222)

        sub_repo = AsyncMock()
        sub_repo.get_expiring_soon = AsyncMock(return_value=[sub1, sub2])
        sub_repo.mark_notified_3d = AsyncMock()

        # Should not raise
        await _notify_expiring_soon(bot, sub_repo, NOW)

        # Neither subscription should be marked (send failed before mark)
        sub_repo.mark_notified_3d.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_message_contains_expiry_date(self) -> None:
        """The notification text must contain the formatted expiry date."""
        bot = AsyncMock()
        expires = datetime(2026, 4, 1, tzinfo=UTC)
        sub = _make_sub_orm(sub_id=1, telegram_id=111111, expires_at=expires)

        sub_repo = AsyncMock()
        sub_repo.get_expiring_soon = AsyncMock(return_value=[sub])
        sub_repo.mark_notified_3d = AsyncMock()

        await _notify_expiring_soon(bot, sub_repo, NOW)

        text = bot.send_message.call_args[0][1]
        assert "01.04.2026" in text

    @pytest.mark.asyncio
    async def test_multiple_subs_all_notified(self) -> None:
        """All returned subscriptions must be notified, not just the first."""
        bot = AsyncMock()
        subs = [_make_sub_orm(sub_id=i, telegram_id=100000 + i) for i in range(1, 4)]

        sub_repo = AsyncMock()
        sub_repo.get_expiring_soon = AsyncMock(return_value=subs)
        sub_repo.mark_notified_3d = AsyncMock()

        await _notify_expiring_soon(bot, sub_repo, NOW)

        assert bot.send_message.await_count == 3
        assert sub_repo.mark_notified_3d.await_count == 3


# ---------------------------------------------------------------------------
# _notify_expired
# ---------------------------------------------------------------------------


class TestNotifyExpired:
    @pytest.mark.asyncio
    async def test_sends_expired_message_and_marks_flag(self) -> None:
        """Expired subs receive the expiry notification and notified_expired is set."""
        bot = AsyncMock()
        sub = _make_sub_orm(sub_id=10, telegram_id=777777)

        sub_repo = AsyncMock()
        sub_repo.get_expired_unnotified = AsyncMock(return_value=[sub])
        sub_repo.mark_notified_expired = AsyncMock()

        await _notify_expired(bot, sub_repo, NOW)

        bot.send_message.assert_awaited_once()
        call_args = bot.send_message.call_args
        assert call_args[0][0] == 777777
        text = call_args[0][1]
        assert "истекла" in text.lower()
        assert call_args[1].get("reply_markup") is not None
        sub_repo.mark_notified_expired.assert_awaited_once_with(10)

    @pytest.mark.asyncio
    async def test_no_message_when_no_expired_subs(self) -> None:
        bot = AsyncMock()
        sub_repo = AsyncMock()
        sub_repo.get_expired_unnotified = AsyncMock(return_value=[])

        await _notify_expired(bot, sub_repo, NOW)

        bot.send_message.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_continues_after_send_error(self) -> None:
        """If bot.send_message raises for one sub, next sub is still processed."""
        bot = AsyncMock()
        bot.send_message = AsyncMock(side_effect=Exception("User blocked bot"))

        sub1 = _make_sub_orm(sub_id=10, telegram_id=100001)
        sub2 = _make_sub_orm(sub_id=11, telegram_id=100002)

        sub_repo = AsyncMock()
        sub_repo.get_expired_unnotified = AsyncMock(return_value=[sub1, sub2])
        sub_repo.mark_notified_expired = AsyncMock()

        await _notify_expired(bot, sub_repo, NOW)

        # send_message was attempted twice despite error on first
        assert bot.send_message.await_count == 2
        # neither marked because exception happens before mark call
        sub_repo.mark_notified_expired.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_deduplicated_by_flag(self) -> None:
        """Calling the helper twice returns no new notifications — flag prevents repeats.

        This is simulated by having the repo return empty on second call.
        """
        bot = AsyncMock()
        sub = _make_sub_orm(sub_id=20)

        sub_repo = AsyncMock()
        # First call: returns expired sub; second call: already marked, returns empty
        sub_repo.get_expired_unnotified = AsyncMock(side_effect=[[sub], []])
        sub_repo.mark_notified_expired = AsyncMock()

        await _notify_expired(bot, sub_repo, NOW)
        await _notify_expired(bot, sub_repo, NOW)

        # Only one message sent total
        assert bot.send_message.await_count == 1


# ---------------------------------------------------------------------------
# _retry_pending_sync
# ---------------------------------------------------------------------------


class TestRetryPendingSync:
    @pytest.mark.asyncio
    async def test_clears_flag_on_success(self) -> None:
        """When sync succeeds, configs_sync_pending should be set to False."""
        sub = _make_sub_orm(sub_id=5, configs_sync_pending=True)
        sub.expires_at = NOW + timedelta(days=30)

        sub_repo = AsyncMock()
        sub_repo.get_pending_sync = AsyncMock(return_value=[sub])
        sub_repo.set_sync_pending = AsyncMock()

        session = AsyncMock()

        with (
            patch(
                "bot.services.notification_service.XUIClient",
            ) as mock_xui_cls,
            patch(
                "bot.services.notification_service.subscription_service.sync_configs_expiry",
                new_callable=AsyncMock,
                return_value=True,
            ),
        ):
            mock_xui = AsyncMock()
            mock_xui.login = AsyncMock()
            mock_xui.close = AsyncMock()
            mock_xui_cls.return_value = mock_xui

            await _retry_pending_sync(sub_repo, session)

        sub_repo.set_sync_pending.assert_awaited_once_with(5, pending=False)

    @pytest.mark.asyncio
    async def test_keeps_flag_when_sync_fails(self) -> None:
        """When sync returns False, the pending flag must NOT be cleared."""
        sub = _make_sub_orm(sub_id=6, configs_sync_pending=True)
        sub.expires_at = NOW + timedelta(days=30)

        sub_repo = AsyncMock()
        sub_repo.get_pending_sync = AsyncMock(return_value=[sub])
        sub_repo.set_sync_pending = AsyncMock()

        session = AsyncMock()

        with (
            patch(
                "bot.services.notification_service.XUIClient",
            ) as mock_xui_cls,
            patch(
                "bot.services.notification_service.subscription_service.sync_configs_expiry",
                new_callable=AsyncMock,
                return_value=False,
            ),
        ):
            mock_xui = AsyncMock()
            mock_xui.login = AsyncMock()
            mock_xui.close = AsyncMock()
            mock_xui_cls.return_value = mock_xui

            await _retry_pending_sync(sub_repo, session)

        sub_repo.set_sync_pending.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_continues_after_xui_exception(self) -> None:
        """If XUIClient raises, the loop must not abort remaining subscriptions."""
        sub1 = _make_sub_orm(sub_id=7, configs_sync_pending=True)
        sub2 = _make_sub_orm(sub_id=8, configs_sync_pending=True)
        sub1.expires_at = NOW + timedelta(days=10)
        sub2.expires_at = NOW + timedelta(days=10)

        sub_repo = AsyncMock()
        sub_repo.get_pending_sync = AsyncMock(return_value=[sub1, sub2])
        sub_repo.set_sync_pending = AsyncMock()

        session = AsyncMock()

        with patch(
            "bot.services.notification_service.XUIClient",
            side_effect=Exception("Connection refused"),
        ):
            # Should not raise
            await _retry_pending_sync(sub_repo, session)

        sub_repo.set_sync_pending.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_no_action_when_no_pending(self) -> None:
        """Nothing should happen when there are no pending subscriptions."""
        sub_repo = AsyncMock()
        sub_repo.get_pending_sync = AsyncMock(return_value=[])
        sub_repo.set_sync_pending = AsyncMock()

        session = AsyncMock()

        await _retry_pending_sync(sub_repo, session)

        sub_repo.set_sync_pending.assert_not_awaited()
