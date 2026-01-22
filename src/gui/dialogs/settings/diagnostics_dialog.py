"""Simple diagnostics dialog to inspect structured logs."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from utils.logging_utils import get_log_file_path


class DiagnosticsDialog(QDialog):
    """Display the latest application logs for quick troubleshooting."""

    MAX_BYTES = 20000  # limit file read for responsiveness

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Diagnostics & Logs")
        self.setMinimumSize(720, 480)

        self._log_path = get_log_file_path()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        header = QLabel("Review recent log entries for troubleshooting.")
        header.setWordWrap(True)
        layout.addWidget(header)

        controls = QHBoxLayout()

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh_logs)
        controls.addWidget(self.refresh_btn)

        copy_btn = QPushButton("Copy Path")
        copy_btn.clicked.connect(self.copy_log_path)
        controls.addWidget(copy_btn)

        open_btn = QPushButton("Open Folder")
        open_btn.clicked.connect(self.open_log_folder)
        controls.addWidget(open_btn)

        controls.addStretch()
        layout.addLayout(controls)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setFontFamily("Consolas")
        self.log_view.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        layout.addWidget(self.log_view, stretch=1)

        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.status_label)

        self.refresh_logs()

    def refresh_logs(self) -> None:
        """Load latest log file contents."""

        path = self._log_path
        if not path.exists():
            self.log_view.setPlainText("Log file not found yet. Trigger an action to generate logs.")
            self.status_label.setText(str(path))
            return

        data = self._read_tail(path)
        self.log_view.setPlainText(data)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        size_kb = path.stat().st_size / 1024
        self.status_label.setText(f"{path} • {size_kb:.1f} KB • Refreshed {timestamp}")

    def copy_log_path(self) -> None:
        QApplication.clipboard().setText(str(self._log_path))

    def open_log_folder(self) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._log_path.parent)))

    def _read_tail(self, path: Path) -> str:
        return read_log_tail(path, max_bytes=self.MAX_BYTES)


def read_log_tail(path: Path, max_bytes: int = DiagnosticsDialog.MAX_BYTES) -> str:
    with path.open("rb") as fh:
        fh.seek(0, 2)
        size = fh.tell()
        if size > max_bytes:
            fh.seek(-max_bytes, 2)
        else:
            fh.seek(0)
        data = fh.read()

    return data.decode("utf-8", errors="replace")
