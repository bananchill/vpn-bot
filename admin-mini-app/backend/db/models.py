"""SQLAlchemy ORM models for the admin mini-app."""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, func
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
    """Admin user with access to the mini-app panel."""

    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, nullable=False
    )
    # "owner" grants full access; "moderator" has limited access
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    added_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<Admin telegram_id={self.telegram_id} role={self.role}>"
