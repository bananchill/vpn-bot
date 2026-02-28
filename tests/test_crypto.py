"""Tests for bot.services.crypto."""

import pytest

from bot.services.crypto import decrypt_credentials, encrypt_credentials


class TestCrypto:
    def test_encrypt_decrypt_roundtrip(self) -> None:
        encrypted = encrypt_credentials("admin", "secret123")
        result = decrypt_credentials(encrypted)
        assert result == {"username": "admin", "password": "secret123"}

    def test_decrypt_invalid_token(self) -> None:
        with pytest.raises(ValueError, match="Failed to decrypt"):
            decrypt_credentials("this-is-not-valid")

    def test_different_encryptions_differ(self) -> None:
        enc1 = encrypt_credentials("admin", "pass")
        enc2 = encrypt_credentials("admin", "pass")
        # Fernet includes a timestamp, so two encryptions of the same
        # plaintext produce different ciphertexts
        assert enc1 != enc2

    def test_decrypt_both_yield_same(self) -> None:
        enc1 = encrypt_credentials("user", "pw")
        enc2 = encrypt_credentials("user", "pw")
        assert decrypt_credentials(enc1) == decrypt_credentials(enc2)
