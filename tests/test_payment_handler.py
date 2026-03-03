"""Tests for bot.handlers.payment -- payment flow handlers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, Chat, Message, PreCheckoutQuery, User

from bot.dto import SubscriptionDTO, UserDTO
from bot.handlers.payment import (
    PaymentStates,
    cancel_promo,
    enter_promo,
    pay_stars,
    pay_ton,
    pay_ton_unavailable,
    pre_checkout_stars,
    pre_checkout_ton,
    process_promo,
    promo_not_text,
    show_payment_menu,
    show_payment_menu_message,
    successful_payment_stars,
    successful_payment_ton,
)
from bot.services.ton_price_service import TonPriceUnavailableError

NOW = datetime.now(tz=UTC)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_callback(data: str, user_id: int = 123456) -> MagicMock:
    cb = MagicMock(spec=CallbackQuery)
    cb.data = data
    cb.from_user = MagicMock(spec=User)
    cb.from_user.id = user_id
    cb.message = MagicMock()
    cb.message.chat = MagicMock(spec=Chat)
    cb.message.chat.id = user_id
    cb.message.edit_text = AsyncMock()
    cb.answer = AsyncMock()
    return cb


def _make_message(text: str | None = None, user_id: int = 123456) -> MagicMock:
    msg = MagicMock(spec=Message)
    msg.text = text
    msg.chat = MagicMock(spec=Chat)
    msg.chat.id = user_id
    msg.message_id = 42
    msg.from_user = MagicMock(spec=User)
    msg.from_user.id = user_id
    msg.answer = AsyncMock()
    return msg


def _make_state() -> FSMContext:
    storage = MemoryStorage()
    key = StorageKey(bot_id=1, chat_id=123456, user_id=123456)
    return FSMContext(storage=storage, key=key)


def _make_user_dto(user_id: int = 1) -> UserDTO:
    return UserDTO(
        id=user_id,
        telegram_id=123456,
        username="testuser",
        is_admin=False,
        created_at=NOW,
    )


def _make_sub_dto(source: str = "stars") -> SubscriptionDTO:
    return SubscriptionDTO(
        id=1,
        user_id=1,
        started_at=NOW,
        expires_at=NOW + timedelta(days=30),
        source=source,
        promo_code=None,
        created_at=NOW,
    )


# ---------------------------------------------------------------------------
# show_payment_menu
# ---------------------------------------------------------------------------


class TestShowPaymentMenu:
    @pytest.mark.asyncio
    async def test_shows_menu_with_ton_available(self) -> None:
        cb = _make_callback("create_config")
        user = _make_user_dto()
        session = AsyncMock()

        with patch(
            "bot.handlers.payment.calculate_ton_nanotons",
            new_callable=AsyncMock,
            return_value=1_000_000_000,
        ):
            await show_payment_menu(cb, user, session)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "подписка" in text.lower()
        cb.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_shows_menu_with_ton_unavailable(self) -> None:
        cb = _make_callback("create_config")
        user = _make_user_dto()
        session = AsyncMock()

        with patch(
            "bot.handlers.payment.calculate_ton_nanotons",
            new_callable=AsyncMock,
            side_effect=TonPriceUnavailableError("test"),
        ):
            await show_payment_menu(cb, user, session)

        cb.message.edit_text.assert_called_once()
        # Keyboard should still be present (with disabled TON button)
        call_kwargs = cb.message.edit_text.call_args[1]
        assert call_kwargs.get("reply_markup") is not None


# ---------------------------------------------------------------------------
# Stars payment
# ---------------------------------------------------------------------------


class TestShowPaymentMenuMessage:
    @pytest.mark.asyncio
    async def test_sends_message_with_ton_available(self) -> None:
        msg = _make_message()

        with patch(
            "bot.handlers.payment.calculate_ton_nanotons",
            new_callable=AsyncMock,
            return_value=666_666_667,
        ):
            await show_payment_menu_message(msg)

        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "подписка" in text.lower()
        call_kwargs = msg.answer.call_args[1]
        assert call_kwargs.get("reply_markup") is not None

    @pytest.mark.asyncio
    async def test_sends_message_with_ton_unavailable(self) -> None:
        msg = _make_message()

        with patch(
            "bot.handlers.payment.calculate_ton_nanotons",
            new_callable=AsyncMock,
            side_effect=TonPriceUnavailableError("test"),
        ):
            await show_payment_menu_message(msg)

        msg.answer.assert_called_once()
        # Keyboard with disabled TON button should be present
        call_kwargs = msg.answer.call_args[1]
        assert call_kwargs.get("reply_markup") is not None


class TestPayStars:
    @pytest.mark.asyncio
    async def test_sends_stars_invoice(self) -> None:
        cb = _make_callback("pay_stars")
        bot = AsyncMock()

        await pay_stars(cb, bot)

        bot.send_invoice.assert_called_once()
        call_kwargs = bot.send_invoice.call_args[1]
        assert call_kwargs["currency"] == "XTR"
        assert call_kwargs["provider_token"] == ""
        assert call_kwargs["payload"] == "subscription_stars"
        cb.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_stars_invoice_amount_is_120(self) -> None:
        """Invoice amount must be exactly 120 (SUBSCRIPTION_STARS)."""
        from bot.config import settings

        cb = _make_callback("pay_stars")
        bot = AsyncMock()

        await pay_stars(cb, bot)

        call_kwargs = bot.send_invoice.call_args[1]
        prices = call_kwargs["prices"]
        assert len(prices) == 1
        assert prices[0].amount == settings.SUBSCRIPTION_STARS


class TestPreCheckout:
    @pytest.mark.asyncio
    async def test_pre_checkout_stars_approves(self) -> None:
        pcq = MagicMock(spec=PreCheckoutQuery)
        pcq.id = "pcq_stars_id"
        bot = AsyncMock()

        await pre_checkout_stars(pcq, bot)

        bot.answer_pre_checkout_query.assert_called_once_with("pcq_stars_id", ok=True)

    @pytest.mark.asyncio
    async def test_pre_checkout_ton_approves(self) -> None:
        pcq = MagicMock(spec=PreCheckoutQuery)
        pcq.id = "pcq_ton_id"
        bot = AsyncMock()

        await pre_checkout_ton(pcq, bot)

        bot.answer_pre_checkout_query.assert_called_once_with("pcq_ton_id", ok=True)


class TestSuccessfulPaymentStars:
    @pytest.mark.asyncio
    async def test_activates_subscription(self) -> None:
        msg = _make_message()
        user = _make_user_dto()
        session = AsyncMock()
        sub = _make_sub_dto(source="stars")

        with (
            patch(
                "bot.handlers.payment.activate",
                new_callable=AsyncMock,
                return_value=sub,
            ) as mock_activate,
            patch(
                "bot.handlers.payment._sync_after_payment",
                new_callable=AsyncMock,
            ),
        ):
            await successful_payment_stars(msg, user, session)

        mock_activate.assert_called_once_with(user.id, "stars", session)
        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "активирована" in text.lower()


# ---------------------------------------------------------------------------
# TON payment
# ---------------------------------------------------------------------------


class TestPayTon:
    @pytest.mark.asyncio
    async def test_sends_ton_invoice(self) -> None:
        cb = _make_callback("pay_ton")
        bot = AsyncMock()

        with patch(
            "bot.handlers.payment.calculate_ton_nanotons",
            new_callable=AsyncMock,
            return_value=666_666_667,
        ):
            await pay_ton(cb, bot)

        bot.send_invoice.assert_called_once()
        call_kwargs = bot.send_invoice.call_args[1]
        assert call_kwargs["currency"] == "TON"
        assert call_kwargs["payload"] == "subscription_ton"

    @pytest.mark.asyncio
    async def test_shows_alert_when_unavailable(self) -> None:
        cb = _make_callback("pay_ton")
        bot = AsyncMock()

        with patch(
            "bot.handlers.payment.calculate_ton_nanotons",
            new_callable=AsyncMock,
            side_effect=TonPriceUnavailableError("test"),
        ):
            await pay_ton(cb, bot)

        cb.answer.assert_called_once()
        assert cb.answer.call_args[1].get("show_alert") is True
        bot.send_invoice.assert_not_called()


class TestPayTonUnavailable:
    @pytest.mark.asyncio
    async def test_shows_alert(self) -> None:
        cb = _make_callback("pay_ton_unavailable")

        await pay_ton_unavailable(cb)

        cb.answer.assert_called_once()
        assert cb.answer.call_args[1].get("show_alert") is True


class TestSuccessfulPaymentTon:
    @pytest.mark.asyncio
    async def test_activates_subscription(self) -> None:
        msg = _make_message()
        user = _make_user_dto()
        session = AsyncMock()
        sub = _make_sub_dto(source="ton")

        with (
            patch(
                "bot.handlers.payment.activate",
                new_callable=AsyncMock,
                return_value=sub,
            ) as mock_activate,
            patch(
                "bot.handlers.payment._sync_after_payment",
                new_callable=AsyncMock,
            ),
        ):
            await successful_payment_ton(msg, user, session)

        mock_activate.assert_called_once_with(user.id, "ton", session)


# ---------------------------------------------------------------------------
# Promo code flow
# ---------------------------------------------------------------------------


class TestEnterPromo:
    @pytest.mark.asyncio
    async def test_sets_fsm_state(self) -> None:
        cb = _make_callback("enter_promo")
        state = _make_state()

        await enter_promo(cb, state)

        current = await state.get_state()
        assert current == PaymentStates.waiting_for_promo
        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "промокод" in text.lower()


class TestCancelPromo:
    @pytest.mark.asyncio
    async def test_clears_state_and_shows_payment_menu(self) -> None:
        cb = _make_callback("cancel_promo")
        state = _make_state()
        await state.set_state(PaymentStates.waiting_for_promo)

        with patch(
            "bot.handlers.payment.calculate_ton_nanotons",
            new_callable=AsyncMock,
            return_value=1_000_000_000,
        ):
            await cancel_promo(cb, state)

        current = await state.get_state()
        assert current is None
        cb.message.edit_text.assert_called_once()


class TestProcessPromo:
    @pytest.mark.asyncio
    async def test_valid_promo_activates_subscription(self) -> None:
        msg = _make_message("TESTCODE")
        state = _make_state()
        await state.set_state(PaymentStates.waiting_for_promo)
        user = _make_user_dto()
        session = AsyncMock()
        sub = _make_sub_dto(source="promo")

        with (
            patch(
                "bot.handlers.payment.activate_promo",
                new_callable=AsyncMock,
                return_value=sub,
            ),
            patch(
                "bot.handlers.payment._sync_after_payment",
                new_callable=AsyncMock,
            ),
        ):
            await process_promo(msg, state, user, session)

        current = await state.get_state()
        assert current is None
        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "принят" in text.lower()

    @pytest.mark.asyncio
    async def test_not_found_promo_shows_error(self) -> None:
        from bot.services.subscription_service import PromoCodeNotFoundError

        msg = _make_message("BADCODE")
        state = _make_state()
        await state.set_state(PaymentStates.waiting_for_promo)
        user = _make_user_dto()
        session = AsyncMock()

        with patch(
            "bot.handlers.payment.activate_promo",
            new_callable=AsyncMock,
            side_effect=PromoCodeNotFoundError("test"),
        ):
            await process_promo(msg, state, user, session)

        # FSM should stay in waiting state
        current = await state.get_state()
        assert current == PaymentStates.waiting_for_promo
        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "не найден" in text.lower()

    @pytest.mark.asyncio
    async def test_already_used_promo_shows_error(self) -> None:
        from bot.services.subscription_service import PromoCodeAlreadyUsedError

        msg = _make_message("USEDCODE")
        state = _make_state()
        await state.set_state(PaymentStates.waiting_for_promo)
        user = _make_user_dto()
        session = AsyncMock()

        with patch(
            "bot.handlers.payment.activate_promo",
            new_callable=AsyncMock,
            side_effect=PromoCodeAlreadyUsedError("test"),
        ):
            await process_promo(msg, state, user, session)

        current = await state.get_state()
        assert current == PaymentStates.waiting_for_promo
        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "уже использовали" in text.lower()


class TestPromoNotText:
    @pytest.mark.asyncio
    async def test_rejects_non_text(self) -> None:
        msg = _make_message(None)
        await promo_not_text(msg)
        msg.answer.assert_called_once()
        assert "текстовым" in msg.answer.call_args[0][0].lower()
