"""Inline keyboard builders for bot menus."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

SUPPORT_URL = "https://t.me/help_chat_b"


def main_menu() -> InlineKeyboardMarkup:
    """Main menu shown after /start for regular users."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="\U0001f511 Создать конфиг", callback_data="create_config")],
            [InlineKeyboardButton(text="\U0001f4cb Мои конфиги", callback_data="my_configs")],
            [InlineKeyboardButton(text="\U0001f4ac Поддержка", url=SUPPORT_URL)],
        ]
    )


def config_list(configs: list[tuple[int, str]]) -> InlineKeyboardMarkup:
    """List of user configs as inline buttons.

    Args:
        configs: List of (config_id, email) tuples.
    """
    buttons = [
        [InlineKeyboardButton(text=email, callback_data=f"config:{config_id}:detail")]
        for config_id, email in configs
    ]
    buttons.append(
        [InlineKeyboardButton(text="\U00002b05 Назад", callback_data="back_to_main")]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def config_detail_menu(config_id: int) -> InlineKeyboardMarkup:
    """Detail menu for a single config."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="\U0001f4ca Трафик",
                    callback_data=f"config:{config_id}:traffic",
                ),
                InlineKeyboardButton(
                    text="\U0001f504 Обновить конфиг",
                    callback_data=f"config:{config_id}:refresh",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="\U0001f4ce Получить ссылку",
                    callback_data=f"config:{config_id}:link",
                ),
                InlineKeyboardButton(
                    text="\U0001f5d1 Удалить конфиг",
                    callback_data=f"config:{config_id}:delete",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="\U00002b05 Назад к списку",
                    callback_data="my_configs",
                ),
            ],
        ]
    )


def cancel_config_creation() -> InlineKeyboardMarkup:
    """Single 'Cancel' button shown during config name input FSM state."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="\U00002716 Отмена",
                    callback_data="cancel_config_creation",
                ),
            ],
        ]
    )


def confirm_delete(config_id: int) -> InlineKeyboardMarkup:
    """Confirmation dialog for config deletion."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Да, удалить",
                    callback_data=f"config:{config_id}:confirm_delete",
                ),
                InlineKeyboardButton(
                    text="Отмена",
                    callback_data=f"config:{config_id}:detail",
                ),
            ],
        ]
    )


def payment_menu() -> InlineKeyboardMarkup:
    """Payment method selection menu."""
    from bot.config import settings

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"\u2b50 Оплатить Stars ({settings.SUBSCRIPTION_STARS})",
                    callback_data="pay_stars",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="\U0001f39f У меня есть промокод",
                    callback_data="enter_promo",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="\u2b05 Назад",
                    callback_data="back_to_main",
                ),
            ],
        ]
    )


def promo_cancel_menu() -> InlineKeyboardMarkup:
    """Single cancel button shown during promo code input FSM state."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="\u2716 Отмена",
                    callback_data="cancel_promo",
                ),
            ],
        ]
    )


def renew_button() -> InlineKeyboardMarkup:
    """Single 'Renew subscription' button used in expiry notifications."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="\U0001f504 Продлить подписку",
                    callback_data="pay:menu",
                ),
            ],
        ]
    )
