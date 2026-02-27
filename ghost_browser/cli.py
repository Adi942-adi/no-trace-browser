from __future__ import annotations

import argparse
from typing import Sequence, Tuple

from .settings import (
    DEFAULT_START_URL,
    DOWNLOAD_MODE_AUTO,
    DOWNLOAD_MODE_EPHEMERAL,
    DOWNLOAD_MODE_PROMPT,
)

DEFAULT_WINDOW_SIZE = "1280x900"
DEFAULT_TOR_PROXY = "socks5://127.0.0.1:9050"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ghost-browser",
        description="Ephemeral privacy-focused lab browser based on Qt WebEngine.",
    )
    parser.add_argument(
        "--start-url",
        default=None,
        help=f"Initial page to open (default from saved settings, fallback: {DEFAULT_START_URL})",
    )
    parser.add_argument(
        "--proxy",
        help="Proxy URL, for example socks5://127.0.0.1:9050 or http://127.0.0.1:8080",
    )
    parser.add_argument(
        "--tor",
        action="store_true",
        help=f"Use local Tor SOCKS proxy ({DEFAULT_TOR_PROXY})",
    )
    parser.add_argument(
        "--profile-root",
        help="Directory where the ephemeral profile folder should be created (for example a RAM disk path).",
    )
    parser.add_argument(
        "--download-dir",
        help="Default download location shown in the save dialog.",
    )
    parser.add_argument(
        "--download-mode",
        choices=[DOWNLOAD_MODE_PROMPT, DOWNLOAD_MODE_AUTO, DOWNLOAD_MODE_EPHEMERAL],
        help="Download mode override: prompt, auto, or ephemeral.",
    )
    parser.add_argument(
        "--user-agent",
        help="Override browser user agent.",
    )
    parser.add_argument(
        "--skip-proxy-check",
        action="store_true",
        help="Do not run startup proxy reachability diagnostics.",
    )
    parser.add_argument(
        "--strict-proxy",
        action="store_true",
        help="Exit with an error if proxy diagnostics fail.",
    )
    parser.add_argument(
        "--proxy-timeout",
        type=float,
        default=1.5,
        help="Proxy diagnostic timeout in seconds (default: 1.5).",
    )
    parser.add_argument(
        "--window-size",
        default=DEFAULT_WINDOW_SIZE,
        help=f"Initial window size in WIDTHxHEIGHT format (default: {DEFAULT_WINDOW_SIZE}).",
    )
    return parser


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    return build_parser().parse_args(argv)


def resolve_proxy(args: argparse.Namespace) -> str | None:
    if args.tor and args.proxy:
        raise ValueError("Use either --tor or --proxy, not both.")
    if args.tor:
        return DEFAULT_TOR_PROXY
    return args.proxy


def parse_window_size(raw: str) -> Tuple[int, int]:
    try:
        width_text, height_text = raw.lower().split("x", 1)
        width = int(width_text)
        height = int(height_text)
    except ValueError as exc:
        raise ValueError("Window size must be in WIDTHxHEIGHT format, for example 1280x900.") from exc

    if width < 640 or height < 480:
        raise ValueError("Window size must be at least 640x480.")
    return width, height


def parse_proxy_timeout(raw_value: float) -> float:
    if raw_value <= 0:
        raise ValueError("Proxy timeout must be greater than 0.")
    if raw_value > 30:
        raise ValueError("Proxy timeout must be less than or equal to 30 seconds.")
    return raw_value
