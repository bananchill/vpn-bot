"""Async SQLAlchemy engine and session factory.

Base is available immediately for model definitions.
Engine and session factory are created lazily on first use,
so importing this module (e.g. from Alembic) does not require
the full set of bot env vars — only DATABASE_URL.
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

# Engine and session factory are created on first access to avoid
# triggering Settings validation when only Base is needed (e.g. Alembic
# importing models for metadata).
_engine = None
_async_session_factory = None


class Base(DeclarativeBase):
    """Base class for all ORM models."""


def _init_engine() -> None:
    """Create engine and session factory from settings (once)."""
    global _engine, _async_session_factory  # noqa: PLW0603
    if _engine is not None:
        return

    from bot.config import settings

    _engine = create_async_engine(settings.DATABASE_URL, echo=False)
    _async_session_factory = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


class _SessionFactoryProxy:
    """Transparent proxy that lazily initialises the real session factory.

    Allows existing code to keep using ``async_session_factory()`` without
    any import changes while deferring engine creation until the factory
    is actually called.
    """

    def __call__(self, **kwargs: object) -> AsyncSession:
        _init_engine()
        assert _async_session_factory is not None  # noqa: S101
        return _async_session_factory(**kwargs)

    def __getattr__(self, name: str) -> object:
        _init_engine()
        assert _async_session_factory is not None  # noqa: S101
        return getattr(_async_session_factory, name)


async_session_factory: async_sessionmaker[AsyncSession] = _SessionFactoryProxy()  # type: ignore[assignment]
