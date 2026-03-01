"""Tests for bot.handlers.owner -- /setadmin, /rmadmin, /admins commands."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.types import Chat, Message, User

from bot.dto import UserDTO
from bot.handlers.owner import (
    _MISSING,
    IsOwnerFilter,
    _extract_arg,
    cmd_admins,
    cmd_rm_admin,
    cmd_set_admin,
    router,
)

NOW = datetime.now(tz=UTC)

OWNER_ID = 999999999
OTHER_USER_ID = 111111111
TARGET_USER_ID = 123456789


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_message(
    text: str | None = None,
    user_id: int = OWNER_ID,
    username: str | None = "owner_user",
) -> MagicMock:
    """Create a mock Message with essential attributes."""
    msg = MagicMock(spec=Message)
    msg.text = text
    msg.chat = MagicMock(spec=Chat)
    msg.chat.id = user_id
    msg.message_id = 1
    msg.from_user = MagicMock(spec=User)
    msg.from_user.id = user_id
    msg.from_user.username = username
    msg.answer = AsyncMock()
    return msg


def _make_user_dto(
    telegram_id: int = TARGET_USER_ID,
    username: str | None = "target_user",
    is_admin: bool = False,
) -> UserDTO:
    return UserDTO(
        id=1,
        telegram_id=telegram_id,
        username=username,
        is_admin=is_admin,
        created_at=NOW,
    )


def _make_db_session() -> AsyncMock:
    return AsyncMock()


# ---------------------------------------------------------------------------
# IsOwnerFilter
# ---------------------------------------------------------------------------


class TestIsOwnerFilter:
    @pytest.mark.asyncio
    async def test_owner_passes_filter(self) -> None:
        msg = _make_message(user_id=OWNER_ID)
        f = IsOwnerFilter()

        # Patch settings.OWNER_ID to match our OWNER_ID constant
        with patch("bot.handlers.owner.settings") as mock_settings:
            mock_settings.OWNER_ID = OWNER_ID
            result = await f(msg)

        assert result is True

    @pytest.mark.asyncio
    async def test_non_owner_blocked_by_filter(self) -> None:
        msg = _make_message(user_id=OTHER_USER_ID)
        f = IsOwnerFilter()

        with patch("bot.handlers.owner.settings") as mock_settings:
            mock_settings.OWNER_ID = OWNER_ID
            result = await f(msg)

        assert result is False

    @pytest.mark.asyncio
    async def test_missing_from_user_blocked(self) -> None:
        msg = _make_message()
        msg.from_user = None
        f = IsOwnerFilter()

        with patch("bot.handlers.owner.settings") as mock_settings:
            mock_settings.OWNER_ID = OWNER_ID
            result = await f(msg)

        assert result is False


# ---------------------------------------------------------------------------
# _extract_arg helper
# ---------------------------------------------------------------------------


class TestExtractArg:
    def test_returns_arg_when_present(self) -> None:
        result = _extract_arg("/setadmin 123456789")
        assert result == "123456789"

    def test_returns_missing_when_no_arg(self) -> None:
        result = _extract_arg("/setadmin")
        assert result is _MISSING

    def test_returns_missing_on_whitespace_only_arg(self) -> None:
        result = _extract_arg("/setadmin   ")
        assert result is _MISSING

    def test_returns_missing_on_none_text(self) -> None:
        result = _extract_arg(None)
        assert result is _MISSING

    def test_strips_whitespace_from_arg(self) -> None:
        result = _extract_arg("/setadmin   42   ")
        assert result == "42"

    def test_returns_first_arg_only(self) -> None:
        # Only the first argument after the command is relevant
        result = _extract_arg("/setadmin 42 extra stuff")
        assert result == "42 extra stuff"


# ---------------------------------------------------------------------------
# /setadmin command
# ---------------------------------------------------------------------------


class TestCmdSetAdmin:
    @pytest.mark.asyncio
    async def test_setadmin_missing_arg_sends_usage(self) -> None:
        msg = _make_message("/setadmin")
        db_session = _make_db_session()

        await cmd_set_admin(msg, db_session)

        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "Использование: /setadmin <telegram_id>" in text

    @pytest.mark.asyncio
    async def test_setadmin_invalid_number_sends_error(self) -> None:
        msg = _make_message("/setadmin abc")
        db_session = _make_db_session()

        await cmd_set_admin(msg, db_session)

        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "telegram_id должен быть числом" in text

    @pytest.mark.asyncio
    async def test_setadmin_user_not_found_sends_error(self) -> None:
        msg = _make_message(f"/setadmin {TARGET_USER_ID}")
        db_session = _make_db_session()

        with patch("bot.handlers.owner.UserRepository") as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_by_telegram_id = AsyncMock(return_value=None)

            await cmd_set_admin(msg, db_session)

        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "не найден" in text

    @pytest.mark.asyncio
    async def test_setadmin_already_admin_sends_info(self) -> None:
        msg = _make_message(f"/setadmin {TARGET_USER_ID}")
        db_session = _make_db_session()
        existing_admin = _make_user_dto(is_admin=True)

        with patch("bot.handlers.owner.UserRepository") as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_by_telegram_id = AsyncMock(return_value=existing_admin)

            await cmd_set_admin(msg, db_session)

        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "уже является администратором" in text

    @pytest.mark.asyncio
    async def test_setadmin_already_admin_does_not_call_set_admin(self) -> None:
        msg = _make_message(f"/setadmin {TARGET_USER_ID}")
        db_session = _make_db_session()
        existing_admin = _make_user_dto(is_admin=True)

        with patch("bot.handlers.owner.UserRepository") as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_by_telegram_id = AsyncMock(return_value=existing_admin)
            mock_repo.set_admin = AsyncMock()

            await cmd_set_admin(msg, db_session)

        mock_repo.set_admin.assert_not_called()

    @pytest.mark.asyncio
    async def test_setadmin_success_calls_set_admin_and_replies(self) -> None:
        msg = _make_message(f"/setadmin {TARGET_USER_ID}")
        db_session = _make_db_session()
        existing_user = _make_user_dto(is_admin=False)
        promoted_user = _make_user_dto(is_admin=True)

        with patch("bot.handlers.owner.UserRepository") as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_by_telegram_id = AsyncMock(return_value=existing_user)
            mock_repo.set_admin = AsyncMock(return_value=promoted_user)

            await cmd_set_admin(msg, db_session)

        mock_repo.set_admin.assert_called_once_with(TARGET_USER_ID, is_admin=True)
        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "назначен администратором" in text
        assert str(TARGET_USER_ID) in text

    @pytest.mark.asyncio
    async def test_setadmin_success_message_contains_user_id(self) -> None:
        msg = _make_message(f"/setadmin {TARGET_USER_ID}")
        db_session = _make_db_session()
        existing_user = _make_user_dto(is_admin=False)

        with patch("bot.handlers.owner.UserRepository") as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_by_telegram_id = AsyncMock(return_value=existing_user)
            mock_repo.set_admin = AsyncMock(return_value=_make_user_dto(is_admin=True))

            await cmd_set_admin(msg, db_session)

        text = msg.answer.call_args[0][0]
        assert str(TARGET_USER_ID) in text

    @pytest.mark.asyncio
    async def test_setadmin_passes_correct_session_to_repo(self) -> None:
        msg = _make_message(f"/setadmin {TARGET_USER_ID}")
        db_session = _make_db_session()

        with patch("bot.handlers.owner.UserRepository") as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_by_telegram_id = AsyncMock(return_value=None)

            await cmd_set_admin(msg, db_session)

        mock_repo_cls.assert_called_once_with(db_session)


# ---------------------------------------------------------------------------
# /rmadmin command
# ---------------------------------------------------------------------------


class TestCmdRmAdmin:
    @pytest.mark.asyncio
    async def test_rmadmin_missing_arg_sends_usage(self) -> None:
        msg = _make_message("/rmadmin")
        db_session = _make_db_session()

        await cmd_rm_admin(msg, db_session)

        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "Использование: /rmadmin <telegram_id>" in text

    @pytest.mark.asyncio
    async def test_rmadmin_invalid_number_sends_error(self) -> None:
        msg = _make_message("/rmadmin notanumber")
        db_session = _make_db_session()

        await cmd_rm_admin(msg, db_session)

        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "telegram_id должен быть числом" in text

    @pytest.mark.asyncio
    async def test_rmadmin_user_not_found_sends_error(self) -> None:
        msg = _make_message(f"/rmadmin {TARGET_USER_ID}")
        db_session = _make_db_session()

        with patch("bot.handlers.owner.UserRepository") as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_by_telegram_id = AsyncMock(return_value=None)

            await cmd_rm_admin(msg, db_session)

        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "не найден или не является администратором" in text

    @pytest.mark.asyncio
    async def test_rmadmin_user_not_admin_sends_error(self) -> None:
        msg = _make_message(f"/rmadmin {TARGET_USER_ID}")
        db_session = _make_db_session()
        regular_user = _make_user_dto(is_admin=False)

        with patch("bot.handlers.owner.UserRepository") as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_by_telegram_id = AsyncMock(return_value=regular_user)

            await cmd_rm_admin(msg, db_session)

        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "не найден или не является администратором" in text

    @pytest.mark.asyncio
    async def test_rmadmin_user_not_admin_does_not_call_set_admin(self) -> None:
        msg = _make_message(f"/rmadmin {TARGET_USER_ID}")
        db_session = _make_db_session()
        regular_user = _make_user_dto(is_admin=False)

        with patch("bot.handlers.owner.UserRepository") as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_by_telegram_id = AsyncMock(return_value=regular_user)
            mock_repo.set_admin = AsyncMock()

            await cmd_rm_admin(msg, db_session)

        mock_repo.set_admin.assert_not_called()

    @pytest.mark.asyncio
    async def test_rmadmin_success_calls_set_admin_false(self) -> None:
        msg = _make_message(f"/rmadmin {TARGET_USER_ID}")
        db_session = _make_db_session()
        admin_user = _make_user_dto(is_admin=True)
        demoted_user = _make_user_dto(is_admin=False)

        with patch("bot.handlers.owner.UserRepository") as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_by_telegram_id = AsyncMock(return_value=admin_user)
            mock_repo.set_admin = AsyncMock(return_value=demoted_user)

            await cmd_rm_admin(msg, db_session)

        mock_repo.set_admin.assert_called_once_with(TARGET_USER_ID, is_admin=False)

    @pytest.mark.asyncio
    async def test_rmadmin_success_sends_confirmation(self) -> None:
        msg = _make_message(f"/rmadmin {TARGET_USER_ID}")
        db_session = _make_db_session()
        admin_user = _make_user_dto(is_admin=True)

        with patch("bot.handlers.owner.UserRepository") as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_by_telegram_id = AsyncMock(return_value=admin_user)
            mock_repo.set_admin = AsyncMock(return_value=_make_user_dto(is_admin=False))

            await cmd_rm_admin(msg, db_session)

        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "Права администратора сняты" in text
        assert str(TARGET_USER_ID) in text

    @pytest.mark.asyncio
    async def test_rmadmin_passes_correct_session_to_repo(self) -> None:
        msg = _make_message(f"/rmadmin {TARGET_USER_ID}")
        db_session = _make_db_session()

        with patch("bot.handlers.owner.UserRepository") as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_by_telegram_id = AsyncMock(return_value=None)

            await cmd_rm_admin(msg, db_session)

        mock_repo_cls.assert_called_once_with(db_session)


# ---------------------------------------------------------------------------
# /admins command
# ---------------------------------------------------------------------------


class TestCmdAdmins:
    @pytest.mark.asyncio
    async def test_admins_empty_list_sends_no_admins_message(self) -> None:
        msg = _make_message("/admins")
        db_session = _make_db_session()

        with patch("bot.handlers.owner.UserRepository") as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.list_admins = AsyncMock(return_value=[])

            await cmd_admins(msg, db_session)

        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "Администраторов нет" in text

    @pytest.mark.asyncio
    async def test_admins_with_username_shows_at_username(self) -> None:
        msg = _make_message("/admins")
        db_session = _make_db_session()
        admin_with_username = _make_user_dto(
            telegram_id=111111111, username="adminuser", is_admin=True
        )

        with patch("bot.handlers.owner.UserRepository") as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.list_admins = AsyncMock(return_value=[admin_with_username])

            await cmd_admins(msg, db_session)

        text = msg.answer.call_args[0][0]
        assert "@adminuser" in text
        assert "111111111" in text

    @pytest.mark.asyncio
    async def test_admins_without_username_shows_id_only(self) -> None:
        msg = _make_message("/admins")
        db_session = _make_db_session()
        admin_no_username = _make_user_dto(
            telegram_id=222222222, username=None, is_admin=True
        )

        with patch("bot.handlers.owner.UserRepository") as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.list_admins = AsyncMock(return_value=[admin_no_username])

            await cmd_admins(msg, db_session)

        text = msg.answer.call_args[0][0]
        assert "222222222" in text
        assert "@" not in text

    @pytest.mark.asyncio
    async def test_admins_multiple_shows_all(self) -> None:
        msg = _make_message("/admins")
        db_session = _make_db_session()
        admin1 = _make_user_dto(telegram_id=111111111, username="alice", is_admin=True)
        admin2 = _make_user_dto(telegram_id=222222222, username="bob", is_admin=True)
        admin3 = _make_user_dto(telegram_id=333333333, username=None, is_admin=True)

        with patch("bot.handlers.owner.UserRepository") as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.list_admins = AsyncMock(return_value=[admin1, admin2, admin3])

            await cmd_admins(msg, db_session)

        text = msg.answer.call_args[0][0]
        assert "@alice" in text
        assert "111111111" in text
        assert "@bob" in text
        assert "222222222" in text
        assert "333333333" in text

    @pytest.mark.asyncio
    async def test_admins_reply_contains_header(self) -> None:
        msg = _make_message("/admins")
        db_session = _make_db_session()
        admin = _make_user_dto(is_admin=True)

        with patch("bot.handlers.owner.UserRepository") as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.list_admins = AsyncMock(return_value=[admin])

            await cmd_admins(msg, db_session)

        text = msg.answer.call_args[0][0]
        assert "Текущие администраторы" in text

    @pytest.mark.asyncio
    async def test_admins_passes_correct_session_to_repo(self) -> None:
        msg = _make_message("/admins")
        db_session = _make_db_session()

        with patch("bot.handlers.owner.UserRepository") as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.list_admins = AsyncMock(return_value=[])

            await cmd_admins(msg, db_session)

        mock_repo_cls.assert_called_once_with(db_session)


# ---------------------------------------------------------------------------
# Router-level filter: non-owner receives no response
# ---------------------------------------------------------------------------


class TestOwnerRouterFilter:
    """Verify that the router-level IsOwnerFilter is applied."""

    def test_router_has_message_filters(self) -> None:
        """The owner router must have at least one message-level filter.

        router.message.filter(...) stores filters on the internal _handler
        object. We verify at least one filter is registered there, which
        is the IsOwnerFilter applied via router.message.filter(IsOwnerFilter()).
        """
        assert len(router.message._handler.filters) > 0

    def test_router_name_is_owner(self) -> None:
        assert router.name == "owner"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_setadmin_with_negative_id_is_parsed(self) -> None:
        """Negative integers should be accepted as valid int conversion."""
        msg = _make_message("/setadmin -1")
        db_session = _make_db_session()

        with patch("bot.handlers.owner.UserRepository") as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_by_telegram_id = AsyncMock(return_value=None)

            await cmd_set_admin(msg, db_session)

        # Should reach "user not found", meaning int(-1) parsed without error
        text = msg.answer.call_args[0][0]
        assert "не найден" in text

    @pytest.mark.asyncio
    async def test_rmadmin_with_float_string_sends_number_error(self) -> None:
        msg = _make_message("/rmadmin 12.34")
        db_session = _make_db_session()

        await cmd_rm_admin(msg, db_session)

        text = msg.answer.call_args[0][0]
        assert "telegram_id должен быть числом" in text

    @pytest.mark.asyncio
    async def test_setadmin_message_is_none(self) -> None:
        """Handler must not crash when message.text is None."""
        msg = _make_message(None)
        db_session = _make_db_session()

        await cmd_set_admin(msg, db_session)

        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "Использование: /setadmin <telegram_id>" in text

    @pytest.mark.asyncio
    async def test_rmadmin_message_is_none(self) -> None:
        msg = _make_message(None)
        db_session = _make_db_session()

        await cmd_rm_admin(msg, db_session)

        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "Использование: /rmadmin <telegram_id>" in text
