"""HTTP client for the 3x-ui panel API.

Wraps aiohttp to handle authentication (session cookie), automatic
re-login on 401 responses, and consistent timeout/error handling.
All public methods raise PanelClientError on failure so callers
get a single exception type to catch.
"""

import logging
import time
from http import HTTPStatus

import aiohttp

logger = logging.getLogger(__name__)

_REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=10)


class PanelClientError(Exception):
    """Raised when the panel API returns an unexpected result or is unreachable."""


class PanelClient:
    """Async HTTP client for 3x-ui panel management operations.

    Usage::

        async with PanelClient(base_url, username, password) as client:
            users = await client.get_users()

    The client stores the session cookie obtained via ``login()`` and
    transparently retries a request once after re-authenticating when
    the panel responds with HTTP 401.
    """

    def __init__(self, base_url: str, username: str, password: str) -> None:
        # Strip trailing slash so path concatenation is predictable
        self._base_url = base_url.rstrip("/")
        self._username = username
        self._password = password
        self._session: aiohttp.ClientSession | None = None
        self._session_cookie: str | None = None

    # -- lifecycle ------------------------------------------------------------

    async def _ensure_session(self) -> aiohttp.ClientSession:
        """Lazily create the underlying aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=_REQUEST_TIMEOUT)
        return self._session

    async def close(self) -> None:
        """Close the underlying HTTP session and release resources."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def __aenter__(self) -> "PanelClient":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        await self.close()

    # -- authentication -------------------------------------------------------

    async def login(self) -> str:
        """Authenticate with the panel and store the session cookie.

        Returns:
            The raw session cookie value.

        Raises:
            PanelClientError: If credentials are rejected or the panel is
                unreachable.
        """
        session = await self._ensure_session()
        url = f"{self._base_url}/login"
        payload = {"username": self._username, "password": self._password}

        try:
            async with session.post(url, data=payload) as resp:
                if resp.status != HTTPStatus.OK:
                    body = await resp.text()
                    raise PanelClientError(
                        f"Login failed (HTTP {resp.status}): {body[:200]}"
                    )

                data = await resp.json()
                if not data.get("success"):
                    raise PanelClientError(
                        f"Login rejected: {data.get('msg', 'unknown reason')}"
                    )

                # 3x-ui returns the session id inside a Set-Cookie header
                cookie = resp.cookies.get("3x-ui")
                # Some panel builds return the cookie under "session"
                if cookie is None:
                    cookie = resp.cookies.get("session")
                if cookie is None:
                    raise PanelClientError("No session cookie in login response")

                self._session_cookie = cookie.value
                logger.info("Logged in to panel at %s", self._base_url)
                return self._session_cookie

        except aiohttp.ClientError as exc:
            raise PanelClientError(f"Connection error during login: {exc}") from exc

    # -- internal request helper ----------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        *,
        retry_auth: bool = True,
        **kwargs: object,
    ) -> dict:
        """Send an authenticated request, retrying once on 401.

        Args:
            method: HTTP method (GET, POST, etc.).
            path: URL path relative to the panel base URL.
            retry_auth: Whether to attempt re-login on a 401 response.
            **kwargs: Forwarded to ``aiohttp.ClientSession.request``.

        Returns:
            Parsed JSON response body as a dict.
        """
        if self._session_cookie is None:
            await self.login()

        session = await self._ensure_session()
        url = f"{self._base_url}{path}"
        cookies = {"3x-ui": self._session_cookie or ""}

        try:
            async with session.request(
                method, url, cookies=cookies, **kwargs
            ) as resp:
                if resp.status == HTTPStatus.UNAUTHORIZED and retry_auth:
                    logger.info("Session expired, re-authenticating")
                    await self.login()
                    # Retry the same request exactly once
                    return await self._request(
                        method, path, retry_auth=False, **kwargs
                    )

                if resp.status != HTTPStatus.OK:
                    body = await resp.text()
                    raise PanelClientError(
                        f"Panel API error (HTTP {resp.status}) on "
                        f"{method} {path}: {body[:300]}"
                    )

                return await resp.json()

        except aiohttp.ClientError as exc:
            raise PanelClientError(
                f"Connection error on {method} {path}: {exc}"
            ) from exc

    # -- public API -----------------------------------------------------------

    async def get_users(self) -> list[dict]:
        """Fetch all inbound client entries from the panel.

        Returns:
            A list of client dicts as reported by the 3x-ui API.
        """
        data = await self._request("GET", "/panel/api/inbounds/list")
        # 3x-ui wraps the payload under "obj"; flatten all clients
        inbounds: list[dict] = data.get("obj") or []
        clients: list[dict] = []
        for inbound in inbounds:
            for client in inbound.get("clientStats", []) or []:
                clients.append(client)
        return clients

    async def get_user_configs(self, user_id: str) -> list[dict]:
        """Return VPN configs belonging to a specific panel user.

        Args:
            user_id: The panel-side email / identifier of the user.

        Returns:
            A list of config dicts for the user.
        """
        data = await self._request(
            "GET", f"/panel/api/inbounds/getClientTraffics/{user_id}"
        )
        configs: list[dict] = data.get("obj") if data.get("obj") else []
        return configs if isinstance(configs, list) else [configs]

    async def enable_config(self, config_id: str) -> bool:
        """Enable a single VPN config by its panel ID.

        Returns:
            True if the panel acknowledged the change.
        """
        return await self._toggle_config(config_id, enable=True)

    async def disable_config(self, config_id: str) -> bool:
        """Disable a single VPN config by its panel ID.

        Returns:
            True if the panel acknowledged the change.
        """
        return await self._toggle_config(config_id, enable=False)

    async def _toggle_config(self, config_id: str, *, enable: bool) -> bool:
        """Toggle a single config's enabled state on the panel."""
        # Fetch current client IPs to confirm the config exists
        await self._request(
            "POST",
            f"/panel/api/inbounds/clientIps/{config_id}",
        )
        # For enable/disable we need to update the client settings
        # The actual endpoint depends on the inbound id and client email
        # Using the direct update endpoint
        action = "enable" if enable else "disable"
        logger.info("Toggling config %s → %s", config_id, action)

        result = await self._request(
            "POST",
            f"/panel/api/inbounds/updateClient/{config_id}",
            json={"enable": enable},
        )
        return bool(result.get("success"))

    async def disable_all_user_configs(self, user_id: str) -> bool:
        """Disable every config belonging to a panel user.

        Args:
            user_id: Panel-side user identifier (email).

        Returns:
            True if all configs were successfully disabled.
        """
        return await self._toggle_all_user_configs(user_id, enable=False)

    async def enable_all_user_configs(self, user_id: str) -> bool:
        """Enable every config belonging to a panel user.

        Args:
            user_id: Panel-side user identifier (email).

        Returns:
            True if all configs were successfully enabled.
        """
        return await self._toggle_all_user_configs(user_id, enable=True)

    async def _toggle_all_user_configs(
        self, user_id: str, *, enable: bool
    ) -> bool:
        """Iterate over a user's configs and toggle each one."""
        configs = await self.get_user_configs(user_id)
        if not configs:
            logger.info("No configs found for user %s", user_id)
            return True

        action = "enable" if enable else "disable"
        logger.info("Toggling all %d configs for user %s → %s",
                     len(configs), user_id, action)

        all_ok = True
        for cfg in configs:
            cfg_id = cfg.get("id") or cfg.get("email", "")
            try:
                result = await self._toggle_config(str(cfg_id), enable=enable)
                if not result:
                    all_ok = False
            except PanelClientError:
                logger.exception("Failed to %s config %s", action, cfg_id)
                all_ok = False

        return all_ok

    async def check_connection(self) -> tuple[bool, str]:
        """Verify that the panel is reachable and credentials are valid.

        Returns:
            A (success, message) tuple. ``success`` is True when login
            and a basic API call both succeed.
        """
        start = time.monotonic()
        try:
            await self.login()
            # Perform a lightweight API call to confirm the session works
            await self._request("GET", "/panel/api/inbounds/list")
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return True, f"OK ({elapsed_ms}ms)"
        except PanelClientError as exc:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            logger.warning("Panel connection check failed: %s", exc)
            return False, str(exc)
