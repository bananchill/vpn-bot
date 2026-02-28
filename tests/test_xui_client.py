"""Tests for bot.services.xui_client."""

from __future__ import annotations

import httpx
import pytest

from bot.services.xui_client import (
    XUIAuthError,
    XUIClient,
    XUIConnectionError,
    XUIRequestError,
    XUIResponse,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ok_response(obj: object = None, msg: str = "") -> httpx.Response:
    """Build a fake httpx.Response with success=True."""
    return httpx.Response(
        status_code=200,
        json={"success": True, "msg": msg, "obj": obj},
    )


def _fail_response(msg: str = "error", status_code: int = 200) -> httpx.Response:
    """Build a fake httpx.Response with success=False."""
    return httpx.Response(
        status_code=status_code,
        json={"success": False, "msg": msg, "obj": None},
    )


# ---------------------------------------------------------------------------
# Tests: _parse_response
# ---------------------------------------------------------------------------


class TestParseResponse:
    def test_parse_success(self, panel_url: str) -> None:
        client = XUIClient(panel_url)
        resp = _ok_response(obj={"key": "value"})
        parsed = client._parse_response(resp)
        assert parsed == XUIResponse(success=True, msg="", obj={"key": "value"})

    def test_parse_failure(self, panel_url: str) -> None:
        client = XUIClient(panel_url)
        resp = _fail_response(msg="bad request")
        parsed = client._parse_response(resp)
        assert parsed.success is False
        assert parsed.msg == "bad request"

    def test_parse_invalid_json(self, panel_url: str) -> None:
        client = XUIClient(panel_url)
        resp = httpx.Response(status_code=200, text="not json")
        with pytest.raises(XUIRequestError, match="Invalid JSON"):
            client._parse_response(resp)


# ---------------------------------------------------------------------------
# Tests: login
# ---------------------------------------------------------------------------


class TestLogin:
    @pytest.mark.asyncio
    async def test_login_success(self, panel_url: str) -> None:
        transport = httpx.MockTransport(lambda request: _ok_response())
        client = XUIClient(panel_url)
        client._client = httpx.AsyncClient(transport=transport, base_url=panel_url)

        result = await client.login("admin", "password")
        assert result.success is True
        assert client._username == "admin"
        assert client._password == "password"
        await client.close()

    @pytest.mark.asyncio
    async def test_login_bad_credentials(self, panel_url: str) -> None:
        transport = httpx.MockTransport(
            lambda request: _fail_response("invalid credentials")
        )
        client = XUIClient(panel_url)
        client._client = httpx.AsyncClient(transport=transport, base_url=panel_url)

        with pytest.raises(XUIAuthError, match="Login failed"):
            await client.login("admin", "wrong")
        await client.close()

    @pytest.mark.asyncio
    async def test_login_connection_error(self, panel_url: str) -> None:
        def raise_connect_error(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("refused")

        transport = httpx.MockTransport(raise_connect_error)
        client = XUIClient(panel_url)
        client._client = httpx.AsyncClient(transport=transport, base_url=panel_url)

        with pytest.raises(XUIConnectionError, match="Cannot connect"):
            await client.login("admin", "password")
        await client.close()

    @pytest.mark.asyncio
    async def test_login_timeout(self, panel_url: str) -> None:
        def raise_timeout(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("timeout")

        transport = httpx.MockTransport(raise_timeout)
        client = XUIClient(panel_url)
        client._client = httpx.AsyncClient(transport=transport, base_url=panel_url)

        with pytest.raises(XUIConnectionError, match="timed out"):
            await client.login("admin", "password")
        await client.close()


# ---------------------------------------------------------------------------
# Tests: API methods
# ---------------------------------------------------------------------------


class TestAPIMethods:
    @pytest.mark.asyncio
    async def test_get_inbounds(self, panel_url: str) -> None:
        inbounds = [{"id": 1, "protocol": "vless"}]
        transport = httpx.MockTransport(lambda req: _ok_response(obj=inbounds))
        client = XUIClient(panel_url)
        client._client = httpx.AsyncClient(transport=transport, base_url=panel_url)

        result = await client.get_inbounds()
        assert result == inbounds
        await client.close()

    @pytest.mark.asyncio
    async def test_get_inbound(self, panel_url: str) -> None:
        inbound = {"id": 1, "protocol": "vless"}
        transport = httpx.MockTransport(lambda req: _ok_response(obj=inbound))
        client = XUIClient(panel_url)
        client._client = httpx.AsyncClient(transport=transport, base_url=panel_url)

        result = await client.get_inbound(1)
        assert result == inbound
        await client.close()

    @pytest.mark.asyncio
    async def test_add_client(self, panel_url: str) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return _ok_response()

        transport = httpx.MockTransport(handler)
        client = XUIClient(panel_url)
        client._client = httpx.AsyncClient(transport=transport, base_url=panel_url)

        result = await client.add_client(1, {"id": "test-uuid", "email": "user@test"})
        assert result.success is True
        await client.close()

    @pytest.mark.asyncio
    async def test_delete_client(self, panel_url: str) -> None:
        transport = httpx.MockTransport(lambda req: _ok_response())
        client = XUIClient(panel_url)
        client._client = httpx.AsyncClient(transport=transport, base_url=panel_url)

        result = await client.delete_client(1, "test-uuid")
        assert result.success is True
        await client.close()

    @pytest.mark.asyncio
    async def test_get_client_traffic(self, panel_url: str) -> None:
        traffic = {"up": 1000, "down": 5000}
        transport = httpx.MockTransport(lambda req: _ok_response(obj=traffic))
        client = XUIClient(panel_url)
        client._client = httpx.AsyncClient(transport=transport, base_url=panel_url)

        result = await client.get_client_traffic("user@test")
        assert result == traffic
        await client.close()

    @pytest.mark.asyncio
    async def test_reset_client_traffic(self, panel_url: str) -> None:
        transport = httpx.MockTransport(lambda req: _ok_response())
        client = XUIClient(panel_url)
        client._client = httpx.AsyncClient(transport=transport, base_url=panel_url)

        result = await client.reset_client_traffic(1, "user@test")
        assert result.success is True
        await client.close()

    @pytest.mark.asyncio
    async def test_update_client(self, panel_url: str) -> None:
        transport = httpx.MockTransport(lambda req: _ok_response())
        client = XUIClient(panel_url)
        client._client = httpx.AsyncClient(transport=transport, base_url=panel_url)

        result = await client.update_client("test-uuid", 1, {"id": "test-uuid", "email": "u@t"})
        assert result.success is True
        await client.close()

    @pytest.mark.asyncio
    async def test_get_client_ips(self, panel_url: str) -> None:
        ips = "1.2.3.4,5.6.7.8"
        transport = httpx.MockTransport(lambda req: _ok_response(obj=ips))
        client = XUIClient(panel_url)
        client._client = httpx.AsyncClient(transport=transport, base_url=panel_url)

        result = await client.get_client_ips("user@test")
        assert result == ips
        await client.close()


# ---------------------------------------------------------------------------
# Tests: auto-relogin
# ---------------------------------------------------------------------------


class TestAutoRelogin:
    @pytest.mark.asyncio
    async def test_relogin_on_401(self, panel_url: str) -> None:
        """Client should automatically re-login when it gets a 401."""
        call_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1

            # Login endpoint always succeeds
            if request.url.path == "/login":
                return _ok_response()

            # First API call returns 401, second succeeds
            if call_count <= 2:  # 1=login, 2=first API attempt
                return httpx.Response(status_code=401, json={"success": False, "msg": ""})
            return _ok_response(obj=[])

        transport = httpx.MockTransport(handler)
        client = XUIClient(panel_url)
        client._client = httpx.AsyncClient(transport=transport, base_url=panel_url)

        await client.login("admin", "password")
        result = await client.get_inbounds()
        assert result == []
        # login(1) + first attempt(2) + relogin(3) + retry(4)
        assert call_count == 4
        await client.close()

    @pytest.mark.asyncio
    async def test_relogin_on_api_auth_message(self, panel_url: str) -> None:
        """Client should relogin if the API response mentions auth failure."""
        call_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1

            if request.url.path == "/login":
                return _ok_response()

            if call_count <= 2:
                return _fail_response("session expired, please login")
            return _ok_response(obj=[{"id": 1}])

        transport = httpx.MockTransport(handler)
        client = XUIClient(panel_url)
        client._client = httpx.AsyncClient(transport=transport, base_url=panel_url)

        await client.login("admin", "password")
        result = await client.get_inbounds()
        assert len(result) == 1
        await client.close()

    @pytest.mark.asyncio
    async def test_no_relogin_without_credentials(self, panel_url: str) -> None:
        """Without stored credentials, auth errors should raise immediately."""
        transport = httpx.MockTransport(
            lambda req: httpx.Response(status_code=401, json={"success": False, "msg": ""})
        )
        client = XUIClient(panel_url)
        client._client = httpx.AsyncClient(transport=transport, base_url=panel_url)

        with pytest.raises(XUIAuthError, match="Session expired"):
            await client.get_inbounds()
        await client.close()


# ---------------------------------------------------------------------------
# Tests: error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_api_error_non_auth(self, panel_url: str) -> None:
        """Non-auth API errors should raise XUIRequestError."""
        transport = httpx.MockTransport(lambda req: _fail_response("some API error"))
        client = XUIClient(panel_url)
        client._client = httpx.AsyncClient(transport=transport, base_url=panel_url)

        with pytest.raises(XUIRequestError, match="some API error"):
            await client.get_inbounds()
        await client.close()

    @pytest.mark.asyncio
    async def test_http_error_status(self, panel_url: str) -> None:
        """HTTP 500 should raise XUIRequestError."""
        transport = httpx.MockTransport(
            lambda req: httpx.Response(status_code=500, text="Internal Server Error")
        )
        client = XUIClient(panel_url)
        client._client = httpx.AsyncClient(transport=transport, base_url=panel_url)

        with pytest.raises(XUIRequestError, match="HTTP 500"):
            await client.get_inbounds()
        await client.close()

    @pytest.mark.asyncio
    async def test_connection_timeout_on_request(self, panel_url: str) -> None:
        def raise_timeout(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("read timeout")

        transport = httpx.MockTransport(raise_timeout)
        client = XUIClient(panel_url)
        client._client = httpx.AsyncClient(transport=transport, base_url=panel_url)

        with pytest.raises(XUIConnectionError, match="timed out"):
            await client.get_inbounds()
        await client.close()


# ---------------------------------------------------------------------------
# Tests: context manager
# ---------------------------------------------------------------------------


class TestContextManager:
    @pytest.mark.asyncio
    async def test_context_manager(self, panel_url: str) -> None:
        async with XUIClient(panel_url) as client:
            assert client.base_url == panel_url

    @pytest.mark.asyncio
    async def test_trailing_slash_stripped(self) -> None:
        async with XUIClient("http://localhost:2053/") as client:
            assert client.base_url == "http://localhost:2053"


# ---------------------------------------------------------------------------
# Tests: get_inbounds returns empty list when obj is None
# ---------------------------------------------------------------------------


class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_get_inbounds_none_obj(self, panel_url: str) -> None:
        transport = httpx.MockTransport(
            lambda req: httpx.Response(
                status_code=200, json={"success": True, "msg": "", "obj": None}
            )
        )
        client = XUIClient(panel_url)
        client._client = httpx.AsyncClient(transport=transport, base_url=panel_url)

        result = await client.get_inbounds()
        assert result == []
        await client.close()
