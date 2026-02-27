from __future__ import annotations

from pathlib import Path
from typing import Dict

from PyQt5.QtCore import Qt
from PyQt5.QtWebEngineWidgets import QWebEngineDownloadItem
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QDockWidget,
    QFileDialog,
    QHBoxLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .settings import DOWNLOAD_MODE_AUTO, DOWNLOAD_MODE_EPHEMERAL, DOWNLOAD_MODE_PROMPT


class DownloadPanel(QDockWidget):
    def __init__(
        self,
        parent=None,
        default_download_dir: str | None = None,
        download_mode: str = DOWNLOAD_MODE_PROMPT,
        ephemeral_download_dir: str | None = None,
    ) -> None:
        super().__init__("Downloads", parent)
        self._downloads: Dict[int, QWebEngineDownloadItem] = {}
        self._rows: Dict[int, int] = {}
        self.default_download_dir = Path(default_download_dir).expanduser() if default_download_dir else None
        self.ephemeral_download_dir = (
            Path(ephemeral_download_dir).expanduser() if ephemeral_download_dir else None
        )
        self.download_mode = download_mode
        self.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetClosable)
        self.setAllowedAreas(Qt.BottomDockWidgetArea | Qt.TopDockWidgetArea)
        self._setup_ui()

    def _setup_ui(self) -> None:
        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(8, 8, 8, 8)

        self.table = QTableWidget(0, 3, container)
        self.table.setHorizontalHeaderLabels(["File", "Status", "Progress"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        layout.addWidget(self.table)

        actions_layout = QHBoxLayout()
        clear_button = QPushButton("Clear List", container)
        clear_button.clicked.connect(self.clear_entries)
        actions_layout.addStretch(1)
        actions_layout.addWidget(clear_button)
        layout.addLayout(actions_layout)

        self.setWidget(container)

    def handle_download_requested(self, item: QWebEngineDownloadItem) -> None:
        target_path = self._resolve_target_path(item)
        if not target_path:
            item.cancel()
            return

        Path(target_path).parent.mkdir(parents=True, exist_ok=True)
        item.setPath(target_path)
        item.accept()

        key = id(item)
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(Path(target_path).name))
        self.table.setItem(row, 1, QTableWidgetItem("In progress"))
        self.table.setItem(row, 2, QTableWidgetItem("0%"))

        self._downloads[key] = item
        self._rows[key] = row

        item.downloadProgress.connect(
            lambda received, total, row_key=key: self._update_progress(row_key, received, total)
        )
        item.finished.connect(lambda row_key=key: self._mark_finished(row_key))
        self.show()

    def set_preferences(
        self,
        download_mode: str,
        default_download_dir: str | None = None,
        ephemeral_download_dir: str | None = None,
    ) -> None:
        self.download_mode = download_mode
        self.default_download_dir = Path(default_download_dir).expanduser() if default_download_dir else None
        self.ephemeral_download_dir = (
            Path(ephemeral_download_dir).expanduser() if ephemeral_download_dir else None
        )

    def _resolve_target_path(self, item: QWebEngineDownloadItem) -> str:
        suggested = Path(item.path()).name or "download.bin"
        if self.download_mode == DOWNLOAD_MODE_AUTO:
            base_dir = self.default_download_dir or Path.home() / "Downloads"
            return str(_next_available_path(base_dir / suggested))
        if self.download_mode == DOWNLOAD_MODE_EPHEMERAL:
            base_dir = self.ephemeral_download_dir or (Path.home() / "Downloads")
            return str(_next_available_path(base_dir / suggested))
        return self._ask_target_path(item)

    def _ask_target_path(self, item: QWebEngineDownloadItem) -> str:
        suggested = Path(item.path()).name or "download.bin"
        if self.default_download_dir:
            proposed = self.default_download_dir / suggested
        else:
            proposed = Path.home() / "Downloads" / suggested

        selected, _ = QFileDialog.getSaveFileName(self, "Save Download", str(proposed))
        return selected

    def _update_progress(self, key: int, received_bytes: int, total_bytes: int) -> None:
        row = self._rows.get(key)
        if row is None:
            return
        if total_bytes > 0:
            progress = int((received_bytes * 100) / total_bytes)
            progress_text = f"{progress}% ({_format_bytes(received_bytes)} / {_format_bytes(total_bytes)})"
        else:
            progress_text = _format_bytes(received_bytes)
        self.table.setItem(row, 2, QTableWidgetItem(progress_text))

    def _mark_finished(self, key: int) -> None:
        row = self._rows.get(key)
        item = self._downloads.get(key)
        if row is None or item is None:
            return
        state = item.state()
        state_map = {
            QWebEngineDownloadItem.DownloadCompleted: "Completed",
            QWebEngineDownloadItem.DownloadCancelled: "Cancelled",
            QWebEngineDownloadItem.DownloadInterrupted: "Interrupted",
            QWebEngineDownloadItem.DownloadInProgress: "In progress",
        }
        self.table.setItem(row, 1, QTableWidgetItem(state_map.get(state, "Finished")))
        self._downloads.pop(key, None)

    def clear_entries(self) -> None:
        self.table.setRowCount(0)
        self._downloads.clear()
        self._rows.clear()


def _format_bytes(num_bytes: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(num_bytes)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def _next_available_path(path: Path) -> Path:
    if not path.exists():
        return path
    counter = 1
    while True:
        candidate = path.with_name(f"{path.stem} ({counter}){path.suffix}")
        if not candidate.exists():
            return candidate
        counter += 1
