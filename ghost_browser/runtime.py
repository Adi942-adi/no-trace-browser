from __future__ import annotations

import os
from typing import List


def build_chromium_flags(proxy_url: str | None = None) -> List[str]:
    flags = [
        "--incognito",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-sync",
        "--disable-default-apps",
        "--disable-background-networking",
        "--metrics-recording-only",
        "--password-store=basic",
        "--use-mock-keychain",
    ]
    if proxy_url:
        flags.append(f"--proxy-server={proxy_url}")
    return flags


def configure_chromium_environment(proxy_url: str | None = None) -> None:
    generated_flags = " ".join(build_chromium_flags(proxy_url))
    existing_flags = os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS", "").strip()
    if existing_flags:
        os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = f"{existing_flags} {generated_flags}".strip()
    else:
        os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = generated_flags
