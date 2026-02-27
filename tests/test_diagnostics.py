import socket

import pytest

from ghost_browser.diagnostics import parse_proxy_endpoint, run_proxy_diagnostic


def test_parse_proxy_endpoint():
    host, port = parse_proxy_endpoint("socks5://127.0.0.1:9050")
    assert host == "127.0.0.1"
    assert port == 9050


def test_parse_proxy_endpoint_requires_port():
    with pytest.raises(ValueError):
        parse_proxy_endpoint("socks5://127.0.0.1")


def test_run_proxy_diagnostic_failure(monkeypatch):
    def _raise(*_args, **_kwargs):
        raise OSError("connection refused")

    monkeypatch.setattr(socket, "create_connection", _raise)
    result = run_proxy_diagnostic("socks5://127.0.0.1:9050", timeout_seconds=0.2)
    assert result.ok is False
    assert "connection refused" in result.message
