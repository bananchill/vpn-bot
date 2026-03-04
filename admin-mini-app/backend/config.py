"""Application configuration loaded from environment variables."""

import os

from dotenv import load_dotenv

load_dotenv()


def _require_env(name: str) -> str:
    """Return the value of a required environment variable or raise."""
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


# Database connection string (async driver: asyncpg)
DATABASE_URL: str = _require_env("DATABASE_URL")

# Telegram bot token for the admin bot (used to validate initData and run polling)
ADMIN_BOT_TOKEN: str = _require_env("ADMIN_BOT_TOKEN")

# Fernet symmetric key for encrypting sensitive fields in the database
FERNET_KEY: str = _require_env("FERNET_KEY")

# Public URL where the Mini App frontend is hosted (used for CORS and WebAppInfo)
WEBAPP_URL: str = _require_env("WEBAPP_URL")

# Dev mode: skip Telegram initData validation for local browser testing
DEV_MODE: bool = os.getenv("ADMIN_DEV_MODE", "").lower() in ("1", "true", "yes")

# Telegram ID to use as the fake admin in dev mode
DEV_ADMIN_ID: int = int(os.getenv("ADMIN_DEV_TELEGRAM_ID", "123456789"))
