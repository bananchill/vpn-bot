"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Bot configuration backed by env vars / .env file."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    BOT_TOKEN: str
    DATABASE_URL: str
    DEFAULT_INBOUND_ID: int = 1
    PANEL_URL: str
    PANEL_SUB_URL: str  # Base URL for subscription links (e.g. https://host:2096)
    PANEL_USERNAME: str  # 3x-ui panel login
    PANEL_PASSWORD: str  # 3x-ui panel password
    ENCRYPTION_KEY: str  # Fernet key for encrypting admin credentials
    OWNER_ID: int  # Telegram user ID of the bot owner
    MAX_CONFIGS_PER_USER: int = 7

    # Subscription & payment settings
    SUBSCRIPTION_PRICE_RUB: int = 200
    SUBSCRIPTION_STARS: int = 120
    SUBSCRIPTION_DAYS: int = 30
    TON_PRICE_CACHE_TTL: int = 300  # seconds


settings = Settings()  # type: ignore[call-arg]
