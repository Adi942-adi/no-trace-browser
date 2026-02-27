from ghost_browser.utils import normalize_start_url, normalize_user_input


def test_normalize_user_input_url():
    assert normalize_user_input("example.com") == "http://example.com"


def test_normalize_user_input_search():
    result = normalize_user_input("privacy browser")
    assert result.startswith("https://duckduckgo.com/?q=")
    assert "privacy+browser" in result


def test_normalize_start_url_fallback():
    assert normalize_start_url("", "https://duckduckgo.com") == "https://duckduckgo.com"
