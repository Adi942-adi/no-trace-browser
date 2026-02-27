from __future__ import annotations

from typing import Optional

from PyQt5.QtCore import QPoint, QUrl, Qt
from PyQt5.QtGui import QIcon, QKeySequence
from PyQt5.QtWebEngineWidgets import QWebEnginePage, QWebEngineProfile, QWebEngineView
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QStatusBar,
    QTabWidget,
    QToolBar,
)

from .downloads import DownloadPanel
from .settings import (
    AppSettings,
    DOWNLOAD_MODE_PROMPT,
    PROXY_MODE_CUSTOM,
    PROXY_MODE_NONE,
    PROXY_MODE_TOR,
)
from .settings_dialog import SettingsDialog
from .utils import normalize_start_url, normalize_user_input


def _feature_set(*feature_names: str):
    features = set()
    for feature_name in feature_names:
        feature = getattr(QWebEnginePage, feature_name, None)
        if feature is not None:
            features.add(feature)
    return features


class BrowserPage(QWebEnginePage):
    _DENIED_FEATURES = _feature_set(
        "Geolocation",
        "MediaAudioCapture",
        "MediaVideoCapture",
        "MediaAudioVideoCapture",
        "DesktopVideoCapture",
        "DesktopAudioVideoCapture",
        "Notifications",
        "ClipboardReadWrite",
        "ClipboardRead",
    )

    def __init__(self, profile: QWebEngineProfile, window: "BrowserWindow") -> None:
        super().__init__(profile, window)
        self._window = window
        self.featurePermissionRequested.connect(self._handle_permission_request)

    def createWindow(self, _window_type):  # noqa: N802 (Qt override)
        return self._window.create_popup_page()

    def _handle_permission_request(self, security_origin, feature) -> None:
        if feature in self._DENIED_FEATURES:
            self.setFeaturePermission(security_origin, feature, QWebEnginePage.PermissionDeniedByUser)
            self._window.statusBar().showMessage("Blocked sensitive site permission request.", 2500)
            return
        self.setFeaturePermission(security_origin, feature, QWebEnginePage.PermissionDeniedByUser)


