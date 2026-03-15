"""SQLAlchemy ORM models."""

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.db.base import Base


class BotSettingsRecord(Base):
    """Read-only mirror of the ``bot_settings`` table managed by admin-mini-app.

    Singleton row (id=1) storing panel connection credentials and bot token.
    Sensitive fields (panel_password, client_bot_token) are Fernet-encrypted.
    """

    __tablename__ = "bot_settings"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    panel_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    panel_sub_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    panel_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    panel_password: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    owner_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    client_bot_token: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<BotSettingsRecord id={self.id} panel_url={self.panel_url}>"


class AdminRecord(Base):
    """Read-only mirror of the ``admins`` table managed by admin-mini-app.

    The bot uses this model to check admin rights via a direct SELECT
    against the shared PostgreSQL database. The admin-mini-app owns writes
    to this table; the bot only reads from it.

    Named ``AdminRecord`` (not ``Admin``) to avoid collision with the
    ``AdminSession`` model and aiogram's own ``Admin`` type in tests.
    """

    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, nullable=False
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<AdminRecord telegram_id={self.telegram_id} role={self.role}>"


class User(Base):
    """Telegram user."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    admin_session: Mapped["AdminSession | None"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    configs: Mapped[list["Config"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    subscriptions: Mapped[list["Subscription"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User telegram_id={self.telegram_id} is_admin={self.is_admin}>"


class AdminSession(Base):
    """Stored admin credentials and session cookie for the 3x-ui panel."""

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

    user: Mapped["User"] = relationship(back_populates="admin_session")

    def __repr__(self) -> str:
        return f"<AdminSession user_id={self.user_id} panel_url={self.panel_url}>"


class Config(Base):
    """VPN configuration (client) linked to a user and an inbound."""

    __tablename__ = "configs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    inbound_id: Mapped[int] = mapped_column(Integer, nullable=False)
    client_id: Mapped[str] = mapped_column(String(36), nullable=False)  # UUID
    # 3x-ui subscription identifier (16 hex chars); used in /sub/{sub_id} URL
    sub_id: Mapped[str] = mapped_column(String(16), nullable=False, server_default="")
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    protocol: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="configs")

    def __repr__(self) -> str:
        return f"<Config email={self.email} protocol={self.protocol}>"


class Subscription(Base):
    """User subscription record — grants access to config creation."""

    __tablename__ = "subscriptions"
    __table_args__ = (
        Index("ix_subscriptions_user_expires", "user_id", "expires_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    source: Mapped[str] = mapped_column(String(20), nullable=False)  # "stars" / "ton" / "promo"
    promo_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Notification flags — prevent duplicate messages from the scheduler
    notified_3d: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notified_expired: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Retry flag — set when expiryTime sync to 3x-ui fails after payment
    configs_sync_pending: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="subscriptions")

    def __repr__(self) -> str:
        return (
            f"<Subscription user_id={self.user_id} "
            f"source={self.source} expires_at={self.expires_at}>"
        )


class PromoCode(Base):
    """Reusable promotional code for granting subscriptions."""

    __tablename__ = "promo_codes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    use_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
