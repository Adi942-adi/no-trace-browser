from __future__ import annotations

import atexit
import os
import shutil
import stat
import tempfile
from pathlib import Path
from typing import Optional

from PyQt5.QtWebEngineWidgets import QWebEngineProfile, QWebEngineSettings


def _make_writable_and_retry(func, path, _exc_info) -> None:
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except OSError:
        pass


class EphemeralProfileManager:
    def __init__(self, base_dir: str | None = None) -> None:
        self._cleaned = False
        self.root_path = self._create_root_path(base_dir)
        self.storage_path = self.root_path / "storage"
        self.cache_path = self.root_path / "cache"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.cache_path.mkdir(parents=True, exist_ok=True)
        atexit.register(self.cleanup)

    def create_qt_profile(
        self,
        parent=None,
        user_agent: Optional[str] = None,
    ) -> QWebEngineProfile:
        profile = QWebEngineProfile("ghost-ephemeral", parent)
        profile.setPersistentStoragePath(str(self.storage_path))
        profile.setCachePath(str(self.cache_path))
        profile.setPersistentCookiesPolicy(QWebEngineProfile.NoPersistentCookies)
        profile.setHttpCacheType(QWebEngineProfile.MemoryHttpCache)
        if user_agent:
            profile.setHttpUserAgent(user_agent)

        settings = profile.settings()
        settings.setAttribute(QWebEngineSettings.PluginsEnabled, False)
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, False)
        settings.setAttribute(QWebEngineSettings.FullScreenSupportEnabled, True)
        return profile

    def cleanup(self) -> None:
        if self._cleaned:
            return
        self._cleaned = True
        shutil.rmtree(self.root_path, ignore_errors=True, onerror=_make_writable_and_retry)

    @staticmethod
    def _create_root_path(base_dir: str | None) -> Path:
        target_dir = None
        if base_dir:
            expanded = Path(base_dir).expanduser().resolve()
            expanded.mkdir(parents=True, exist_ok=True)
            target_dir = str(expanded)
        path = tempfile.mkdtemp(prefix="ghost-profile-", dir=target_dir)
        return Path(path)
