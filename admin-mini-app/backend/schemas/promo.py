"""Pydantic v2 schemas for the promo codes API.

These DTOs transfer promo code data between the API layer and clients.
PromoResponse includes a computed `is_expired` field derived from the
`valid_until` timestamp so the frontend doesn't need date arithmetic.
"""

from datetime import UTC, datetime

from pydantic import BaseModel, Field, computed_field, model_validator


class PromoCreate(BaseModel):
    """Payload for creating a new promo code.

    Either ``valid_days`` or ``valid_until`` must be provided (not both empty).
    ``valid_days`` is a convenience shortcut that the API converts to an
    absolute ``valid_until`` timestamp.
    """

    code: str = Field(min_length=1, max_length=32, pattern=r"^[A-Z0-9]+$")
    discount_percent: int = Field(ge=1, le=100)
    max_activations: int = Field(ge=1)
    valid_days: int | None = Field(default=None, ge=1)
    valid_until: datetime | None = None

    @model_validator(mode="after")
    def check_validity_period(self) -> "PromoCreate":
        """Ensure at least one validity constraint is provided."""
        if self.valid_days is None and self.valid_until is None:
            raise ValueError(
                "Either valid_days or valid_until must be provided"
            )
        return self


class PromoResponse(BaseModel):
    """Full promo code representation returned to the client."""

    id: int
    code: str
    discount_percent: int
    max_activations: int
    current_activations: int
    valid_until: datetime
    is_active: bool
    created_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_expired(self) -> bool:
        """True when the promo code's validity period has passed."""
        return datetime.now(UTC) > self.valid_until.astimezone(UTC)


class PromoListResponse(BaseModel):
    """Paginated list of promo codes."""

    items: list[PromoResponse]
    total: int
    page: int
    per_page: int


class PromoToggleRequest(BaseModel):
    """Payload for toggling promo code active state."""

    is_active: bool


class PromoUsageResponse(BaseModel):
    """Single promo usage record with user info."""

    user_id: int
    username: str | None = None
    first_name: str | None = None
    used_at: datetime


class PromoUsageListResponse(BaseModel):
    """Paginated list of promo usage records."""

    items: list[PromoUsageResponse]
    total: int
    page: int
    per_page: int


class GenerateCodeResponse(BaseModel):
    """Response containing a generated unique promo code."""

    code: str
