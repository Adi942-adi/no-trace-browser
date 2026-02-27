from ghost_browser.runtime import build_chromium_flags


def test_build_flags_without_proxy():
    flags = build_chromium_flags()
    assert "--incognito" in flags
    assert not any(flag.startswith("--proxy-server=") for flag in flags)


def test_build_flags_with_proxy():
    flags = build_chromium_flags("socks5://127.0.0.1:9050")
    assert "--proxy-server=socks5://127.0.0.1:9050" in flags
