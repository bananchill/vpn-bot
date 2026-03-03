"""Payment handler -- Stars and promo code flows."""

from __future__ import annotations

import logging
from datetime import datetime

from aiogram import Bot, F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, LabeledPrice, Message, PreCheckoutQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import settings
from bot.db.repositories.subscription_repo import SubscriptionRepository
from bot.dto import UserDTO
from bot.keyboards.menus import main_menu, payment_menu, promo_cancel_menu
from bot.services.subscription_service import (
    PromoCodeAlreadyUsedError,
    PromoCodeNotFoundError,
    activate,
    activate_promo,
    sync_configs_expiry,
)
from bot.services.xui_client import XUIClient

logger = logging.getLogger(__name__)

router = Router(name="payment")


# ---------------------------------------------------------------------------
# FSM states
# ---------------------------------------------------------------------------


class PaymentStates(StatesGroup):
    """States for promo code input flow."""

    waiting_for_promo = State()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_xui_client() -> XUIClient:
    """Get an authenticated XUI client using credentials from settings."""
    xui = XUIClient(settings.PANEL_URL)
    await xui.login(settings.PANEL_USERNAME, settings.PANEL_PASSWORD)
    return xui


async def _sync_after_payment(
    user_id: int,
    sub_id: int,
    expires_at: datetime,
    session: AsyncSession,
    message: Message,
) -> None:
    """Sync expiryTime on all user configs in 3x-ui after subscription activation.

    If the sync fails, marks the subscription for retry by the scheduler
    and informs the user.
    """
    try:
        xui = await _get_xui_client()
        try:
            success = await sync_configs_expiry(user_id, expires_at, xui, session)
        finally:
            await xui.close()

        if not success:
            sub_repo = SubscriptionRepository(session)
            await sub_repo.set_sync_pending(sub_id, pending=True)
            await message.answer(
                "\u23f3 Конфиги обновляются, "
                "это займёт немного времени."
            )
    except Exception:
        logger.exception(
            "Failed to sync configs after payment for user_id=%s",
            user_id,
        )
        sub_repo = SubscriptionRepository(session)
        await sub_repo.set_sync_pending(sub_id, pending=True)
        await message.answer(
            "\u23f3 Конфиги обновляются, "
            "это займёт немного времени."
        )


async def show_payment_menu(
    callback: CallbackQuery,
    user: UserDTO,
    session: AsyncSession,
) -> None:
    """Show the payment method selection menu.

    Called when a user without an active subscription tries to create a config.
    """
    await callback.message.edit_text(
        "Для создания конфига требуется активная подписка.\n"
        f"Стоимость: {settings.SUBSCRIPTION_PRICE_RUB} \u20bd / "
        f"{settings.SUBSCRIPTION_DAYS} дней.",
        reply_markup=payment_menu(),
    )
    await callback.answer()


async def show_payment_menu_message(
    message: Message,
) -> None:
    """Show the payment method selection menu via Message (reply-keyboard entry)."""
    await message.answer(
        "Для создания конфига требуется активная подписка.\n"
        f"Стоимость: {settings.SUBSCRIPTION_PRICE_RUB} \u20bd / "
        f"{settings.SUBSCRIPTION_DAYS} дней.",
        reply_markup=payment_menu(),
    )


# ---------------------------------------------------------------------------
# Renew subscription (from notification button)
# ---------------------------------------------------------------------------


@router.callback_query(F.data == "pay:menu")
async def renew_subscription(
    callback: CallbackQuery,
    user: UserDTO,
    db_session: AsyncSession,
) -> None:
    """Handle the 'Renew subscription' button from expiry notifications."""
    await callback.message.answer(
        "Для создания конфига требуется активная подписка.\n"
        f"Стоимость: {settings.SUBSCRIPTION_PRICE_RUB} \u20bd / "
        f"{settings.SUBSCRIPTION_DAYS} дней.",
        reply_markup=payment_menu(),
    )
    await callback.answer()


# ---------------------------------------------------------------------------
# Stars payment
# ---------------------------------------------------------------------------


