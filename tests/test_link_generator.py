"""Tests for bot.services.link_generator."""

import base64
import json

import pytest

from bot.services.link_generator import (
    generate_link_from_inbound,
    generate_trojan_link,
    generate_vless_link,
    generate_vmess_link,
)


class TestGenerateVlessLink:
    def test_basic_link(self) -> None:
        link = generate_vless_link(
            uuid="test-uuid",
            server="1.2.3.4",
            port=443,
            remark="my-config",
        )
        assert link.startswith("vless://test-uuid@1.2.3.4:443?")
        assert "my-config" in link
        assert "type=tcp" in link

    def test_with_reality(self) -> None:
        link = generate_vless_link(
            uuid="test-uuid",
            server="1.2.3.4",
            port=443,
            remark="test",
            security="reality",
            sni="example.com",
            public_key="pubkey123",
            short_id="abcd",
            flow="xtls-rprx-vision",
        )
        assert "security=reality" in link
        assert "sni=example.com" in link
        assert "pbk=pubkey123" in link
        assert "sid=abcd" in link
        assert "flow=xtls-rprx-vision" in link

    def test_remark_encoding(self) -> None:
        link = generate_vless_link(
            uuid="uuid",
            server="1.2.3.4",
            port=443,
            remark="my config name",
        )
        # Space should be percent-encoded
        assert "my%20config%20name" in link


class TestGenerateVmessLink:
    def test_basic_link(self) -> None:
        link = generate_vmess_link(
            uuid="test-uuid",
            server="1.2.3.4",
            port=443,
            remark="my-config",
        )
        assert link.startswith("vmess://")
        # Decode and verify
        encoded = link[len("vmess://"):]
        decoded = json.loads(base64.urlsafe_b64decode(encoded + "==").decode())
        assert decoded["id"] == "test-uuid"
        assert decoded["add"] == "1.2.3.4"
        assert decoded["port"] == "443"
        assert decoded["ps"] == "my-config"

    def test_with_tls(self) -> None:
        link = generate_vmess_link(
            uuid="uuid",
            server="1.2.3.4",
            port=443,
            remark="test",
            tls="tls",
            sni="example.com",
        )
        encoded = link[len("vmess://"):]
        decoded = json.loads(base64.urlsafe_b64decode(encoded + "==").decode())
        assert decoded["tls"] == "tls"
        assert decoded["sni"] == "example.com"


class TestGenerateTrojanLink:
    def test_basic_link(self) -> None:
        link = generate_trojan_link(
            password="secret",
            server="1.2.3.4",
            port=443,
            remark="test",
        )
        assert link.startswith("trojan://secret@1.2.3.4:443?")
        assert "test" in link
        assert "security=tls" in link


class TestGenerateLinkFromInbound:
    def test_vless_inbound(self) -> None:
        inbound = {
            "protocol": "vless",
            "port": 443,
            "listen": "1.2.3.4",
            "settings": json.dumps({
                "clients": [{"id": "client-uuid", "flow": "xtls-rprx-vision"}]
            }),
            "streamSettings": json.dumps({
                "network": "tcp",
                "security": "reality",
                "realitySettings": {
                    "serverNames": ["example.com"],
                    "settings": {
                        "publicKey": "pubkey",
                        "shortIds": ["abc"],
                        "fingerprint": "chrome",
                    },
                },
            }),
        }
        link = generate_link_from_inbound(inbound, "client-uuid", "test-config")
        assert link.startswith("vless://client-uuid@1.2.3.4:443?")
        assert "security=reality" in link
        assert "flow=xtls-rprx-vision" in link

    def test_vmess_inbound(self) -> None:
        inbound = {
            "protocol": "vmess",
            "port": 8080,
            "listen": "5.6.7.8",
            "settings": json.dumps({
                "clients": [{"id": "vmess-uuid"}]
            }),
            "streamSettings": json.dumps({
                "network": "ws",
                "security": "tls",
                "tlsSettings": {
                    "serverName": "example.com",
                },
            }),
        }
        link = generate_link_from_inbound(inbound, "vmess-uuid", "vmess-test")
        assert link.startswith("vmess://")

    def test_trojan_inbound(self) -> None:
        inbound = {
            "protocol": "trojan",
            "port": 443,
            "listen": "9.8.7.6",
            "settings": json.dumps({
                "clients": [{"password": "trojan-pass"}]
            }),
            "streamSettings": json.dumps({
                "network": "tcp",
                "security": "tls",
                "tlsSettings": {
                    "serverNames": ["trojan.example.com"],
                },
            }),
        }
        link = generate_link_from_inbound(inbound, "trojan-pass", "trojan-test")
        assert link.startswith("trojan://trojan-pass@9.8.7.6:443?")

    def test_unsupported_protocol(self) -> None:
        inbound = {
            "protocol": "shadowsocks",
            "port": 443,
            "listen": "1.2.3.4",
            "settings": "{}",
            "streamSettings": "{}",
        }
        with pytest.raises(ValueError, match="shadowsocks"):
            generate_link_from_inbound(inbound, "uuid", "test")

    def test_dict_settings(self) -> None:
        """Settings can be dicts instead of JSON strings."""
        inbound = {
            "protocol": "vless",
            "port": 443,
            "listen": "1.2.3.4",
            "settings": {"clients": [{"id": "uuid", "flow": ""}]},
            "streamSettings": {"network": "tcp", "security": "none"},
        }
        link = generate_link_from_inbound(inbound, "uuid", "test")
        assert link.startswith("vless://uuid@1.2.3.4:443?")
