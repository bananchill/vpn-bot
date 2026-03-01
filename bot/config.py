"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Bot configuration backed by env vars / .env file."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    BOT_TOKEN: str
    DATABASE_URL: str
    DEFAULT_INBOUND_ID: int = 1
    PANEL_URL: str
    PANEL_USERNAME: str  # 3x-ui panel login
    PANEL_PASSWORD: str  # 3x-ui panel password
    ENCRYPTION_KEY: str  # Fernet key for encrypting admin credentials
    OWNER_ID: int  # Telegram user ID of the bot owner


settings = Settings()  # type: ignore[call-arg]
