"""SQLAlchemy ORM models."""

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.db.base import Base


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
