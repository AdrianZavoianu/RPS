"""A4 page preview widget for report generation."""

from __future__ import annotations

from typing import List

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QColor, QPen
from PyQt6.QtWidgets import QLabel, QScrollArea, QSizePolicy, QVBoxLayout, QWidget

from gui.icon_utils import ICONS_DIR
from gui.styles import COLORS
from .report_header_footer import ReportHeaderFooter
from .report_layout import A4_HEIGHT_PX, A4_WIDTH_PX, SECTION_GAP
from .report_page_builder import ReportPageBuilder
from .report_plot_renderer import ReportPlotRenderer
from .report_table_renderer import ReportTableRenderer


class ReportPageWidget(QWidget):
    """Widget representing a single A4 page in the preview."""

    def __init__(self, project_name: str, page_number: int = 1, parent=None):
        super().__init__(parent)
        self.project_name = project_name
        self.page_number = page_number
        self.sections: List = []

        self.setFixedSize(A4_WIDTH_PX, A4_HEIGHT_PX)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        logo_path = ICONS_DIR / "RPS_Logo.png"
        logo = ReportHeaderFooter.load_colorized_logo(logo_path)
        header_footer = ReportHeaderFooter(logo)
        table_renderer = ReportTableRenderer()
        plot_renderer = ReportPlotRenderer()
        self._page_builder = ReportPageBuilder(header_footer, table_renderer, plot_renderer)

    @classmethod
    def estimate_section_height(cls, section, available_width: int = 485) -> int:
        """Estimate height for a section."""
        return ReportPageBuilder.estimate_section_height(section, available_width)

    @classmethod
    def get_content_height(cls) -> int:
        """Available content height."""
        return ReportPageBuilder.get_content_height()

    def set_sections(self, sections: list) -> None:
        self.sections = sections
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        # White background
        painter.fillRect(self.rect(), QColor("#ffffff"))

        # Page border
        painter.setPen(QPen(QColor(COLORS["border"]), 1))
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))

        self._page_builder.draw_page(painter, self.sections, self.project_name, self.page_number)
        painter.end()


class ReportPreviewWidget(QScrollArea):
    """Scrollable container for A4 page previews."""

    def __init__(self, project_name: str, parent=None):
        super().__init__(parent)
        self.project_name = project_name
        self._pages: List[ReportPageWidget] = []

        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setStyleSheet(
            f"""
            QScrollArea {{
                background-color: {COLORS['card']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
            }}
        """
        )

        self._container = QWidget()
        self._container.setStyleSheet(f"background-color: {COLORS['card']};")
        self._layout = QVBoxLayout(self._container)
        self._layout.setContentsMargins(20, 20, 20, 20)
        self._layout.setSpacing(20)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)

        self.setWidget(self._container)
        self._show_empty_state()

    def _show_empty_state(self) -> None:
        self._clear_pages()
        label = QLabel("Select sections from the tree to preview")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet(f"color: {COLORS['muted']}; font-size: 14px; padding: 40px;")
        self._layout.addWidget(label)

    def _clear_pages(self) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._pages.clear()

    def set_sections(self, sections: list) -> None:
        self._clear_pages()

        if not sections:
            self._show_empty_state()
            return

        # Distribute sections across pages
        max_height = ReportPageWidget.get_content_height()
        current_sections = []
        current_h = 0
        page_num = 1

        for section in sections:
            section_h = ReportPageWidget.estimate_section_height(section)

            if current_h + section_h > max_height and current_sections:
                page = ReportPageWidget(self.project_name, page_number=page_num)
                page.set_sections(current_sections)
                self._layout.addWidget(page)
                self._pages.append(page)
                page_num += 1
                current_sections = []
                current_h = 0

            current_sections.append(section)
            current_h += section_h + SECTION_GAP

        if current_sections:
            page = ReportPageWidget(self.project_name, page_number=page_num)
            page.set_sections(current_sections)
            self._layout.addWidget(page)
            self._pages.append(page)

        self._layout.addStretch()

    def clear_preview(self) -> None:
        self._clear_pages()
        self._show_empty_state()
