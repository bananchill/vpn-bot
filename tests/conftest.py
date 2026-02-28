"""Shared test fixtures."""

from __future__ import annotations

import os

import pytest

# Set env vars BEFORE importing anything from bot.*
os.environ.setdefault("BOT_TOKEN", "000000000:AAFakeTokenForTesting")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///")
os.environ.setdefault("PANEL_URL", "http://localhost:2053")
# Valid Fernet key (base64-encoded 32 bytes)
os.environ.setdefault(
    "ENCRYPTION_KEY", "uD1gNjS5zNNNWL0fthTbmqp_0MO--Wpc3K-be1seUCY="
)


@pytest.fixture()
def panel_url() -> str:
    return "http://localhost:2053"
