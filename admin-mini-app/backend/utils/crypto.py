"""Fernet symmetric encryption for sensitive database fields.

Uses FERNET_KEY from the application config to encrypt/decrypt values such as
panel passwords and bot tokens before they are stored in the database.
"""

from config import FERNET_KEY
from cryptography.fernet import Fernet, InvalidToken

# Fernet requires a URL-safe base64-encoded 32-byte key
try:
    _fernet = Fernet(FERNET_KEY.encode())
except (ValueError, InvalidToken) as exc:
    raise RuntimeError(
        "Invalid FERNET_KEY: must be a URL-safe base64-encoded 32-byte key. "
        "Generate one with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
    ) from exc


def encrypt(value: str) -> str:
    """Encrypt a plaintext string and return the ciphertext as a UTF-8 string."""
    return _fernet.encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    """Decrypt a Fernet ciphertext string and return the original plaintext."""
    return _fernet.decrypt(value.encode()).decode()
