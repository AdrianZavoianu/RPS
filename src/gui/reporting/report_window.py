"""Report window dialog for PDF report generation."""

from __future__ import annotations

import logging

from PyQt6.QtWidgets import QDialog, QVBoxLayout
from PyQt6.QtCore import Qt

from gui.styles import COLORS
from gui.window_utils import enable_dark_title_bar
from services.project_runtime import ProjectRuntime
from .report_view import ReportView

logger = logging.getLogger(__name__)


class ReportWindow(QDialog):
    """Dialog window for generating PDF reports.

    Opens as a modal window containing the ReportView with:
    - Checkbox tree for section selection
    - A4 preview
    - Print and Export buttons
    """

    def __init__(self, runtime: ProjectRuntime, result_set_id: int, parent=None, analysis_context: str = 'NLTHA'):
        super().__init__(parent)
        self.runtime = runtime
        self.result_set_id = result_set_id
        self.analysis_context = analysis_context

        # Set window title based on context
        context_label = "Pushover Report" if analysis_context == 'Pushover' else "Report"
        self.setWindowTitle(f"{context_label} - {runtime.project.name}")
        self.setMinimumSize(1200, 800)
        self.setModal(True)

        # Apply dark theme - use object name to avoid styling children
        self.setObjectName("reportWindow")
        self.setStyleSheet(f"""
            QDialog#reportWindow {{
                background-color: {COLORS['background']};
            }}
        """)

        self._setup_ui()
        enable_dark_title_bar(self)

    def _setup_ui(self) -> None:
        """Build the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Report view takes up the entire dialog
        logger.info(f"ReportWindow: Creating ReportView for result_set_id={self.result_set_id} (context={self.analysis_context})")
        self.report_view = ReportView(self.runtime, parent=self, analysis_context=self.analysis_context)
        logger.info(f"ReportWindow: ReportView created, size={self.report_view.size()}")
        self.report_view.set_result_set(self.result_set_id)
        layout.addWidget(self.report_view)
        logger.info("ReportWindow: ReportView added to layout")

    def showEvent(self, event) -> None:
        """Maximize the dialog on show."""
        super().showEvent(event)
        # Make the dialog larger but not maximized
        screen = self.screen().availableGeometry()
        self.resize(int(screen.width() * 0.85), int(screen.height() * 0.85))
        # Center the dialog
        self.move(
            (screen.width() - self.width()) // 2,
            (screen.height() - self.height()) // 2
        )
