"""Telegram WebApp initData validation.

Implements the server-side signature check as described in the Telegram
Bot API documentation for Mini Apps. The initData query string is signed
by the bot token using HMAC-SHA256, and this module verifies that signature.
"""

import hashlib
import hmac
import json
from urllib.parse import parse_qs


def validate_init_data(init_data: str, bot_token: str) -> dict[str, str | int] | None:
    """Validate initData from a Telegram WebApp request.

    Args:
        init_data: Raw query-string sent by the Telegram Mini App client.
        bot_token: The bot token used to compute the expected HMAC signature.

    Returns:
        Parsed user data dict on success, or None if the signature is invalid
        or the hash is missing.
    """
    parsed = dict(parse_qs(init_data, keep_blank_values=True))

    received_hash = parsed.pop("hash", [None])[0]
    if not received_hash:
        return None

    # Build the data-check string: sorted key=value pairs joined by newlines
    data_check = "\n".join(
        f"{k}={v[0]}" for k, v in sorted(parsed.items())
    )

    # HMAC-SHA256: secret = HMAC("WebAppData", bot_token), then HMAC(secret, data_check)
    secret = hmac.new(
        b"WebAppData", bot_token.encode(), hashlib.sha256
    ).digest()
    calculated = hmac.new(
        secret, data_check.encode(), hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(calculated, received_hash):
        return None

    # Extract user JSON from the validated payload
    user_json = parsed.get("user", ["{}"])[0]
    user_data: dict[str, str | int] = json.loads(user_json)
    return user_data
