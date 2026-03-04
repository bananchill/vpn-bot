"""Pydantic v2 schemas for the users API.

These DTOs transfer user data between the API layer and clients.
UserDetail includes computed fields like days_subscribed so the
frontend does not need to perform date arithmetic.
"""

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, computed_field

from schemas.config import ConfigResponse


class UserShort(BaseModel):
    """Compact user representation for list views."""

    id: int
    telegram_id: int
    username: str | None = None
    first_name: str | None = None
    photo_url: str | None = None
    is_paid: bool
    is_blocked: bool
    subscription_expires: datetime | None = None


class UserDetail(UserShort):
    """Full user representation with configs and computed metrics."""

    subscribed_since: datetime | None = None
    admin_note: str | None = None
    configs: list[ConfigResponse] = []
    # promo_usages will be populated in a later stage
    promo_usages: list[dict[str, str]] = []

    @computed_field  # type: ignore[prop-decorator]
    @property
    def days_subscribed(self) -> int | None:
        """Calculate the number of days since the subscription started.

        Returns None when the user has never been subscribed.
        """
        if self.subscribed_since is None:
            return None
        delta = datetime.now(UTC) - self.subscribed_since.replace(
            tzinfo=UTC
        )
        return max(0, delta.days)


class UserListResponse(BaseModel):
    """Paginated list of users."""

    items: list[UserShort]
    total: int
    page: int
    per_page: int
    pages: int


class UserBlockRequest(BaseModel):
    """Payload for blocking/unblocking a user."""

    is_blocked: bool


class UserNoteRequest(BaseModel):
    """Payload for updating the admin note on a user.

    Send note=None (or omit the field) to clear the existing note.
    """

    note: str | None = None


class UserExtendRequest(BaseModel):
    """Payload for extending a user's subscription by N days."""

    days: int


# Query parameter types for stricter validation
SubscriptionFilter = Literal["active", "expired", "expiring_7d"]
SortField = Literal["created_at", "first_name", "subscription_expires"]
SortOrder = Literal["asc", "desc"]
