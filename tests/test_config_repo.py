"""Tests for bot.db.repositories.config_repo."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from bot.db.repositories.config_repo import ConfigRepository


class TestConfigRepository:
    @pytest.fixture()
    def session(self) -> AsyncMock:
        return AsyncMock()

    @pytest.fixture()
    def repo(self, session: AsyncMock) -> ConfigRepository:
        return ConfigRepository(session)

    @pytest.mark.asyncio
    async def test_create(self, repo: ConfigRepository, session: AsyncMock) -> None:
        session.flush = AsyncMock()

        config = await repo.create(
            user_id=1,
            inbound_id=1,
            client_id="uuid-123",
            email="test@config",
            protocol="vless",
        )

        session.add.assert_called_once()
        session.flush.assert_called_once()
        assert config.user_id == 1
        assert config.client_id == "uuid-123"
        assert config.email == "test@config"
        assert config.protocol == "vless"

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, repo: ConfigRepository, session: AsyncMock) -> None:
        mock_config = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_config
        session.execute = AsyncMock(return_value=mock_result)

        result = await repo.get_by_id(42)

        assert result == mock_config

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, repo: ConfigRepository, session: AsyncMock) -> None:
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)

        result = await repo.get_by_id(999)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_user_id(self, repo: ConfigRepository, session: AsyncMock) -> None:
        mock_configs = [MagicMock(), MagicMock()]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_configs
        session.execute = AsyncMock(return_value=mock_result)

        result = await repo.get_by_user_id(1)

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_by_email_found(self, repo: ConfigRepository, session: AsyncMock) -> None:
        mock_config = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_config
        session.execute = AsyncMock(return_value=mock_result)

        result = await repo.get_by_email("test@config")

        assert result == mock_config

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