class BrowserWindow(QMainWindow):
    def __init__(
        self,
        profile: QWebEngineProfile,
        start_url: str,
        default_download_dir: Optional[str] = None,
        download_mode: str = DOWNLOAD_MODE_PROMPT,
        ephemeral_download_dir: Optional[str] = None,
        settings: Optional[AppSettings] = None,
        settings_store=None,
        proxy_mode: str = PROXY_MODE_NONE,
        proxy_reachable: Optional[bool] = None,
        tor_endpoint_reachable: Optional[bool] = None,
    ) -> None:
        super().__init__()
        self.profile = profile
        self.start_url = normalize_start_url(start_url, fallback="about:blank")
        self._closed_tabs: list[str] = []
        self._max_closed_tabs = 20
        self._settings = settings.normalized() if settings else AppSettings()
        self._settings_store = settings_store
        self._proxy_mode = proxy_mode
        self._proxy_reachable = proxy_reachable
        self._tor_endpoint_reachable = tor_endpoint_reachable
        self._proxy_pending_restart = False
        self._ephemeral_download_dir = ephemeral_download_dir

        self.setWindowTitle("Ghost Browser (Lab Edition)")
        self.setStatusBar(QStatusBar(self))

        self.tabs = QTabWidget(self)
        self.tabs.setDocumentMode(True)
        self.tabs.setMovable(True)
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self._on_current_tab_changed)
        self.tabs.tabBar().setContextMenuPolicy(Qt.CustomContextMenu)
        self.tabs.tabBar().customContextMenuRequested.connect(self._show_tab_context_menu)
        self.setCentralWidget(self.tabs)

        self.download_panel = DownloadPanel(
            self,
            default_download_dir=default_download_dir,
            download_mode=download_mode,
            ephemeral_download_dir=ephemeral_download_dir,
        )
        self.addDockWidget(Qt.BottomDockWidgetArea, self.download_panel)
        self.download_panel.hide()
        self.profile.downloadRequested.connect(self.download_panel.handle_download_requested)

        self.url_input = QLineEdit(self)
        self.url_input.returnPressed.connect(self.navigate_from_input)

        self._build_menu()
        self._build_toolbar()
        self._build_privacy_status()
        self.create_new_tab(self.start_url, make_current=True)

    def _build_menu(self) -> None:
        session_menu = self.menuBar().addMenu("Session")

        new_session_action = QAction("New Session", self)
        new_session_action.setShortcut(QKeySequence("Ctrl+Shift+N"))
        new_session_action.triggered.connect(self.start_new_session)
        session_menu.addAction(new_session_action)

        clear_data_action = QAction("Clear Session Data", self)
        clear_data_action.triggered.connect(self.clear_session_data)
        session_menu.addAction(clear_data_action)

        reopen_action = QAction("Reopen Closed Tab", self)
        reopen_action.setShortcut(QKeySequence("Ctrl+Shift+T"))
        reopen_action.triggered.connect(self.reopen_last_closed_tab)
        session_menu.addAction(reopen_action)

        settings_menu = self.menuBar().addMenu("Settings")
        preferences_action = QAction("Preferences", self)
        preferences_action.setShortcut(QKeySequence("Ctrl+,"))
        preferences_action.triggered.connect(self.open_settings_dialog)
        settings_menu.addAction(preferences_action)

    def _add_action(
        self,
        toolbar: QToolBar,
        label: str,
        callback,
        shortcut: Optional[QKeySequence] = None,
    ) -> QAction:
        action = QAction(label, self)
        if shortcut is not None:
            action.setShortcut(shortcut)
        action.triggered.connect(callback)
        toolbar.addAction(action)
        return action

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Navigation", self)
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        self._add_action(toolbar, "Back", lambda: self._current_view_action("back"), QKeySequence.Back)
        self._add_action(toolbar, "Forward", lambda: self._current_view_action("forward"), QKeySequence.Forward)
        self._add_action(toolbar, "Reload", lambda: self._current_view_action("reload"), QKeySequence.Refresh)
        self._add_action(toolbar, "Stop", lambda: self._current_view_action("stop"), QKeySequence("Esc"))
        self._add_action(toolbar, "Home", lambda: self.navigate_to(self.start_url))
        self._add_action(
            toolbar,
            "New Tab",
            lambda: self.create_new_tab(self.start_url, make_current=True),
            QKeySequence.AddTab,
        )
        self._add_action(toolbar, "Close Tab", self.close_current_tab, QKeySequence.Close)
        self._add_action(toolbar, "Reopen", self.reopen_last_closed_tab, QKeySequence("Ctrl+Shift+T"))
        self._add_action(toolbar, "Session", self.start_new_session, QKeySequence("Ctrl+Shift+N"))
        self._add_action(toolbar, "Downloads", self.toggle_downloads_panel)
        self._add_action(toolbar, "Settings", self.open_settings_dialog, QKeySequence("Ctrl+,"))

        toolbar.addWidget(self.url_input)

    def _build_privacy_status(self) -> None:
        self.proxy_status_label = QLabel(self)
        self.tor_status_label = QLabel(self)
        self.session_status_label = QLabel("Session: Ephemeral", self)
        self.statusBar().addPermanentWidget(self.proxy_status_label)
        self.statusBar().addPermanentWidget(self.tor_status_label)
        self.statusBar().addPermanentWidget(self.session_status_label)
        self._refresh_privacy_status()

    def create_new_tab(self, url: str | QUrl | None = None, make_current: bool = True) -> QWebEngineView:
        view = QWebEngineView(self)
        view.setPage(BrowserPage(self.profile, self))

        index = self.tabs.addTab(view, "New Tab")
        if make_current:
            self.tabs.setCurrentIndex(index)

        view.titleChanged.connect(lambda title, browser=view: self._update_tab_title(browser, title))
        view.iconChanged.connect(lambda icon, browser=view: self._update_tab_icon(browser, icon))
        view.urlChanged.connect(lambda page_url, browser=view: self._update_url_input(browser, page_url))
        view.loadStarted.connect(lambda browser=view: self._on_load_started(browser))
        view.loadFinished.connect(lambda _ok, browser=view: self._on_load_finished(browser))

        target_url = QUrl(url) if isinstance(url, str) else (url or QUrl(self.start_url))
        view.setUrl(target_url)
        return view

    def create_popup_page(self) -> QWebEnginePage:
        popup = self.create_new_tab("about:blank", make_current=True)
        return popup.page()

    def close_tab(self, index: int, record_closed: bool = True, ensure_one: bool = True) -> None:
        if index < 0 or index >= self.tabs.count():
            return
        if record_closed:
            self._record_closed_tab(index)
        widget = self.tabs.widget(index)
        self.tabs.removeTab(index)
        if widget is not None:
            widget.deleteLater()
        if ensure_one and self.tabs.count() == 0:
            self.create_new_tab(self.start_url, make_current=True)

    def close_current_tab(self) -> None:
        index = self.tabs.currentIndex()
        if index >= 0:
            self.close_tab(index)

    def close_other_tabs(self, keep_index: int) -> None:
        keep_widget = self.tabs.widget(keep_index)
        for index in reversed(range(self.tabs.count())):
            if index != keep_index:
                self.close_tab(index, record_closed=True, ensure_one=False)
        if keep_widget is not None:
            self.tabs.setCurrentWidget(keep_widget)

    def close_tabs_to_right(self, from_index: int) -> None:
        for index in reversed(range(from_index + 1, self.tabs.count())):
            self.close_tab(index, record_closed=True, ensure_one=False)

    def navigate_from_input(self) -> None:
        normalized = normalize_user_input(self.url_input.text())
        if normalized:
            self.navigate_to(normalized)

    def navigate_to(self, url: str) -> None:
        current = self.current_view()
        if current is not None:
            current.setUrl(QUrl(url))

    def toggle_downloads_panel(self) -> None:
        self.download_panel.setVisible(not self.download_panel.isVisible())

    def duplicate_current_tab(self) -> None:
        current = self.current_view()
        if current is not None:
            self.create_new_tab(current.url(), make_current=True)

    def reopen_last_closed_tab(self) -> None:
        if not self._closed_tabs:
            self.statusBar().showMessage("No recently closed tabs.", 2000)
            return
        self.create_new_tab(self._closed_tabs.pop(), make_current=True)

    def clear_session_data(self, show_feedback: bool = True) -> None:
        self.profile.clearHttpCache()
        self.profile.cookieStore().deleteAllCookies()
        if show_feedback:
            self.statusBar().showMessage("Session cookies and cache cleared.", 3000)

    def start_new_session(self) -> None:
        response = QMessageBox.question(
            self,
            "New Session",
            "Close all tabs and clear current session cache/cookies?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if response != QMessageBox.Yes:
            return

        for index in reversed(range(self.tabs.count())):
            self.close_tab(index, record_closed=False, ensure_one=False)

        self._closed_tabs.clear()
        self.download_panel.clear_entries()
        self.clear_session_data(show_feedback=False)
        self.create_new_tab(self.start_url, make_current=True)
        self.statusBar().showMessage("Started a fresh session.", 3000)

    def open_settings_dialog(self) -> None:
        dialog = SettingsDialog(self._settings, self)
        if dialog.exec_() != QDialog.Accepted:
            return

        new_settings = dialog.to_settings()
        proxy_changed = (
            new_settings.proxy_mode != self._settings.proxy_mode
            or new_settings.custom_proxy_url != self._settings.custom_proxy_url
        )
        self._settings = new_settings
        if self._settings_store is not None:
            self._settings_store.save(new_settings)

        self.start_url = normalize_start_url(new_settings.startup_url, fallback="about:blank")
        self.download_panel.set_preferences(
            download_mode=new_settings.download_mode,
            default_download_dir=new_settings.download_dir or None,
            ephemeral_download_dir=self._ephemeral_download_dir,
        )
        self.profile.setHttpUserAgent(new_settings.user_agent or "")

        if proxy_changed:
            self._proxy_mode = new_settings.proxy_mode
            self._proxy_reachable = None
            self._tor_endpoint_reachable = None
            self._proxy_pending_restart = True
            QMessageBox.information(
                self,
                "Settings",
                "Proxy settings were saved. Restart Ghost Browser to apply proxy changes.",
            )

        self._refresh_privacy_status()
        self.statusBar().showMessage("Settings saved.", 2500)

    def current_view(self) -> Optional[QWebEngineView]:
        widget = self.tabs.currentWidget()
        if isinstance(widget, QWebEngineView):
            return widget
        return None

    def _current_view_action(self, action_name: str) -> None:
        current = self.current_view()
        if current is None:
            return
        action = getattr(current, action_name, None)
        if action:
            action()

    def _on_current_tab_changed(self, _index: int) -> None:
        current = self.current_view()
        if current is not None:
            self.url_input.setText(current.url().toString())
            self._update_window_title(current)

    def _update_tab_title(self, browser: QWebEngineView, title: str) -> None:
        index = self.tabs.indexOf(browser)
        if index >= 0:
            self.tabs.setTabText(index, title[:60] if title else "New Tab")
        if browser is self.current_view():
            self._update_window_title(browser)

    def _update_tab_icon(self, browser: QWebEngineView, icon: QIcon) -> None:
        index = self.tabs.indexOf(browser)
        if index >= 0:
            self.tabs.setTabIcon(index, icon)

    def _update_url_input(self, browser: QWebEngineView, url: QUrl) -> None:
        if browser is self.current_view():
            self.url_input.setText(url.toString())

    def _on_load_started(self, browser: QWebEngineView) -> None:
        if browser is self.current_view():
            self.statusBar().showMessage("Loading...", 1500)

    def _on_load_finished(self, browser: QWebEngineView) -> None:
        if browser is self.current_view():
            self.statusBar().clearMessage()
            self._update_window_title(browser)

    def _update_window_title(self, browser: QWebEngineView) -> None:
        title = browser.title() or "Ghost Browser (Lab Edition)"
        self.setWindowTitle(f"{title} - Ghost Browser (Lab Edition)")

    def _record_closed_tab(self, index: int) -> None:
        browser = self._tab_view(index)
        if browser is None:
            return
        url = browser.url().toString()
        if not url or url == "about:blank":
            return
        self._closed_tabs.append(url)
        if len(self._closed_tabs) > self._max_closed_tabs:
            self._closed_tabs = self._closed_tabs[-self._max_closed_tabs :]

    def _tab_view(self, index: int) -> Optional[QWebEngineView]:
        widget = self.tabs.widget(index)
        if isinstance(widget, QWebEngineView):
            return widget
        return None

    def _copy_tab_url(self, index: int) -> None:
        browser = self._tab_view(index)
        if browser is None:
            return
        QApplication.clipboard().setText(browser.url().toString())
        self.statusBar().showMessage("Copied tab URL.", 1500)

    def _show_tab_context_menu(self, position: QPoint) -> None:
        tab_bar = self.tabs.tabBar()
        index = tab_bar.tabAt(position)
        if index < 0:
            return

        menu = QMenu(self)
        new_tab_action = menu.addAction("New Tab")
        duplicate_action = menu.addAction("Duplicate Tab")
        reload_action = menu.addAction("Reload Tab")
        copy_url_action = menu.addAction("Copy Tab URL")
        menu.addSeparator()
        close_action = menu.addAction("Close Tab")
        close_others_action = menu.addAction("Close Other Tabs")
        close_right_action = menu.addAction("Close Tabs to the Right")
        menu.addSeparator()
        reopen_action = menu.addAction("Reopen Closed Tab")

        duplicate_action.setEnabled(self._tab_view(index) is not None)
        close_others_action.setEnabled(self.tabs.count() > 1)
        close_right_action.setEnabled(index < self.tabs.count() - 1)
        reopen_action.setEnabled(bool(self._closed_tabs))

        selected = menu.exec_(tab_bar.mapToGlobal(position))
        if selected is None:
            return
        if selected is new_tab_action:
            self.create_new_tab(self.start_url, make_current=True)
        elif selected is duplicate_action:
            browser = self._tab_view(index)
            if browser is not None:
                self.create_new_tab(browser.url(), make_current=True)
        elif selected is reload_action:
            browser = self._tab_view(index)
            if browser is not None:
                browser.reload()
        elif selected is copy_url_action:
            self._copy_tab_url(index)
        elif selected is close_action:
            self.close_tab(index, record_closed=True, ensure_one=True)
        elif selected is close_others_action:
            self.close_other_tabs(index)
        elif selected is close_right_action:
            self.close_tabs_to_right(index)
        elif selected is reopen_action:
            self.reopen_last_closed_tab()

    def _refresh_privacy_status(self) -> None:
        if self._proxy_pending_restart:
            self._set_status_chip(self.proxy_status_label, "Proxy: pending restart", "#d08700")
            self._set_status_chip(self.tor_status_label, "Tor endpoint: pending restart", "#d08700")
            self._set_status_chip(self.session_status_label, "Session: Ephemeral", "#2f855a")
            return

        if self._proxy_mode == PROXY_MODE_NONE:
            self._set_status_chip(self.proxy_status_label, "Proxy: Off", "#666666")
        elif self._proxy_reachable is True:
            self._set_status_chip(self.proxy_status_label, "Proxy: On", "#2f855a")
        elif self._proxy_reachable is False:
            self._set_status_chip(self.proxy_status_label, "Proxy: Unreachable", "#c53030")
        else:
            self._set_status_chip(self.proxy_status_label, "Proxy: Unchecked", "#d08700")

        if self._proxy_mode == PROXY_MODE_TOR:
            if self._tor_endpoint_reachable is True:
                self._set_status_chip(self.tor_status_label, "Tor endpoint: Reachable", "#2f855a")
            elif self._tor_endpoint_reachable is False:
                self._set_status_chip(self.tor_status_label, "Tor endpoint: Unreachable", "#c53030")
            else:
                self._set_status_chip(self.tor_status_label, "Tor endpoint: Unchecked", "#d08700")
        elif self._proxy_mode == PROXY_MODE_CUSTOM:
            self._set_status_chip(self.tor_status_label, "Tor endpoint: N/A", "#666666")
        else:
            self._set_status_chip(self.tor_status_label, "Tor endpoint: Off", "#666666")

        self._set_status_chip(self.session_status_label, "Session: Ephemeral", "#2f855a")

    @staticmethod
    def _set_status_chip(label: QLabel, text: str, color: str) -> None:
        label.setText(text)
        label.setStyleSheet(
            f"QLabel {{ color: white; background: {color}; border-radius: 4px; padding: 2px 8px; }}"
        )
