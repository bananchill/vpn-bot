"""Tests for bot.dto — DTO structure and validation."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from bot.dto import ConfigDTO, ConfigSummaryDTO, UserDTO

NOW = datetime.now(tz=UTC)


class TestUserDTO:
    def test_create_with_valid_data(self) -> None:
        user = UserDTO(
            id=1,
            telegram_id=123456,
            username="testuser",
            is_admin=False,
            created_at=NOW,
        )
        assert user.id == 1
        assert user.telegram_id == 123456
        assert user.username == "testuser"
        assert user.is_admin is False
        assert user.created_at == NOW

    def test_username_can_be_none(self) -> None:
        user = UserDTO(
            id=1,
            telegram_id=123456,
            username=None,
            is_admin=False,
            created_at=NOW,
        )
        assert user.username is None

    def test_from_attributes_enabled(self) -> None:
        """model_validate must accept ORM-like objects with attribute access."""
        orm_like = MagicMock()
        orm_like.id = 5
        orm_like.telegram_id = 999
        orm_like.username = "admin"
        orm_like.is_admin = True
        orm_like.created_at = NOW

        dto = UserDTO.model_validate(orm_like)

        assert dto.id == 5
        assert dto.telegram_id == 999
        assert dto.is_admin is True

    def test_is_pydantic_not_orm(self) -> None:
        """UserDTO must be a Pydantic model, not an ORM object."""
        # Pydantic models expose model_fields on the class; ORM objects do not
        assert hasattr(UserDTO, "model_fields")


class TestConfigDTO:
    def test_create_with_valid_data(self) -> None:
        config = ConfigDTO(
            id=1,
            user_id=1,
            inbound_id=2,
            client_id="uuid-abc",
            sub_id="abcdef0123456789",
            email="my-config",
            protocol="vless",
            created_at=NOW,
        )
        assert config.id == 1
        assert config.user_id == 1
        assert config.inbound_id == 2
        assert config.client_id == "uuid-abc"
        assert config.sub_id == "abcdef0123456789"
        assert config.email == "my-config"
        assert config.protocol == "vless"

    def test_from_attributes_enabled(self) -> None:
        """model_validate must accept ORM-like objects."""
        orm_like = MagicMock()
        orm_like.id = 42
        orm_like.user_id = 7
        orm_like.inbound_id = 3
        orm_like.client_id = "some-uuid"
        orm_like.sub_id = "abcdef0123456789"
        orm_like.email = "cfg@test"
        orm_like.protocol = "vmess"
        orm_like.created_at = NOW

        dto = ConfigDTO.model_validate(orm_like)

        assert dto.id == 42
        assert dto.sub_id == "abcdef0123456789"
        assert dto.protocol == "vmess"

    def test_is_pydantic_not_orm(self) -> None:
        assert hasattr(ConfigDTO, "model_fields")


class TestConfigSummaryDTO:
    def test_create_with_id_and_email(self) -> None:
        summary = ConfigSummaryDTO(id=3, email="my-vpn")
        assert summary.id == 3
        assert summary.email == "my-vpn"

    def test_has_no_extra_fields(self) -> None:
        """ConfigSummaryDTO is intentionally lightweight — only id and email."""
        assert set(ConfigSummaryDTO.model_fields.keys()) == {"id", "email"}

    def test_missing_required_field_raises(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ConfigSummaryDTO(id=1)  # type: ignore[call-arg]
