"""Reusable project grid widget with responsive card layout."""

from __future__ import annotations

from typing import Callable, Dict, List, Optional

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from gui.icon_utils import load_svg_icon


class ProjectGridWidget(QWidget):
    """Displays project summary cards in a responsive grid."""

    def __init__(
        self,
        on_open: Callable[[str], None],
        on_delete: Callable[[str], None],
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._on_open = on_open
        self._on_delete = on_delete
        self._projects: List[Dict] = []
        self._current_columns: int = 0

        self._grid = QGridLayout()
        self._grid.setContentsMargins(0, 12, 0, 12)  # Top and bottom margins only
        self._grid.setHorizontalSpacing(20)
        self._grid.setVerticalSpacing(20)
        self._grid.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.setLayout(self._grid)

    def set_projects(self, projects: List[Dict]) -> None:
        """Replace grid contents with provided projects."""
        self._projects = projects or []
        self._current_columns = 0
        self._render()

    def clear(self) -> None:
        """Clear all project cards."""
        self.set_projects([])

    # ------------------------------------------------------------------
    # QWidget overrides
    # ------------------------------------------------------------------

    def resizeEvent(self, event):
        """Re-render cards when available width changes."""
        super().resizeEvent(event)
        if not self._projects:
            return

        new_columns = self._determine_columns(len(self._projects))
        if new_columns != self._current_columns:
            self._render(reuse_placeholder=False)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _render(self, reuse_placeholder: bool = True) -> None:
        self._clear_layout()

        if not self._projects:
            if reuse_placeholder:
                placeholder = QLabel("No projects imported yet. Use the Home page to import results.")
                placeholder.setObjectName("pageBodyText")
                placeholder.setWordWrap(True)
                self._grid.addWidget(placeholder, 0, 0)
            self._current_columns = 0
            return

        columns = self._determine_columns(len(self._projects))
        self._current_columns = columns

        for col in range(columns):
            self._grid.setColumnStretch(col, 1)

        for index, project in enumerate(self._projects):
            row_idx = index // columns
            col_idx = index % columns
            card = self._create_project_card(project)
            self._grid.addWidget(card, row_idx, col_idx)

    def _clear_layout(self) -> None:
        while self._grid.count():
            item = self._grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)

    def _determine_columns(self, project_count: int) -> int:
        if project_count <= 0:
            return 1

        available_width = self._available_width()
        spacing = self._grid.horizontalSpacing() or 20
        min_card_width = 220
        max_columns = min(5, project_count)

        for columns in range(max_columns, 0, -1):
            required_width = columns * min_card_width + (columns - 1) * spacing
            if available_width >= required_width:
                return columns

        return 1

    def _available_width(self) -> int:
        """Best-effort width of the viewport hosting this grid."""
        viewport = self.parentWidget()
        if viewport and hasattr(viewport, "width"):
            available = viewport.width()
            scroll_area = viewport.parentWidget()
            if scroll_area and hasattr(scroll_area, "verticalScrollBar"):
                scrollbar = scroll_area.verticalScrollBar()
                if scrollbar:
                    available -= scrollbar.sizeHint().width()
        else:
            available = self.width()

        margins = self._grid.contentsMargins()
        available -= margins.left() + margins.right()
        return max(available, 0)

    def _create_project_card(self, data: Dict) -> QWidget:
        card = QFrame()
        card.setObjectName("projectCard")
        card.setFrameShape(QFrame.Shape.StyledPanel)
        card.setMinimumSize(220, 220)
        card.setFixedHeight(220)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        title = QLabel(data["name"])
        title.setObjectName("cardTitle")
        layout.addWidget(title)

        body_text = data.get("description")
        if body_text:
            body = QLabel(body_text)
            body.setObjectName("cardBody")
            body.setWordWrap(True)
            layout.addWidget(body)

        stats_container = QFrame()
        stats_container.setObjectName("cardStatsContainer")
        stats_layout = QVBoxLayout(stats_container)
        stats_layout.setContentsMargins(0, 0, 0, 0)
        stats_layout.setSpacing(8)

        stats = [
            ("Load cases", data.get("load_cases", 0)),
            ("Stories", data.get("stories", 0)),
        ]

        for label, value in stats:
            row = QHBoxLayout()
            row.setSpacing(8)
            label_widget = QLabel(label)
            label_widget.setObjectName("cardStatLabel")
            value_widget = QLabel(str(value))
            value_widget.setObjectName("cardStatValue")
            row.addWidget(label_widget)
            row.addStretch()
            row.addWidget(value_widget)
            stats_layout.addLayout(row)

        layout.addWidget(stats_container)

        layout.addStretch()

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setObjectName("cardDivider")
        layout.addWidget(divider)

        footer = QHBoxLayout()
        footer.setSpacing(12)

        created_label = QLabel("Created")
        created_label.setObjectName("cardFooterLabel")
        footer.addWidget(created_label)

        created_at = data.get("created_at")
        created_value = QLabel(data.get("_formatted_created", ""))
        created_value.setObjectName("cardFooterValue")
        footer.addWidget(created_value)

        footer.addStretch()

        layout.addLayout(footer)

        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)

        open_button = QPushButton("Open")
        open_button.setObjectName("cardPrimaryAction")
        open_button.clicked.connect(lambda _, name=data["name"]: self._on_open(name))
        button_layout.addWidget(open_button)

        button_layout.addStretch()

        delete_button = QPushButton()
        delete_button.setObjectName("cardDeleteAction")
        delete_button.setToolTip("Delete project")
        delete_button.setIcon(load_svg_icon("trash", 18, "#8b949e"))
        delete_button.setIconSize(QSize(18, 18))
        delete_button.setFixedSize(32, 32)
        delete_button.clicked.connect(lambda _, name=data["name"]: self._on_delete(name))
        button_layout.addWidget(delete_button)

        layout.addLayout(button_layout)

        return card
