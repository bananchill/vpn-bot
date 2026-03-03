"""Business logic for subscriptions and promo code activation.

Pure business logic layer -- no framework imports.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import settings
from bot.db.repositories.config_repo import ConfigRepository
from bot.db.repositories.promo_code_repo import PromoCodeRepository
from bot.db.repositories.subscription_repo import SubscriptionRepository
from bot.dto import SubscriptionDTO
from bot.services.xui_client import XUIClient

logger = logging.getLogger(__name__)


class PromoCodeError(Exception):
    """Base error for promo code validation failures."""


class PromoCodeNotFoundError(PromoCodeError):
    """The promo code does not exist or is deactivated."""


class PromoCodeAlreadyUsedError(PromoCodeError):
    """The user has already used this promo code."""


async def get_active(user_id: int, session: AsyncSession) -> SubscriptionDTO | None:
    """Return the active subscription for a user, or None.

    Args:
        user_id: Internal DB user ID.
        session: DB session (caller manages transaction).

    Returns:
        Active subscription DTO if one exists, None otherwise.
    """
    repo = SubscriptionRepository(session)
    return await repo.get_active(user_id, now=datetime.now(tz=UTC))


async def activate(
    user_id: int,
    source: str,
    session: AsyncSession,
) -> SubscriptionDTO:
    """Create or extend a subscription for a user.

    Smart renewal: if the user already has an active subscription,
    the new period starts from the current expiry date (stacking).
    Otherwise it starts from now.

    Args:
        user_id: Internal DB user ID.
        source: Payment source ("stars", "ton", or "promo").
        session: DB session (caller manages transaction).

    Returns:
        Newly created subscription DTO.
    """
    now = datetime.now(tz=UTC)
    repo = SubscriptionRepository(session)

    existing = await repo.get_active(user_id, now=now)
    if existing is not None:
        # Stack on top of the current active subscription
        started_at = existing.expires_at
        expires_at = existing.expires_at + timedelta(days=settings.SUBSCRIPTION_DAYS)
    else:
        started_at = now
        expires_at = now + timedelta(days=settings.SUBSCRIPTION_DAYS)

    sub = await repo.create(
        user_id=user_id,
        source=source,
        started_at=started_at,
        expires_at=expires_at,
    )
    logger.info(
        "Subscription activated: user_id=%s source=%s expires_at=%s",
        user_id, source, expires_at,
    )
    return sub


async def activate_promo(
    user_id: int,
    code: str,
    session: AsyncSession,
) -> SubscriptionDTO:
    """Validate a promo code and activate a subscription.

    Checks that the code exists, is active, and has not been used
    by this user. Increments the use_count and creates a subscription.

    Args:
        user_id: Internal DB user ID.
        code: Promo code string (will be normalized to lowercase).
        session: DB session (caller manages transaction).

    Returns:
        Newly created subscription DTO.

    Raises:
        PromoCodeNotFoundError: If the code does not exist or is deactivated.
        PromoCodeAlreadyUsedError: If this user has already used this code.
    """
    normalized = code.strip().lower()

    promo_repo = PromoCodeRepository(session)
    promo = await promo_repo.get_by_code(normalized)

    if promo is None or not promo.is_active:
        raise PromoCodeNotFoundError(f"Promo code '{normalized}' not found or inactive")

    sub_repo = SubscriptionRepository(session)
    if await sub_repo.has_used_promo(user_id, normalized):
        raise PromoCodeAlreadyUsedError(
            f"User {user_id} already used promo code '{normalized}'"
        )

    await promo_repo.increment_use_count(normalized)

    now = datetime.now(tz=UTC)
    existing = await sub_repo.get_active(user_id, now=now)
    if existing is not None:
        started_at = existing.expires_at
        expires_at = existing.expires_at + timedelta(days=settings.SUBSCRIPTION_DAYS)
    else:
        started_at = now
        expires_at = now + timedelta(days=settings.SUBSCRIPTION_DAYS)

    sub = await sub_repo.create(
        user_id=user_id,
        source="promo",
        started_at=started_at,
        expires_at=expires_at,
        promo_code=normalized,
    )
    logger.info(
        "Promo subscription activated: user_id=%s code=%s expires_at=%s",
        user_id, normalized, expires_at,
    )
    return sub


async def sync_configs_expiry(
    user_id: int,
    new_expires_at: datetime,
    xui: XUIClient,
    session: AsyncSession,
) -> bool:
    """Update expiryTime for all user configs in 3x-ui after subscription renewal.

    Fetches each config's current client data from the panel, patches the
    expiryTime field, and pushes the update back.  Errors on individual
    configs are logged but do not abort the loop.

    Args:
        user_id: Internal DB user ID.
        new_expires_at: The new subscription expiry timestamp.
        xui: Authenticated XUI client.
        session: DB session (caller manages transaction).

    Returns:
        True if all configs were updated successfully, False otherwise.
    """
    config_repo = ConfigRepository(session)
    configs = await config_repo.get_by_user_id(user_id)

    if not configs:
        return True

    expiry_time_ms = int(new_expires_at.timestamp() * 1000)
    all_ok = True

    for cfg in configs:
        try:
            inbound = await xui.get_inbound(cfg.inbound_id)
            # Parse the settings JSON to find the client by UUID
            raw_settings = inbound.get("settings", "{}")
            parsed = json.loads(raw_settings) if isinstance(raw_settings, str) else raw_settings
            clients = parsed.get("clients", [])

            client_data = _find_client_by_uuid(clients, cfg.client_id)
            if client_data is None:
                logger.warning(
                    "Client uuid=%s not found in inbound %s, skipping",
                    cfg.client_id, cfg.inbound_id,
                )
                all_ok = False
                continue

            # Update only the expiryTime field, keep everything else intact
            client_data["expiryTime"] = expiry_time_ms
            await xui.update_client(cfg.client_id, cfg.inbound_id, client_data)

            logger.info(
                "Updated expiryTime for config '%s' (uuid=%s) to %s",
                cfg.email, cfg.client_id, new_expires_at,
            )
        except Exception:
            logger.exception(
                "Failed to sync expiryTime for config '%s' (uuid=%s)",
                cfg.email, cfg.client_id,
            )
            all_ok = False

    return all_ok


def _find_client_by_uuid(
    clients: list[dict[str, object]],
    client_uuid: str,
) -> dict[str, object] | None:
    """Locate a client dict in the inbound's client list by its UUID."""
    for client in clients:
        if client.get("id") == client_uuid:
            return client
    return None
