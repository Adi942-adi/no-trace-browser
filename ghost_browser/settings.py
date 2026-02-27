from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict

DEFAULT_START_URL = "about:blank"
PROXY_MODE_NONE = "none"
PROXY_MODE_TOR = "tor"
PROXY_MODE_CUSTOM = "custom"
DOWNLOAD_MODE_PROMPT = "prompt"
DOWNLOAD_MODE_AUTO = "auto"
DOWNLOAD_MODE_EPHEMERAL = "ephemeral"

VALID_PROXY_MODES = {PROXY_MODE_NONE, PROXY_MODE_TOR, PROXY_MODE_CUSTOM}
VALID_DOWNLOAD_MODES = {DOWNLOAD_MODE_PROMPT, DOWNLOAD_MODE_AUTO, DOWNLOAD_MODE_EPHEMERAL}


@dataclass
class AppSettings:
    startup_url: str = DEFAULT_START_URL
    download_dir: str = ""
    proxy_mode: str = PROXY_MODE_NONE
    custom_proxy_url: str = ""
    user_agent: str = ""
    download_mode: str = DOWNLOAD_MODE_PROMPT

    def normalized(self) -> "AppSettings":
        startup = (self.startup_url or "").strip() or DEFAULT_START_URL
        download_dir = (self.download_dir or "").strip()
        proxy_mode = self.proxy_mode if self.proxy_mode in VALID_PROXY_MODES else PROXY_MODE_NONE
        custom_proxy_url = (self.custom_proxy_url or "").strip()
        user_agent = (self.user_agent or "").strip()
        download_mode = self.download_mode if self.download_mode in VALID_DOWNLOAD_MODES else DOWNLOAD_MODE_PROMPT
        if proxy_mode == PROXY_MODE_CUSTOM and not custom_proxy_url:
            proxy_mode = PROXY_MODE_NONE

        return AppSettings(
            startup_url=startup,
            download_dir=download_dir,
            proxy_mode=proxy_mode,
            custom_proxy_url=custom_proxy_url,
            user_agent=user_agent,
            download_mode=download_mode,
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self.normalized())


class SettingsStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or default_settings_path()

    def load(self) -> AppSettings:
        if not self.path.exists():
            return AppSettings()

        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return AppSettings()

        if not isinstance(raw, dict):
            return AppSettings()

        return AppSettings(
            startup_url=_read_str(raw, "startup_url", DEFAULT_START_URL),
            download_dir=_read_str(raw, "download_dir", ""),
            proxy_mode=_read_str(raw, "proxy_mode", PROXY_MODE_NONE),
            custom_proxy_url=_read_str(raw, "custom_proxy_url", ""),
            user_agent=_read_str(raw, "user_agent", ""),
            download_mode=_read_str(raw, "download_mode", DOWNLOAD_MODE_PROMPT),
        ).normalized()

    def save(self, settings: AppSettings) -> None:
        normalized = settings.normalized()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(normalized.to_dict(), indent=2), encoding="utf-8")


def default_settings_path() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home()))
        return base / "GhostBrowserLab" / "settings.json"
    return Path.home() / ".config" / "ghost-browser-lab" / "settings.json"


def _read_str(raw: Dict[str, Any], key: str, fallback: str) -> str:
    value = raw.get(key, fallback)
    return value if isinstance(value, str) else fallback
