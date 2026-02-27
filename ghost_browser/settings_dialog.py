from __future__ import annotations

from pathlib import Path

from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .settings import (
    AppSettings,
    DOWNLOAD_MODE_AUTO,
    DOWNLOAD_MODE_EPHEMERAL,
    DOWNLOAD_MODE_PROMPT,
    PROXY_MODE_CUSTOM,
    PROXY_MODE_NONE,
    PROXY_MODE_TOR,
)


class SettingsDialog(QDialog):
    def __init__(self, current_settings: AppSettings, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self._current = current_settings.normalized()
        self._build_ui()
        self._load_current_settings()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        self.form = QFormLayout()
        self.startup_url_input = QLineEdit(self)
        self.startup_url_input.setPlaceholderText("about:blank")
        self.form.addRow("Startup URL", self.startup_url_input)

        download_container = QWidget(self)
        download_layout = QHBoxLayout(download_container)
        download_layout.setContentsMargins(0, 0, 0, 0)
        self.download_dir_input = QLineEdit(download_container)
        browse_button = QPushButton("Browse", download_container)
        browse_button.clicked.connect(self._pick_download_folder)
        download_layout.addWidget(self.download_dir_input)
        download_layout.addWidget(browse_button)
        self.form.addRow("Download folder", download_container)

        self.download_mode_combo = QComboBox(self)
        self.download_mode_combo.addItem("Prompt every time", DOWNLOAD_MODE_PROMPT)
        self.download_mode_combo.addItem("Auto-save to download folder", DOWNLOAD_MODE_AUTO)
        self.download_mode_combo.addItem("Ephemeral (auto-delete on exit)", DOWNLOAD_MODE_EPHEMERAL)
        self.form.addRow("Download mode", self.download_mode_combo)

        self.proxy_mode_combo = QComboBox(self)
        self.proxy_mode_combo.addItem("Off", PROXY_MODE_NONE)
        self.proxy_mode_combo.addItem("Tor (127.0.0.1:9050)", PROXY_MODE_TOR)
        self.proxy_mode_combo.addItem("Custom proxy", PROXY_MODE_CUSTOM)
        self.proxy_mode_combo.currentIndexChanged.connect(self._on_proxy_mode_changed)
        self.form.addRow("Proxy mode", self.proxy_mode_combo)

        self.custom_proxy_input = QLineEdit(self)
        self.custom_proxy_input.setPlaceholderText("socks5://127.0.0.1:9050")
        self.form.addRow("Custom proxy URL", self.custom_proxy_input)

        self.user_agent_input = QLineEdit(self)
        self.user_agent_input.setPlaceholderText("Leave empty to use default")
        self.form.addRow("User-Agent override", self.user_agent_input)

        tip = QLabel(
            "Proxy mode changes apply on next launch. Other settings apply immediately.",
            self,
        )
        tip.setWordWrap(True)
        self.form.addRow(tip)

        layout.addLayout(self.form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self._accept_with_validation)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _load_current_settings(self) -> None:
        self.startup_url_input.setText(self._current.startup_url)
        self.download_dir_input.setText(self._current.download_dir)
        self.custom_proxy_input.setText(self._current.custom_proxy_url)
        self.user_agent_input.setText(self._current.user_agent)
        self._set_combo_data(self.download_mode_combo, self._current.download_mode)
        self._set_combo_data(self.proxy_mode_combo, self._current.proxy_mode)
        self._on_proxy_mode_changed()

    def to_settings(self) -> AppSettings:
        return AppSettings(
            startup_url=self.startup_url_input.text().strip(),
            download_dir=self.download_dir_input.text().strip(),
            proxy_mode=self.proxy_mode_combo.currentData(),
            custom_proxy_url=self.custom_proxy_input.text().strip(),
            user_agent=self.user_agent_input.text().strip(),
            download_mode=self.download_mode_combo.currentData(),
        ).normalized()

    def _accept_with_validation(self) -> None:
        settings = self.to_settings()
        if settings.proxy_mode == PROXY_MODE_CUSTOM and not settings.custom_proxy_url:
            QMessageBox.warning(self, "Settings", "Custom proxy mode requires a proxy URL.")
            return
        if settings.download_dir and not Path(settings.download_dir).expanduser().exists():
            QMessageBox.warning(self, "Settings", "Selected download folder does not exist.")
            return
        self.accept()

    def _pick_download_folder(self) -> None:
        initial_dir = self.download_dir_input.text().strip()
        start = str(Path(initial_dir).expanduser()) if initial_dir else str(Path.home())
        chosen = QFileDialog.getExistingDirectory(self, "Select Download Folder", start)
        if chosen:
            self.download_dir_input.setText(chosen)

    def _on_proxy_mode_changed(self) -> None:
        is_custom = self.proxy_mode_combo.currentData() == PROXY_MODE_CUSTOM
        self.custom_proxy_input.setEnabled(is_custom)

    @staticmethod
    def _set_combo_data(combo: QComboBox, target_data: str) -> None:
        for idx in range(combo.count()):
            if combo.itemData(idx) == target_data:
                combo.setCurrentIndex(idx)
                return
