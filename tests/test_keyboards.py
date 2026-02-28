"""Tests for bot.keyboards.menus."""

from bot.keyboards.menus import config_detail_menu, config_list, confirm_delete, main_menu


class TestMainMenu:
    def test_has_two_buttons(self) -> None:
        kb = main_menu()
        assert len(kb.inline_keyboard) == 2

    def test_create_config_button(self) -> None:
        kb = main_menu()
        btn = kb.inline_keyboard[0][0]
        assert btn.callback_data == "create_config"
        assert "Создать конфиг" in btn.text

    def test_my_configs_button(self) -> None:
        kb = main_menu()
        btn = kb.inline_keyboard[1][0]
        assert btn.callback_data == "my_configs"
        assert "Мои конфиги" in btn.text


class TestConfigList:
    def test_empty_list_has_back_button(self) -> None:
        kb = config_list([])
        assert len(kb.inline_keyboard) == 1
        assert kb.inline_keyboard[0][0].callback_data == "back_to_main"

    def test_shows_config_buttons(self) -> None:
        items = [(1, "config-1"), (2, "config-2")]
        kb = config_list(items)
        # 2 config buttons + 1 back button
        assert len(kb.inline_keyboard) == 3
        assert kb.inline_keyboard[0][0].text == "config-1"
        assert kb.inline_keyboard[0][0].callback_data == "config:1:detail"
        assert kb.inline_keyboard[1][0].text == "config-2"
        assert kb.inline_keyboard[1][0].callback_data == "config:2:detail"


class TestConfigDetailMenu:
    def test_has_action_buttons(self) -> None:
        kb = config_detail_menu(42)
        # 3 rows: [traffic, refresh], [link, delete], [back]
        assert len(kb.inline_keyboard) == 3

    def test_traffic_button(self) -> None:
        kb = config_detail_menu(42)
        btn = kb.inline_keyboard[0][0]
        assert btn.callback_data == "config:42:traffic"

    def test_refresh_button(self) -> None:
        kb = config_detail_menu(42)
        btn = kb.inline_keyboard[0][1]
        assert btn.callback_data == "config:42:refresh"

    def test_link_button(self) -> None:
        kb = config_detail_menu(42)
        btn = kb.inline_keyboard[1][0]
        assert btn.callback_data == "config:42:link"

    def test_delete_button(self) -> None:
        kb = config_detail_menu(42)
        btn = kb.inline_keyboard[1][1]
        assert btn.callback_data == "config:42:delete"

    def test_back_button(self) -> None:
        kb = config_detail_menu(42)
        btn = kb.inline_keyboard[2][0]
        assert btn.callback_data == "my_configs"


class TestConfirmDelete:
    def test_has_two_buttons(self) -> None:
        kb = confirm_delete(5)
        assert len(kb.inline_keyboard) == 1
        assert len(kb.inline_keyboard[0]) == 2

    def test_confirm_button(self) -> None:
        kb = confirm_delete(5)
        btn = kb.inline_keyboard[0][0]
        assert btn.callback_data == "config:5:confirm_delete"
        assert "Да, удалить" in btn.text

    def test_cancel_button(self) -> None:
        kb = confirm_delete(5)
        btn = kb.inline_keyboard[0][1]
        assert btn.callback_data == "config:5:detail"
        assert "Отмена" in btn.text
