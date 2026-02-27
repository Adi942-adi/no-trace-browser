from __future__ import annotations

import pytest
from PyQt5.QtCore import QUrl
from PyQt5.QtWidgets import QMessageBox, QWidget

from ghost_browser.browser import BrowserWindow
from ghost_browser.settings import AppSettings


class _DummySignal:
    def __init__(self) -> None:
        self._callbacks = []

    def connect(self, callback) -> None:
        self._callbacks.append(callback)


class _DummyCookieStore:
    def __init__(self) -> None:
        self.cleared = False

    def deleteAllCookies(self) -> None:  # noqa: N802 (Qt-style API emulation)
        self.cleared = True


class _FakeProfile:
    def __init__(self) -> None:
        self.downloadRequested = _DummySignal()
        self._cookie_store = _DummyCookieStore()
        self.cache_cleared = False
        self.user_agent = ""

    def clearHttpCache(self) -> None:  # noqa: N802
        self.cache_cleared = True

    def cookieStore(self) -> _DummyCookieStore:  # noqa: N802
        return self._cookie_store

    def setHttpUserAgent(self, user_agent: str) -> None:  # noqa: N802
        self.user_agent = user_agent


class _DummyBrowserView(QWidget):
    def __init__(self, url: QUrl, parent=None) -> None:
        super().__init__(parent)
        self._url = url

    def url(self) -> QUrl:
        return self._url

    def setUrl(self, url: QUrl) -> None:  # noqa: N802
        self._url = url

    def title(self) -> str:
        return self._url.toString()

    def back(self) -> None:
        return None

    def forward(self) -> None:
        return None

    def reload(self) -> None:
        return None

    def stop(self) -> None:
        return None


@pytest.fixture()
def patched_window(qtbot, monkeypatch):
    def _create_new_tab(self, url=None, make_current=True):
        target = QUrl(url) if isinstance(url, str) else (url or QUrl(self.start_url))
        view = _DummyBrowserView(target, self)
        index = self.tabs.addTab(view, "New Tab")
        if make_current:
            self.tabs.setCurrentIndex(index)
        return view

    def _current_view(self):
        return self.tabs.currentWidget()

    def _tab_view(self, index):
        return self.tabs.widget(index)

    monkeypatch.setattr(BrowserWindow, "create_new_tab", _create_new_tab)
    monkeypatch.setattr(BrowserWindow, "current_view", _current_view)
    monkeypatch.setattr(BrowserWindow, "_tab_view", _tab_view)

    profile = _FakeProfile()
    window = BrowserWindow(profile=profile, start_url="about:blank", settings=AppSettings())
    qtbot.addWidget(window)
    window.show()
    return window, profile


def test_close_other_tabs_keeps_active_tab(patched_window):
    window, _profile = patched_window
    window.create_new_tab("https://example.com", make_current=True)
    window.create_new_tab("https://openai.com", make_current=True)

    keep_index = window.tabs.currentIndex()
    keep_url = window.tabs.currentWidget().url().toString()
    window.close_other_tabs(keep_index)

    assert window.tabs.count() == 1
    assert window.tabs.currentWidget().url().toString() == keep_url


def test_reopen_closed_tab_restores_url(patched_window):
    window, _profile = patched_window
    window.create_new_tab("https://example.com", make_current=True)
    window.close_current_tab()

    window.reopen_last_closed_tab()

    assert window.tabs.currentWidget().url().toString() == "https://example.com"


def test_start_new_session_clears_tabs_and_profile_data(patched_window, monkeypatch):
    window, profile = patched_window
    window.create_new_tab("https://example.com", make_current=True)
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.Yes)

    window.start_new_session()

    assert window.tabs.count() == 1
    assert window.tabs.currentWidget().url().toString() == "about:blank"
    assert profile.cache_cleared is True
    assert profile.cookieStore().cleared is True
