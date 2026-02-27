import pytest

from ghost_browser.cli import parse_args, parse_proxy_timeout, parse_window_size
from ghost_browser.settings import DOWNLOAD_MODE_AUTO


def test_parse_window_size_valid():
    assert parse_window_size("1280x720") == (1280, 720)


def test_parse_window_size_invalid():
    with pytest.raises(ValueError):
        parse_window_size("bad-value")


def test_proxy_timeout_limits():
    assert parse_proxy_timeout(1.0) == 1.0
    with pytest.raises(ValueError):
        parse_proxy_timeout(0)
    with pytest.raises(ValueError):
        parse_proxy_timeout(31)


def test_parse_args_defaults():
    args = parse_args([])
    assert args.start_url is None
    assert args.download_mode is None


def test_parse_args_download_mode():
    args = parse_args(["--download-mode", DOWNLOAD_MODE_AUTO])
    assert args.download_mode == DOWNLOAD_MODE_AUTO
