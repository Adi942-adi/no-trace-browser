from pathlib import Path
from uuid import uuid4

from ghost_browser.settings import (
    AppSettings,
    DOWNLOAD_MODE_AUTO,
    PROXY_MODE_CUSTOM,
    PROXY_MODE_NONE,
    SettingsStore,
)


def test_settings_normalization_custom_proxy_requires_url():
    settings = AppSettings(proxy_mode=PROXY_MODE_CUSTOM, custom_proxy_url="")
    normalized = settings.normalized()
    assert normalized.proxy_mode == PROXY_MODE_NONE


def test_settings_store_roundtrip():
    temp_root = Path(".test-temp")
    temp_root.mkdir(parents=True, exist_ok=True)
    settings_file = temp_root / f"settings-{uuid4().hex}.json"
    store = SettingsStore(settings_file)

    original = AppSettings(
        startup_url="about:blank",
        download_dir=str(temp_root),
        proxy_mode=PROXY_MODE_CUSTOM,
        custom_proxy_url="socks5://127.0.0.1:9050",
        user_agent="UA-Test",
        download_mode=DOWNLOAD_MODE_AUTO,
    )
    store.save(original)

    loaded = store.load()
    assert loaded.startup_url == "about:blank"
    assert loaded.proxy_mode == PROXY_MODE_CUSTOM
    assert loaded.custom_proxy_url == "socks5://127.0.0.1:9050"
    assert loaded.download_mode == DOWNLOAD_MODE_AUTO
