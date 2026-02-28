"""Async HTTP client for the 3x-ui panel API."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Typed exceptions
# ---------------------------------------------------------------------------


class XUIError(Exception):
    """Base exception for all 3x-ui API errors."""


class XUIAuthError(XUIError):
    """Authentication or session error."""


class XUIRequestError(XUIError):
    """Non-auth API error (bad request, server error, etc.)."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class XUIConnectionError(XUIError):
    """Network-level error (timeout, DNS, connection refused, etc.)."""


# ---------------------------------------------------------------------------
# API response wrapper
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class XUIResponse:
    """Parsed API response from the 3x-ui panel."""

    success: bool
    msg: str
    obj: Any = None


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


@dataclass
class XUIClient:
    """Async HTTP client for the 3x-ui panel.

    Usage::

        async with XUIClient("http://panel:2053") as xui:
            await xui.login("admin", "password")
            inbounds = await xui.get_inbounds()
    """

    base_url: str
    _username: str | None = field(default=None, repr=False)
    _password: str | None = field(default=None, repr=False)
    _client: httpx.AsyncClient = field(init=False, repr=False)

    def __post_init__(self) -> None:
        # Strip trailing slash for consistent URL joining
        self.base_url = self.base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(30.0),
            follow_redirects=True,
        )

    # -- context manager -----------------------------------------------------

    async def __aenter__(self) -> XUIClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    # -- internal helpers ----------------------------------------------------

    def _parse_response(self, response: httpx.Response) -> XUIResponse:
        """Parse the standard 3x-ui JSON envelope."""
        try:
            data = response.json()
        except (json.JSONDecodeError, ValueError) as exc:
            raise XUIRequestError(
                f"Invalid JSON in response: {response.text[:200]}",
                status_code=response.status_code,
            ) from exc

        return XUIResponse(
            success=data.get("success", False),
            msg=data.get("msg", ""),
            obj=data.get("obj"),
        )

    async def _request(
        self,
        method: str,
        path: str,
        *,
        auto_relogin: bool = True,
        **kwargs: Any,
    ) -> XUIResponse:
        """Execute an HTTP request with optional auto-relogin on 401."""
        try:
            response = await self._client.request(method, path, **kwargs)
        except httpx.TimeoutException as exc:
            raise XUIConnectionError(f"Request timed out: {path}") from exc
        except httpx.ConnectError as exc:
            raise XUIConnectionError(f"Connection failed: {exc}") from exc
        except httpx.HTTPError as exc:
            raise XUIConnectionError(f"HTTP error: {exc}") from exc

        # 3x-ui returns 200 even on auth failure in many cases,
        # but may also return 401 or redirect to login page.
        if response.status_code == 401 or (
            response.status_code == 307
            and "/login" in response.headers.get("location", "")
        ):
            if auto_relogin and self._username and self._password:
                logger.info("Session expired, attempting re-login")
                await self.login(self._username, self._password, _store_creds=False)
                return await self._request(method, path, auto_relogin=False, **kwargs)
            raise XUIAuthError("Session expired and auto-relogin is not possible")

        if response.status_code >= 400:
            raise XUIRequestError(
                f"HTTP {response.status_code}: {response.text[:200]}",
                status_code=response.status_code,
            )

        parsed = self._parse_response(response)

        # Some endpoints return success=false with an error message
        if not parsed.success:
            # Check if it's really an auth problem
            msg_lower = parsed.msg.lower()
            if "login" in msg_lower or "auth" in msg_lower or "session" in msg_lower:
                if auto_relogin and self._username and self._password:
                    logger.info("API reports auth failure, attempting re-login")
                    await self.login(self._username, self._password, _store_creds=False)
                    return await self._request(method, path, auto_relogin=False, **kwargs)
                raise XUIAuthError(parsed.msg)
            raise XUIRequestError(parsed.msg)

        return parsed

    # -- authentication ------------------------------------------------------

    async def login(
        self,
        username: str,
        password: str,
        *,
        _store_creds: bool = True,
    ) -> XUIResponse:
        """Authenticate with the 3x-ui panel.

        Stores the session cookie in the httpx client for subsequent requests.

        Raises:
            XUIAuthError: If credentials are invalid.
            XUIConnectionError: If the panel is unreachable.
        """
        if _store_creds:
            self._username = username
            self._password = password

        try:
            response = await self._client.post(
                "/login",
                data={"username": username, "password": password},
            )
        except httpx.TimeoutException as exc:
            raise XUIConnectionError("Login request timed out") from exc
        except httpx.ConnectError as exc:
            raise XUIConnectionError(f"Cannot connect to panel: {exc}") from exc
        except httpx.HTTPError as exc:
            raise XUIConnectionError(f"HTTP error during login: {exc}") from exc

        parsed = self._parse_response(response)
        if not parsed.success:
            raise XUIAuthError(f"Login failed: {parsed.msg}")

        logger.info("Successfully logged in to 3x-ui panel at %s", self.base_url)
        return parsed

    # -- inbound endpoints ---------------------------------------------------

    async def get_inbounds(self) -> list[dict[str, Any]]:
        """Return list of all inbounds."""
        resp = await self._request("GET", "/panel/api/inbounds/list")
        return resp.obj if resp.obj else []

    async def get_inbound(self, inbound_id: int) -> dict[str, Any]:
        """Return a single inbound by ID."""
        resp = await self._request("GET", f"/panel/api/inbounds/get/{inbound_id}")
        return resp.obj

    # -- client endpoints ----------------------------------------------------

    async def add_client(self, inbound_id: int, client_settings: dict[str, Any]) -> XUIResponse:
        """Add a client to an inbound.

        Args:
            inbound_id: Target inbound ID.
            client_settings: Dict with keys like id (uuid), email, flow, etc.
        """
        payload = {
            "id": inbound_id,
            "settings": json.dumps({"clients": [client_settings]}),
        }
        return await self._request("POST", "/panel/api/inbounds/addClient", data=payload)

    async def update_client(
        self, client_uuid: str, inbound_id: int, client_settings: dict[str, Any]
    ) -> XUIResponse:
        """Update an existing client."""
        payload = {
            "id": inbound_id,
            "settings": json.dumps({"clients": [client_settings]}),
        }
        return await self._request(
            "POST",
            f"/panel/api/inbounds/updateClient/{client_uuid}",
            data=payload,
        )

    async def delete_client(self, inbound_id: int, client_uuid: str) -> XUIResponse:
        """Delete a client from an inbound."""
        return await self._request(
            "POST",
            f"/panel/api/inbounds/{inbound_id}/delClient/{client_uuid}",
        )

    async def get_client_traffic(self, email: str) -> dict[str, Any]:
        """Get traffic statistics for a client by email."""
        resp = await self._request("GET", f"/panel/api/inbounds/getClientTraffics/{email}")
        return resp.obj

    async def get_client_ips(self, email: str) -> Any:
        """Get IPs that a client has connected from."""
        resp = await self._request("POST", f"/panel/api/inbounds/clientIps/{email}")
        return resp.obj

    async def reset_client_traffic(self, inbound_id: int, email: str) -> XUIResponse:
        """Reset traffic counters for a client."""
        return await self._request(
            "POST",
            f"/panel/api/inbounds/{inbound_id}/resetClientTraffic/{email}",
        )
