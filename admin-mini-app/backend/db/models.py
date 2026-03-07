"""SQLAlchemy ORM models for the admin mini-app.

Mirror models (AdminSession) reflect tables owned by the bot so that
the admin-mini-app can read/write them through the shared PostgreSQL
database without an intermediate HTTP API.
"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.engine import Base


class BotSettings(Base):
    """Singleton row storing panel connection credentials and bot configuration.

    Only one row (id=1) should exist. All sensitive fields (panel_password,
    client_bot_token) are stored Fernet-encrypted.
    """

    __tablename__ = "bot_settings"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    panel_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    panel_sub_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    panel_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Fernet-encrypted panel password
    panel_password: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    owner_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    # Fernet-encrypted client bot token
    client_bot_token: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<BotSettings id={self.id} panel_url={self.panel_url}>"


class User(Base):
    """Telegram user of the VPN service."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, nullable=False, index=True
    )
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_admin: Mapped[bool] = mapped_column(default=False, server_default="false", nullable=False)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_paid: Mapped[bool] = mapped_column(default=False, server_default="false", nullable=False)
    subscription_expires: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    subscribed_since: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_blocked: Mapped[bool] = mapped_column(default=False, server_default="false", nullable=False)
    admin_note: Mapped[str | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    configs: Mapped[list["VPNConfig"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    promo_usages: Mapped[list["PromoUsage"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User telegram_id={self.telegram_id} username={self.username}>"


class VPNConfig(Base):
    """VPN configuration linked to a user, mapped to the bot's 'configs' table."""

    __tablename__ = "configs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    inbound_id: Mapped[int] = mapped_column(nullable=False)
    client_id: Mapped[str] = mapped_column(String(36), nullable=False)
    sub_id: Mapped[str] = mapped_column(String(16), nullable=False, server_default="")
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    protocol: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="configs")

    def __repr__(self) -> str:
        return f"<VPNConfig email={self.email} protocol={self.protocol}>"


class Admin(Base):
    """Admin user with access to the mini-app panel.

    Serves as the single source of truth for administrator identity.
    Both the bot and admin-mini-app read/write this table directly via
    a shared PostgreSQL database.  Per-admin panel credentials and
    config-bot tokens are stored here (encrypted with Fernet).
    """

    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, nullable=False
    )
    # "owner" grants full access; "moderator" has limited access
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    # Telegram username — populated from initData on first login, updated on each entry
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # -- Per-admin 3x-ui panel credentials --
    panel_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    panel_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Fernet-encrypted panel password
    panel_password_encrypted: Mapped[str | None] = mapped_column(
        String(1024), nullable=True
    )
    # Base URL for subscription links (e.g. https://host:2096)
    panel_sub_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # -- Per-admin config-bot token (Fernet-encrypted) --
    config_bot_token_encrypted: Mapped[str | None] = mapped_column(
        String(1024), nullable=True
    )

    added_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<Admin telegram_id={self.telegram_id} role={self.role}>"


class PromoCode(Base):
    """Promotional code with a percentage discount and activation limit.

    Tracks current usage count and can be deactivated by an admin.
    The `is_expired` check lives in the Pydantic schema layer, not here,
    because it depends on wall-clock time and should not be stored.
    """

    __tablename__ = "promo_codes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, nullable=False
    )
    discount_percent: Mapped[int] = mapped_column(nullable=False)
    max_activations: Mapped[int] = mapped_column(nullable=False)
    current_activations: Mapped[int] = mapped_column(
        default=0, server_default="0", nullable=False
    )
    valid_until: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        default=True, server_default="true", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    usages: Mapped[list["PromoUsage"]] = relationship(
        back_populates="promo", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<PromoCode code={self.code} discount={self.discount_percent}%>"


class PromoUsage(Base):
    """Records a single use of a promo code by a user.

    Both foreign keys cascade on delete: removing a promo code or a user
    automatically cleans up associated usage records.
    """

    __tablename__ = "promo_usages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    promo_id: Mapped[int] = mapped_column(
        ForeignKey("promo_codes.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    promo: Mapped["PromoCode"] = relationship(back_populates="usages")
    user: Mapped["User"] = relationship(back_populates="promo_usages")

    def __repr__(self) -> str:
        return f"<PromoUsage promo_id={self.promo_id} user_id={self.user_id}>"


class AdminLog(Base):
    """Audit log entry for admin actions.

    Every mutating admin operation (block, extend, toggle, settings update,
    promo CRUD) writes a row here for traceability.  The `details` column
    stores a free-form JSON string with action-specific context.
    """

    __tablename__ = "admin_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    admin_telegram_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, index=True
    )
    admin_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    target: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Free-form JSON string with action-specific context (e.g., reason, old/new values)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    def __repr__(self) -> str:
        return f"<AdminLog action={self.action} admin={self.admin_telegram_id}>"


# ---------------------------------------------------------------------------
# Mirror models — tables owned by the bot, accessed by admin-mini-app
# ---------------------------------------------------------------------------


class AdminSession(Base):
    """Mirror of the bot's ``admin_sessions`` table.

    The bot creates and owns the table schema (including the FK to
    ``users.id``).  The admin-mini-app writes to it when an admin saves
    panel credentials via ``PUT /api/settings`` so the bot can pick up
    the new credentials on its next panel request.

    This model MUST stay structurally compatible with
    ``bot/db/models.py:AdminSession``.  Alembic autogenerate will not
    create a duplicate migration because the table already exists.
    """

    __tablename__ = "admin_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    panel_url: Mapped[str] = mapped_column(String(512), nullable=False)
    encrypted_credentials: Mapped[str] = mapped_column(Text, nullable=False)
    session_cookie: Mapped[str | None] = mapped_column(Text, nullable=True)
    cookie_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return f"<AdminSession user_id={self.user_id} panel_url={self.panel_url}>"
