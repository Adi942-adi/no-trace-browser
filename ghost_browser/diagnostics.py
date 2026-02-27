from __future__ import annotations

import socket
from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True)
class ProxyDiagnosticResult:
    ok: bool
    proxy_url: str
    endpoint: str
    message: str


def parse_proxy_endpoint(proxy_url: str) -> tuple[str, int]:
    parsed = urlparse(proxy_url)
    if not parsed.scheme:
        raise ValueError("Proxy URL must include a scheme, for example socks5://127.0.0.1:9050.")
    if parsed.hostname is None:
        raise ValueError("Proxy URL must include a hostname.")
    if parsed.port is None:
        raise ValueError("Proxy URL must include an explicit port.")
    return parsed.hostname, parsed.port


def run_proxy_diagnostic(proxy_url: str, timeout_seconds: float = 1.5) -> ProxyDiagnosticResult:
    host, port = parse_proxy_endpoint(proxy_url)
    endpoint = f"{host}:{port}"

    try:
        sock = socket.create_connection((host, port), timeout=timeout_seconds)
    except OSError as exc:
        message = f"Proxy diagnostic failed for {endpoint}: {exc}"
        return ProxyDiagnosticResult(
            ok=False,
            proxy_url=proxy_url,
            endpoint=endpoint,
            message=message,
        )
    sock.close()

    return ProxyDiagnosticResult(
        ok=True,
        proxy_url=proxy_url,
        endpoint=endpoint,
        message=f"Proxy diagnostic passed for {endpoint}.",
    )
