"""VPN connection link generators for various protocols."""

from __future__ import annotations

import base64
import json
import logging
from typing import Any
from urllib.parse import quote, urlencode

logger = logging.getLogger(__name__)


def generate_subscription_url(panel_url: str, sub_id: str) -> str:
    """Generate a subscription URL for all client configs.

    The subscription URL allows V2Ray/Xray clients to fetch all configs
    associated with the given subId from the panel in a single request.

    Args:
        panel_url: Base panel URL (e.g. "http://host:2053").
        sub_id: 3x-ui subscription identifier (16 hex chars, separate from UUID).

    Returns:
        Subscription URL in the format ``{panel_url}/sub/{sub_id}``.
    """
    return f"{panel_url.rstrip('/')}/sub/{sub_id}"


def generate_vless_link(
    uuid: str,
    server: str,
    port: int,
    remark: str,
    *,
    flow: str = "",
    security: str = "reality",
    sni: str = "",
    fingerprint: str = "chrome",
    public_key: str = "",
    short_id: str = "",
    spider_x: str = "",
    mldsa65_verify: str = "",
    network: str = "tcp",
    header_type: str = "none",
) -> str:
    """Generate a VLESS connection link.

    Format: vless://{uuid}@{server}:{port}?params#{remark}
    """
    params: dict[str, str] = {
        "type": network,
        "encryption": "none",
        "security": security,
    }
    if flow:
        params["flow"] = flow
    if sni:
        params["sni"] = sni
    if fingerprint:
        params["fp"] = fingerprint
    if public_key:
        params["pbk"] = public_key
    if short_id:
        params["sid"] = short_id
    if spider_x:
        params["spx"] = spider_x
    if mldsa65_verify:
        params["pqv"] = mldsa65_verify
    if header_type and header_type != "none":
        params["headerType"] = header_type

    query = urlencode(params)
    return f"vless://{uuid}@{server}:{port}?{query}#{quote(remark)}"


def generate_vmess_link(
    uuid: str,
    server: str,
    port: int,
    remark: str,
    *,
    aid: int = 0,
    network: str = "tcp",
    tls: str = "",
    sni: str = "",
    header_type: str = "none",
) -> str:
    """Generate a VMess connection link.

    Format: vmess://base64({json_config})
    """
    config = {
        "v": "2",
        "ps": remark,
        "add": server,
        "port": str(port),
        "id": uuid,
        "aid": str(aid),
        "scy": "auto",
        "net": network,
        "type": header_type,
        "host": sni,
        "path": "",
        "tls": tls,
        "sni": sni,
    }
    json_str = json.dumps(config, separators=(",", ":"))
    encoded = base64.urlsafe_b64encode(json_str.encode()).decode()
    return f"vmess://{encoded}"


def generate_trojan_link(
    password: str,
    server: str,
    port: int,
    remark: str,
    *,
    security: str = "tls",
    sni: str = "",
    fingerprint: str = "chrome",
    network: str = "tcp",
    header_type: str = "none",
) -> str:
    """Generate a Trojan connection link.

    Format: trojan://{password}@{server}:{port}?params#{remark}
    """
    params: dict[str, str] = {
        "type": network,
        "security": security,
    }
    if sni:
        params["sni"] = sni
    if fingerprint:
        params["fp"] = fingerprint
    if header_type and header_type != "none":
        params["headerType"] = header_type

    query = urlencode(params)
    return f"trojan://{password}@{server}:{port}?{query}#{quote(remark)}"


def generate_link_from_inbound(
    inbound: dict[str, Any],
    client_id: str,
    remark: str,
    *,
    server_host: str = "",
) -> str:
    """Generate a connection link by parsing inbound settings.

    Args:
        inbound: Full inbound dict from the 3x-ui API.
        client_id: UUID of the client.
        remark: Human-readable name for the config.
        server_host: Fallback server address when inbound listen is empty
            (e.g. the panel's public IP extracted from PANEL_URL).

    Returns:
        Connection link string.

    Raises:
        ValueError: If the protocol is not supported.
    """
    protocol = inbound.get("protocol", "")
    port = inbound.get("port", 443)

    # Parse settings JSON
    settings_raw = inbound.get("settings", "{}")
    settings = json.loads(settings_raw) if isinstance(settings_raw, str) else settings_raw

    # Parse stream settings JSON
    stream_raw = inbound.get("streamSettings", "{}")
    stream = json.loads(stream_raw) if isinstance(stream_raw, str) else stream_raw

    # When listen is empty the inbound accepts on all interfaces;
    # use the caller-supplied server_host (panel's public IP) as fallback.
    server = inbound.get("listen", "") or server_host
    network = stream.get("network", "tcp")
    security = stream.get("security", "none")

    # Extract TLS/Reality settings
    tls_settings = stream.get("realitySettings") or stream.get("tlsSettings") or {}
    server_names = tls_settings.get("serverNames", [])
    sni = server_names[0] if server_names else tls_settings.get("serverName", "")

    # Reality-specific settings
    reality_settings = tls_settings.get("settings", {})
    public_key = reality_settings.get("publicKey", "")
    short_ids = tls_settings.get("shortIds", [])
    short_id = short_ids[0] if short_ids else ""
    fingerprint = reality_settings.get("fingerprint", "chrome")
    spider_x = reality_settings.get("spiderX", "")
    mldsa65_verify = reality_settings.get("mldsa65Verify", "")

    # Find the specific client to get flow
    clients = settings.get("clients", [])
    client_flow = ""
    for client in clients:
        if client.get("id") == client_id or client.get("password") == client_id:
            client_flow = client.get("flow", "")
            break

    if protocol == "vless":
        return generate_vless_link(
            uuid=client_id,
            server=server,
            port=port,
            remark=remark,
            flow=client_flow,
            security=security,
            sni=sni,
            fingerprint=fingerprint,
            public_key=public_key,
            short_id=short_id,
            spider_x=spider_x,
            mldsa65_verify=mldsa65_verify,
            network=network,
        )
    elif protocol == "vmess":
        tls_value = "tls" if security == "tls" else ""
        return generate_vmess_link(
            uuid=client_id,
            server=server,
            port=port,
            remark=remark,
            network=network,
            tls=tls_value,
            sni=sni,
        )
    elif protocol == "trojan":
        return generate_trojan_link(
            password=client_id,
            server=server,
            port=port,
            remark=remark,
            security=security,
            sni=sni,
            fingerprint=fingerprint,
            network=network,
        )
    else:
        raise ValueError(f"Unsupported protocol: {protocol}")
