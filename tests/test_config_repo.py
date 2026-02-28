"""Tests for bot.db.repositories.config_repo."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from bot.db.repositories.config_repo import ConfigRepository
from bot.dto import ConfigDTO


class TestConfigRepository:
    @pytest.fixture()
    def session(self) -> AsyncMock:
        return AsyncMock()

    @pytest.fixture()
    def repo(self, session: AsyncMock) -> ConfigRepository:
        return ConfigRepository(session)

    @pytest.mark.asyncio
    async def test_create(self, repo: ConfigRepository, session: AsyncMock) -> None:
        now = datetime.now(tz=UTC)

        # After flush + refresh, the ORM object gets server-generated fields
        async def fake_refresh(obj: object) -> None:
            obj.id = 1  # type: ignore[attr-defined]
            obj.created_at = now  # type: ignore[attr-defined]

        session.flush = AsyncMock()
        session.refresh = fake_refresh

        config = await repo.create(
            user_id=1,
            inbound_id=1,
            client_id="uuid-123",
            email="test@config",
            protocol="vless",
        )

        session.add.assert_called_once()
        assert isinstance(config, ConfigDTO)
        assert config.user_id == 1
        assert config.client_id == "uuid-123"
        assert config.email == "test@config"
        assert config.protocol == "vless"
        assert config.created_at == now

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, repo: ConfigRepository, session: AsyncMock) -> None:
        now = datetime.now(tz=UTC)
        mock_config = MagicMock()
        mock_config.id = 42
        mock_config.user_id = 1
        mock_config.inbound_id = 1
        mock_config.client_id = "uuid-123"
        mock_config.email = "test@config"
        mock_config.protocol = "vless"
        mock_config.created_at = now

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_config
        session.execute = AsyncMock(return_value=mock_result)

        result = await repo.get_by_id(42)

        assert isinstance(result, ConfigDTO)
        assert result.id == 42
        assert result.email == "test@config"

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, repo: ConfigRepository, session: AsyncMock) -> None:
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)

        result = await repo.get_by_id(999)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_user_id(self, repo: ConfigRepository, session: AsyncMock) -> None:
        now = datetime.now(tz=UTC)

        def _mock_orm(config_id: int, email: str) -> MagicMock:
            m = MagicMock()
            m.id = config_id
            m.user_id = 1
            m.inbound_id = 1
            m.client_id = f"uuid-{config_id}"
            m.email = email
            m.protocol = "vless"
            m.created_at = now
            return m

        mock_configs = [_mock_orm(1, "cfg-1"), _mock_orm(2, "cfg-2")]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_configs
        session.execute = AsyncMock(return_value=mock_result)

        result = await repo.get_by_user_id(1)

        assert len(result) == 2
        assert all(isinstance(c, ConfigDTO) for c in result)
        assert result[0].email == "cfg-1"
        assert result[1].email == "cfg-2"

    @pytest.mark.asyncio
    async def test_get_by_email_found(self, repo: ConfigRepository, session: AsyncMock) -> None:
        now = datetime.now(tz=UTC)
        mock_config = MagicMock()
        mock_config.id = 1
        mock_config.user_id = 1
        mock_config.inbound_id = 1
        mock_config.client_id = "uuid-123"
        mock_config.email = "test@config"
        mock_config.protocol = "vless"
        mock_config.created_at = now

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_config
        session.execute = AsyncMock(return_value=mock_result)

        result = await repo.get_by_email("test@config")

        assert isinstance(result, ConfigDTO)
        assert result.email == "test@config"

    @pytest.mark.asyncio
    async def test_delete_existing(self, repo: ConfigRepository, session: AsyncMock) -> None:
        mock_config = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_config
        session.execute = AsyncMock(return_value=mock_result)
        session.delete = AsyncMock()
        session.flush = AsyncMock()

        await repo.delete(1)

        session.delete.assert_called_once_with(mock_config)
        session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, repo: ConfigRepository, session: AsyncMock) -> None:
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)
        session.delete = AsyncMock()

        await repo.delete(999)

        session.delete.assert_not_called()
