"""Reply keyboard builders for persistent bottom-panel navigation."""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

# Button text constants — single source of truth for matching in handlers
BTN_CREATE_CONFIG = "Создать конфиг"
BTN_MY_CONFIGS = "Мои конфиги"


def reply_main_menu() -> ReplyKeyboardMarkup:
    """Persistent reply keyboard shown under the text input field.

    Contains two buttons mirroring the inline main menu actions.
    Uses resize_keyboard for compact display and persistent to keep
    the keyboard visible after button presses.
    """
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=BTN_CREATE_CONFIG),
                KeyboardButton(text=BTN_MY_CONFIGS),
            ],
        ],
        resize_keyboard=True,
        persistent=True,
    )