@router.callback_query(F.data == "pay_stars")
async def pay_stars(callback: CallbackQuery, bot: Bot) -> None:
    """Send a Telegram Stars invoice."""
    await bot.send_invoice(
        chat_id=callback.message.chat.id,
        title="VPN подписка",
        description=f"Доступ к VPN на {settings.SUBSCRIPTION_DAYS} дней",
        payload="subscription_stars",
        currency="XTR",
        provider_token="",
        prices=[
            LabeledPrice(
                label=f"VPN {settings.SUBSCRIPTION_DAYS} дней",
                amount=settings.SUBSCRIPTION_STARS,
            ),
        ],
    )
    await callback.answer()


@router.pre_checkout_query(F.invoice_payload == "subscription_stars")
async def pre_checkout_stars(pre_checkout_query: PreCheckoutQuery, bot: Bot) -> None:
    """Approve a Stars pre-checkout query."""
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


@router.message(F.successful_payment.currency == "XTR")
async def successful_payment_stars(
    message: Message,
    user: UserDTO,
    db_session: AsyncSession,
) -> None:
    """Handle successful Stars payment -- activate subscription."""
    sub = await activate(user.id, "stars", db_session)
    expires_str = sub.expires_at.strftime("%d.%m.%Y")
    await message.answer(
        f"Подписка активирована! Действует до {expires_str}.",
        reply_markup=main_menu(),
    )
    await _sync_after_payment(
        user.id, sub.id, sub.expires_at, db_session, message,
    )
    logger.info("Stars payment successful for user_id=%s", user.id)


# ---------------------------------------------------------------------------
# Promo code flow
# ---------------------------------------------------------------------------


@router.callback_query(F.data == "enter_promo")
async def enter_promo(callback: CallbackQuery, state: FSMContext) -> None:
    """Start promo code input FSM."""
    await state.set_state(PaymentStates.waiting_for_promo)
    await callback.message.edit_text(
        "Введите промокод:",
        reply_markup=promo_cancel_menu(),
    )
    await callback.answer()


@router.callback_query(
    F.data == "cancel_promo",
    StateFilter(PaymentStates.waiting_for_promo),
)
async def cancel_promo(callback: CallbackQuery, state: FSMContext) -> None:
    """Cancel promo code input -- return to payment menu."""
    await state.clear()
    await callback.message.edit_text(
        "Для создания конфига требуется активная подписка.\n"
        f"Стоимость: {settings.SUBSCRIPTION_PRICE_RUB} \u20bd / "
        f"{settings.SUBSCRIPTION_DAYS} дней.",
        reply_markup=payment_menu(),
    )
    await callback.answer()


@router.message(PaymentStates.waiting_for_promo, F.text)
async def process_promo(
    message: Message,
    state: FSMContext,
    user: UserDTO,
    db_session: AsyncSession,
) -> None:
    """Validate promo code and activate subscription if valid."""
    code = message.text.strip().lower()

    try:
        sub = await activate_promo(user.id, code, db_session)
    except PromoCodeNotFoundError:
        await message.answer(
            "Промокод не найден или деактивирован. Попробуйте другой:",
            reply_markup=promo_cancel_menu(),
        )
        return
    except PromoCodeAlreadyUsedError:
        await message.answer(
            "Вы уже использовали этот промокод. Попробуйте другой:",
            reply_markup=promo_cancel_menu(),
        )
        return

    await state.clear()
    expires_str = sub.expires_at.strftime("%d.%m.%Y")
    await message.answer(
        f"Промокод принят! Подписка активирована до {expires_str}.",
        reply_markup=main_menu(),
    )
    await _sync_after_payment(
        user.id, sub.id, sub.expires_at, db_session, message,
    )
    logger.info("Promo code '%s' activated for user_id=%s", code, user.id)


@router.message(PaymentStates.waiting_for_promo)
async def promo_not_text(message: Message) -> None:
    """Handle non-text input when expecting promo code."""
    await message.answer(
        "Пожалуйста, отправьте промокод текстовым сообщением.",
        reply_markup=promo_cancel_menu(),
    )
