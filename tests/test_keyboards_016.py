"""Tests for TASK-016 keyboard additions: renew_button."""

from bot.keyboards.menus import renew_button


class TestRenewButton:
    def test_has_single_button(self) -> None:
        kb = renew_button()
        assert len(kb.inline_keyboard) == 1
        assert len(kb.inline_keyboard[0]) == 1

    def test_callback_data_is_pay_menu(self) -> None:
        """The renew button must route to pay:menu callback."""
        kb = renew_button()
        btn = kb.inline_keyboard[0][0]
        assert btn.callback_data == "pay:menu"

    def test_button_text_contains_prodlit(self) -> None:
        """Button text must mention renewal (Продлить)."""
        kb = renew_button()
        btn = kb.inline_keyboard[0][0]
        assert "Продлить" in btn.text
