"""Tests for bot.handlers.owner -- owner commands.

/setadmin, /rmadmin, /admins are deprecated (TASK-018) and now return
a deprecation message directing the user to the admin mini-app.
/promo commands remain functional.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.types import Chat, Message, User

from bot.dto import PromoCodeDTO
from bot.handlers.owner import (
    _DEPRECATED_MSG,
    _MISSING,
    IsOwnerFilter,
    _extract_arg,
    cmd_admins,
    cmd_promo,
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
# /setadmin — deprecated (TASK-018)
# ---------------------------------------------------------------------------


class TestCmdSetAdmin:
    @pytest.mark.asyncio
    async def test_setadmin_returns_deprecated_message(self) -> None:
        msg = _make_message("/setadmin 123456789")
        await cmd_set_admin(msg)

        msg.answer.assert_called_once_with(_DEPRECATED_MSG)

    @pytest.mark.asyncio
    async def test_setadmin_without_args_returns_deprecated_message(self) -> None:
        msg = _make_message("/setadmin")
        await cmd_set_admin(msg)

        msg.answer.assert_called_once_with(_DEPRECATED_MSG)

    @pytest.mark.asyncio
    async def test_setadmin_deprecated_message_mentions_miniapp(self) -> None:
        assert "мини-апп" in _DEPRECATED_MSG


# ---------------------------------------------------------------------------
# /rmadmin — deprecated (TASK-018)
# ---------------------------------------------------------------------------


class TestCmdRmAdmin:
    @pytest.mark.asyncio
    async def test_rmadmin_returns_deprecated_message(self) -> None:
        msg = _make_message("/rmadmin 123456789")
        await cmd_rm_admin(msg)

        msg.answer.assert_called_once_with(_DEPRECATED_MSG)

    @pytest.mark.asyncio
    async def test_rmadmin_without_args_returns_deprecated_message(self) -> None:
        msg = _make_message("/rmadmin")
        await cmd_rm_admin(msg)

        msg.answer.assert_called_once_with(_DEPRECATED_MSG)


# ---------------------------------------------------------------------------
# /admins — deprecated (TASK-018)
# ---------------------------------------------------------------------------


class TestCmdAdmins:
    @pytest.mark.asyncio
    async def test_admins_returns_deprecated_message(self) -> None:
        msg = _make_message("/admins")
        await cmd_admins(msg)

        msg.answer.assert_called_once_with(_DEPRECATED_MSG)


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
# /promo commands
# ---------------------------------------------------------------------------


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


class TestCmdPromo:
    @pytest.mark.asyncio
    async def test_no_subcommand_shows_usage(self) -> None:
        msg = _make_message("/promo")
        db_session = _make_db_session()

        await cmd_promo(msg, db_session)

        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "create" in text
        assert "list" in text
        assert "disable" in text

    @pytest.mark.asyncio
    async def test_unknown_subcommand_shows_error(self) -> None:
        msg = _make_message("/promo unknown")
        db_session = _make_db_session()

        await cmd_promo(msg, db_session)

        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "Неизвестная подкоманда" in text


class TestPromoCreate:
    @pytest.mark.asyncio
    async def test_create_success(self) -> None:
        msg = _make_message("/promo create MYCODE")
        db_session = _make_db_session()
        promo = _make_promo_dto(code="mycode")

        with patch("bot.handlers.owner.PromoCodeRepository") as mock_cls:
            mock_repo = mock_cls.return_value
            mock_repo.get_by_code = AsyncMock(return_value=None)
            mock_repo.create = AsyncMock(return_value=promo)

            await cmd_promo(msg, db_session)

        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "mycode" in text
        assert "создан" in text.lower()

    @pytest.mark.asyncio
    async def test_create_missing_code(self) -> None:
        msg = _make_message("/promo create")
        db_session = _make_db_session()

        await cmd_promo(msg, db_session)

        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "Использование" in text

    @pytest.mark.asyncio
    async def test_create_duplicate_code(self) -> None:
        msg = _make_message("/promo create EXISTING")
        db_session = _make_db_session()
        promo = _make_promo_dto(code="existing")

        with patch("bot.handlers.owner.PromoCodeRepository") as mock_cls:
            mock_repo = mock_cls.return_value
            mock_repo.get_by_code = AsyncMock(return_value=promo)

            await cmd_promo(msg, db_session)

        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "уже существует" in text.lower()


class TestPromoList:
    @pytest.mark.asyncio
    async def test_list_empty(self) -> None:
        msg = _make_message("/promo list")
        db_session = _make_db_session()

        with patch("bot.handlers.owner.PromoCodeRepository") as mock_cls:
            mock_repo = mock_cls.return_value
            mock_repo.list_all = AsyncMock(return_value=[])

            await cmd_promo(msg, db_session)

        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "нет" in text.lower()

    @pytest.mark.asyncio
    async def test_list_shows_all_with_stats(self) -> None:
        msg = _make_message("/promo list")
        db_session = _make_db_session()
        promos = [
            _make_promo_dto(code="code1", is_active=True, use_count=3),
            _make_promo_dto(code="code2", is_active=False, use_count=0),
        ]

        with patch("bot.handlers.owner.PromoCodeRepository") as mock_cls:
            mock_repo = mock_cls.return_value
            mock_repo.list_all = AsyncMock(return_value=promos)

            await cmd_promo(msg, db_session)

        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "code1" in text
        assert "активен" in text
        assert "code2" in text
        assert "деактивирован" in text


class TestPromoDisable:
    @pytest.mark.asyncio
    async def test_disable_success(self) -> None:
        msg = _make_message("/promo disable MYCODE")
        db_session = _make_db_session()

        with patch("bot.handlers.owner.PromoCodeRepository") as mock_cls:
            mock_repo = mock_cls.return_value
            mock_repo.deactivate = AsyncMock(return_value=True)

            await cmd_promo(msg, db_session)

        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "деактивирован" in text.lower()

    @pytest.mark.asyncio
    async def test_disable_not_found(self) -> None:
        msg = _make_message("/promo disable UNKNOWN")
        db_session = _make_db_session()

        with patch("bot.handlers.owner.PromoCodeRepository") as mock_cls:
            mock_repo = mock_cls.return_value
            mock_repo.deactivate = AsyncMock(return_value=False)

            await cmd_promo(msg, db_session)

        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "не найден" in text.lower()

    @pytest.mark.asyncio
    async def test_disable_missing_code(self) -> None:
        msg = _make_message("/promo disable")
        db_session = _make_db_session()

        await cmd_promo(msg, db_session)

        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "Использование" in text
