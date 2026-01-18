"""UI-only view helpers for ProjectDetailWindow (header + main layout)."""

from __future__ import annotations

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QSplitter
from PyQt6.QtCore import Qt


class ProjectDetailWindowView(QWidget):
    """Lightweight view wrapper providing header spacer and main splitter."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        self.header_spacer = QWidget()
        self.header_spacer.setFixedHeight(8)

        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setObjectName("mainSplitter")
        self.main_splitter.setChildrenCollapsible(False)
        self.main_splitter.setHandleWidth(1)
        self.main_splitter.setStyleSheet(
            """
            QSplitter#mainSplitter::handle {
                background-color: transparent;
                border: none;
            }
            QSplitter#mainSplitter::handle:hover {
                background-color: rgba(74, 125, 137, 0.2);
            }
        """
        )
