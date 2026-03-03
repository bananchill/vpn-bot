"""TON price service — fetches TON/RUB rate from CoinGecko with in-process cache."""

import logging
import time
from decimal import ROUND_UP, Decimal

import httpx

from bot.config import settings

logger = logging.getLogger(__name__)

COINGECKO_URL = (
    "https://api.coingecko.com/api/v3/simple/price"
    "?ids=the-open-network&vs_currencies=rub"
)

# 1 TON = 1_000_000_000 nanotons
NANOTONS_PER_TON = 1_000_000_000


class TonPriceUnavailableError(Exception):
    """Raised when the TON price cannot be fetched from CoinGecko."""


# Simple in-process cache: stores (price, timestamp)
_cache: dict[str, Decimal | float] = {}


def _is_cache_valid() -> bool:
    """Check whether the cached price is still within TTL."""
    fetched_at = _cache.get("fetched_at")
    if fetched_at is None:
        return False
    elapsed = time.monotonic() - float(fetched_at)
    return elapsed < settings.TON_PRICE_CACHE_TTL


async def get_ton_price_rub() -> Decimal:
    """Fetch the current TON price in RUB from CoinGecko.

    Uses an in-process cache with TTL defined by TON_PRICE_CACHE_TTL.

    Returns:
        TON price in RUB as a Decimal.

    Raises:
        TonPriceUnavailableError: If the API is unreachable or returns unexpected data.
    """
    if _is_cache_valid():
        cached = _cache.get("price")
        if cached is not None:
            return Decimal(str(cached))

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(COINGECKO_URL)
            response.raise_for_status()
            data = response.json()
            price_raw = data["the-open-network"]["rub"]
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        logger.error("Failed to fetch TON price from CoinGecko: %s", exc)
        raise TonPriceUnavailableError("CoinGecko API unavailable") from exc

    price = Decimal(str(price_raw))
    _cache["price"] = price
    _cache["fetched_at"] = time.monotonic()
    return price


async def calculate_ton_nanotons(rub_amount: int) -> int:
    """Calculate nanoton amount for a given RUB price.

    Args:
        rub_amount: Price in Russian Rubles.

    Returns:
        Amount in nanotons (1 TON = 1_000_000_000 nanotons), rounded up.

    Raises:
        TonPriceUnavailableError: If the TON price cannot be fetched.
    """
    price_rub = await get_ton_price_rub()
    # TON amount = rub_amount / price_per_ton
    ton_amount = Decimal(str(rub_amount)) / price_rub
    nanotons = ton_amount * Decimal(str(NANOTONS_PER_TON))
    # Round up to avoid underpayment
    return int(nanotons.to_integral_value(rounding=ROUND_UP))


def format_ton_display(nanotons: int) -> str:
    """Format nanotons as a human-readable TON string with 2 decimal places.

    Args:
        nanotons: Amount in nanotons.

    Returns:
        String like "1.23" representing the TON amount.
    """
    ton = Decimal(str(nanotons)) / Decimal(str(NANOTONS_PER_TON))
    return str(ton.quantize(Decimal("0.01"), rounding=ROUND_UP))


def clear_cache() -> None:
    """Clear the price cache. Useful for testing."""
    _cache.clear()
