"""Tests for bot.services.ton_price_service -- TON/RUB price fetching and caching."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from bot.services.ton_price_service import (
    NANOTONS_PER_TON,
    TonPriceUnavailableError,
    calculate_ton_nanotons,
    clear_cache,
    format_ton_display,
    get_ton_price_rub,
)


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    """Clear the price cache before each test to avoid cross-test leakage."""
    clear_cache()


def _mock_response(price: float) -> MagicMock:
    """Create a mock httpx response with a given TON/RUB price."""
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {"the-open-network": {"rub": price}}
    return resp


# ---------------------------------------------------------------------------
# get_ton_price_rub
# ---------------------------------------------------------------------------


class TestGetTonPriceRub:
    @pytest.mark.asyncio
    async def test_returns_decimal_price(self) -> None:
        mock_resp = _mock_response(250.50)
        with patch("bot.services.ton_price_service.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            price = await get_ton_price_rub()

        assert price == Decimal("250.50")

    @pytest.mark.asyncio
    async def test_caches_result(self) -> None:
        """Second call should use cached value, not make HTTP request."""
        mock_resp = _mock_response(250.50)
        with patch("bot.services.ton_price_service.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            price1 = await get_ton_price_rub()
            price2 = await get_ton_price_rub()

        assert price1 == price2
        # Only one HTTP call should have been made
        assert mock_client.get.call_count == 1

    @pytest.mark.asyncio
    async def test_raises_on_http_error(self) -> None:
        with patch("bot.services.ton_price_service.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=httpx.ConnectError("timeout"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            with pytest.raises(TonPriceUnavailableError):
                await get_ton_price_rub()

    @pytest.mark.asyncio
    async def test_raises_on_unexpected_json(self) -> None:
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"unexpected": "data"}

        with patch("bot.services.ton_price_service.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            with pytest.raises(TonPriceUnavailableError):
                await get_ton_price_rub()

    @pytest.mark.asyncio
    async def test_cache_expires_after_ttl(self) -> None:
        """After TTL expires, a new HTTP request should be made."""
        mock_resp = _mock_response(250.50)
        with (
            patch("bot.services.ton_price_service.httpx.AsyncClient") as mock_cls,
            patch("bot.services.ton_price_service.time.monotonic") as mock_time,
        ):
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            # First call at time=0
            mock_time.return_value = 0.0
            await get_ton_price_rub()

            # Second call at time=400 (past the 300s TTL)
            mock_time.return_value = 400.0
            await get_ton_price_rub()

        assert mock_client.get.call_count == 2


# ---------------------------------------------------------------------------
# calculate_ton_nanotons
# ---------------------------------------------------------------------------


class TestCalculateTonNanotons:
    @pytest.mark.asyncio
    async def test_calculates_nanotons(self) -> None:
        """200 RUB at 200 RUB/TON = 1 TON = 1_000_000_000 nanotons."""
        with patch(
            "bot.services.ton_price_service.get_ton_price_rub",
            new_callable=AsyncMock,
            return_value=Decimal("200"),
        ):
            nanotons = await calculate_ton_nanotons(200)

        assert nanotons == NANOTONS_PER_TON

    @pytest.mark.asyncio
    async def test_rounds_up(self) -> None:
        """Amount should be rounded up to avoid underpayment."""
        with patch(
            "bot.services.ton_price_service.get_ton_price_rub",
            new_callable=AsyncMock,
            return_value=Decimal("300"),
        ):
            nanotons = await calculate_ton_nanotons(200)

        # 200/300 = 0.666... TON = 666_666_666.666... nanotons -> 666_666_667
        assert nanotons == 666_666_667

    @pytest.mark.asyncio
    async def test_propagates_unavailable_error(self) -> None:
        with (
            patch(
                "bot.services.ton_price_service.get_ton_price_rub",
                new_callable=AsyncMock,
                side_effect=TonPriceUnavailableError("test"),
            ),
            pytest.raises(TonPriceUnavailableError),
        ):
            await calculate_ton_nanotons(200)


# ---------------------------------------------------------------------------
# format_ton_display
# ---------------------------------------------------------------------------


class TestFormatTonDisplay:
    def test_formats_to_two_decimals(self) -> None:
        # 1_000_000_000 nanotons = 1 TON
        assert format_ton_display(1_000_000_000) == "1.00"

    def test_rounds_up_display(self) -> None:
        # 666_666_667 nanotons = 0.666666667 TON -> "0.67"
        assert format_ton_display(666_666_667) == "0.67"

    def test_small_amount(self) -> None:
        # 100_000_000 nanotons = 0.1 TON
        assert format_ton_display(100_000_000) == "0.10"
