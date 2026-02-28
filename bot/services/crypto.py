"""Encryption utilities for storing admin credentials."""

import json
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from bot.config import settings


def _get_fernet() -> Fernet:
    """Create a Fernet instance from the configured key."""
    return Fernet(settings.ENCRYPTION_KEY.encode())


def encrypt_credentials(username: str, password: str) -> str:
    """Encrypt admin credentials and return a base64-encoded token string."""
    payload = json.dumps({"username": username, "password": password})
    return _get_fernet().encrypt(payload.encode()).decode()


def decrypt_credentials(encrypted: str) -> dict[str, Any]:
    """Decrypt credentials token and return {"username": ..., "password": ...}.

    Raises:
        ValueError: If the token is invalid or corrupted.
    """
    try:
        decrypted = _get_fernet().decrypt(encrypted.encode()).decode()
        return json.loads(decrypted)
    except (InvalidToken, json.JSONDecodeError) as exc:
        raise ValueError("Failed to decrypt credentials") from exc
