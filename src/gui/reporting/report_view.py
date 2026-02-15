"""Main reporting view with checkbox tree and A4 preview."""

from __future__ import annotations

import logging
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QLabel,
    QComboBox,
    QApplication,
    QProgressBar,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QCursor

from gui.design_tokens import FormStyles
from gui.styles import COLORS
from gui.ui_helpers import create_styled_label, create_styled_button
from services.project_runtime import ProjectRuntime
from services.reporting_data import ReportingDataService
from .report_models import ReportSection
from .report_section_loader import ReportSectionLoader

logger = logging.getLogger(__name__)


class ReportView(QWidget):
    """Main reporting interface with checkbox tree and A4 preview.

    Layout:
    ┌─────────────────────────────────────────────┐
    │ Result Set: [DES ▼]  [Print] [Export PDF]   │ Settings bar
    ├──────────────┬──────────────────────────────┤
    │ ☑ Global     │                              │
    │   ☑ Drifts   │     A4 Preview Area          │
    │     ☑ X      │     (scrollable)             │
    │     ☑ Y      │                              │
    │   ☐ Forces   │                              │
    │              │                              │
    └──────────────┴──────────────────────────────┘
         30%                    70%
    """

    section_selection_changed = pyqtSignal()

    def __init__(self, runtime: ProjectRuntime, parent: Optional[QWidget] = None, analysis_context: str = 'NLTHA'):
        super().__init__(parent)
        self.runtime = runtime
        self.result_service = runtime.result_service
        self.reporting_service = ReportingDataService(runtime.context.session)
        self.project_name = runtime.project.name
        self.project_id = runtime.project.id
        self.analysis_context = analysis_context  # 'NLTHA' or 'Pushover'

        self._selected_result_set_id: Optional[int] = None
        self.section_loader = ReportSectionLoader(
            self.result_service,
            self.reporting_service,
            self.project_id,
            self.analysis_context,
        )

        # Debounce timer for preview updates (300ms delay)
        self._update_timer = QTimer(self)
        self._update_timer.setSingleShot(True)
        self._update_timer.setInterval(300)
        self._update_timer.timeout.connect(self._do_update_preview)

        self.setMinimumSize(800, 600)
        self._setup_ui()
        self._load_result_sets()

    def _setup_ui(self) -> None:
        """Build the reporting view UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Settings bar at top
        settings_bar = self._create_settings_bar()
        layout.addWidget(settings_bar)

        # Main splitter: checkbox tree (left) | preview area (right)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setObjectName("reportSplitter")
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(4)
        splitter.setStyleSheet(f"""
            QSplitter#reportSplitter {{
                background-color: {COLORS['background']};
            }}
            QSplitter#reportSplitter::handle {{
                background-color: {COLORS['border']};
            }}
        """)

        # Left: Checkbox tree container
        tree_container = self._create_tree_container()
        splitter.addWidget(tree_container)

        # Right: Preview area
        preview_container = self._create_preview_container()
        splitter.addWidget(preview_container)

        # Set splitter proportions (30% tree, 70% preview)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        splitter.setSizes([280, 800])

        layout.addWidget(splitter, stretch=1)

    def _create_settings_bar(self) -> QWidget:
        """Create the top settings bar with result set dropdown and buttons."""
        bar = QWidget()
        bar.setObjectName("settingsBar")
        bar.setFixedHeight(48)
        bar.setStyleSheet(f"""
            QWidget#settingsBar {{
                background-color: {COLORS['card']};
                border-bottom: 1px solid {COLORS['border']};
            }}
        """)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(12)

        # Result set label and dropdown
        rs_label = create_styled_label("Result Set:", "muted")
        layout.addWidget(rs_label)

        self.result_set_combo = QComboBox()
        self.result_set_combo.setMinimumWidth(150)
        self.result_set_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS['background']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                padding: 4px 8px;
                min-height: 24px;
            }}
            QComboBox:hover {{
                border-color: {COLORS['accent']};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {COLORS['card']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                selection-background-color: {COLORS['accent']};
            }}
        """)
        self.result_set_combo.currentIndexChanged.connect(self._on_result_set_changed)
        layout.addWidget(self.result_set_combo)

        layout.addStretch()

        # Select All / Clear buttons
        select_all_btn = create_styled_button("Select All", variant="ghost")
        select_all_btn.clicked.connect(self._on_select_all)
        layout.addWidget(select_all_btn)

        clear_btn = create_styled_button("Clear", variant="ghost")
        clear_btn.clicked.connect(self._on_clear_selection)
        layout.addWidget(clear_btn)

        # Separator
        sep = QWidget()
        sep.setFixedWidth(1)
        sep.setFixedHeight(24)
        sep.setStyleSheet(f"background-color: {COLORS['border']};")
        layout.addWidget(sep)

        # Print and Export buttons
        print_btn = create_styled_button("Print", variant="secondary")
        print_btn.setToolTip("Open print dialog")
        print_btn.clicked.connect(self._on_print_clicked)
        layout.addWidget(print_btn)

        export_btn = create_styled_button("Export PDF", variant="primary")
        export_btn.setToolTip("Export report to PDF file")
        export_btn.clicked.connect(self._on_export_clicked)
        layout.addWidget(export_btn)

        return bar

    def _create_tree_container(self) -> QWidget:
        """Create the left panel with checkbox tree."""
        container = QWidget()
        container.setObjectName("treeContainer")
        container.setMinimumWidth(200)
        container.setStyleSheet(f"QWidget#treeContainer {{ background-color: {COLORS['background']}; }}")

        layout = QVBoxLayout(container)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Header
        header = create_styled_label("Report Sections", "section")
        layout.addWidget(header)

        # Checkbox tree for section selection
        from .report_checkbox_tree import ReportCheckboxTree
        self.checkbox_tree = ReportCheckboxTree()
        self.checkbox_tree.selection_changed.connect(self._on_tree_selection_changed)
        layout.addWidget(self.checkbox_tree, stretch=1)

        return container

    def _create_preview_container(self) -> QWidget:
        """Create the right panel with A4 preview area."""
        container = QWidget()
        container.setObjectName("previewContainer")
        container.setMinimumWidth(400)
        container.setStyleSheet(f"QWidget#previewContainer {{ background-color: {COLORS['background']}; }}")

        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(8)

        # Header
        header = create_styled_label("Report Preview", "section")
        layout.addWidget(header)
        
        # Loading indicator - indeterminate progress bar with message
        self._loading_container = QWidget()
        loading_layout = QHBoxLayout(self._loading_container)
        loading_layout.setContentsMargins(0, 4, 0, 4)
        loading_layout.setSpacing(10)
        
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 0)  # Indeterminate mode
        self._progress_bar.setFixedHeight(16)
        self._progress_bar.setFixedWidth(120)
        self._progress_bar.setStyleSheet(FormStyles.progress_bar(height=16))
        loading_layout.addWidget(self._progress_bar)
        
        loading_label = QLabel("Please wait, loading report data...")
        loading_label.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['text_secondary']};
                font-size: 12px;
            }}
        """)
        loading_layout.addWidget(loading_label)
        loading_layout.addStretch()
        
        self._loading_container.hide()
        layout.addWidget(self._loading_container)

        # Preview widget
        from .report_preview_widget import ReportPreviewWidget
        self.preview_widget = ReportPreviewWidget(self.project_name)
        layout.addWidget(self.preview_widget, stretch=1)

        return container

    def _load_result_sets(self) -> None:
        """Load result sets into the dropdown based on analysis context."""
        result_sets = self.runtime.repos.result_set.get_by_project(self.project_id)
        logger.info(f"Reporting: Found {len(result_sets)} result sets for project {self.project_id}")

        # Filter result sets based on analysis context
        if self.analysis_context == 'Pushover':
            filtered_sets = [rs for rs in result_sets if getattr(rs, 'analysis_type', None) == 'Pushover']
            logger.info(f"Reporting: Filtered to {len(filtered_sets)} Pushover result sets")
        else:
            # NLTHA context - exclude Pushover result sets
            filtered_sets = [rs for rs in result_sets if getattr(rs, 'analysis_type', None) != 'Pushover']
            logger.info(f"Reporting: Filtered to {len(filtered_sets)} NLTHA result sets")

        self.result_set_combo.clear()
        for rs in filtered_sets:
            logger.info(f"Reporting: Adding result set '{rs.name}' (id={rs.id})")
            self.result_set_combo.addItem(rs.name, rs.id)

        if filtered_sets:
            self._selected_result_set_id = filtered_sets[0].id
            self._refresh_tree()
        else:
            logger.warning(f"Reporting: No {self.analysis_context} result sets found")

    def _on_result_set_changed(self, index: int) -> None:
        """Handle result set dropdown change."""
        if index < 0:
            return
        self._selected_result_set_id = self.result_set_combo.currentData()
        self._refresh_tree()

    def _refresh_tree(self) -> None:
        """Refresh the checkbox tree for the selected result set."""
        if self._selected_result_set_id is None:
            return
        # Pass session_factory to allow DataAccessService creation
        self.checkbox_tree.populate_from_result_set(
            self._selected_result_set_id,
            self.runtime.context.session  # session_factory, not session instance
        )
        self._update_preview()

    def _on_tree_selection_changed(self) -> None:
        """Handle checkbox tree selection changes."""
        self._update_preview()
        self.section_selection_changed.emit()

    def _update_preview(self) -> None:
        """Schedule a debounced preview update."""
        # Restart the timer on each call - only triggers after user stops clicking
        self._update_timer.start()

    def _do_update_preview(self) -> None:
        """Actually update the preview (called after debounce delay)."""
        if self._selected_result_set_id is None:
            return

        sections = self.checkbox_tree.get_selected_sections(self._selected_result_set_id, self.analysis_context)
        
        if not sections:
            self.preview_widget.set_sections([])
            return

        # Check if any sections need fetching (not cached)
        needs_fetch = self.section_loader.needs_fetch(sections)
        
        # Show loading indicator if fetching is needed
        if needs_fetch:
            self._loading_container.show()
            QApplication.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor))
            QApplication.processEvents()

        try:
            # Fetch datasets for each section (with caching)
            self.section_loader.load_sections(sections)
            self.preview_widget.set_sections(sections)
        finally:
            # Hide loading indicator
            if needs_fetch:
                self._loading_container.hide()
                QApplication.restoreOverrideCursor()

    def _on_select_all(self) -> None:
        """Select all items in the checkbox tree."""
        self.checkbox_tree.select_all()

    def _on_clear_selection(self) -> None:
        """Clear all selections in the checkbox tree."""
        self.checkbox_tree.clear_selection()

    def _on_print_clicked(self) -> None:
        """Open print dialog."""
        from .pdf_generator import PDFGenerator

        sections = self._get_sections_with_data()
        if not sections:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "No Sections Selected",
                "Please select at least one section to print."
            )
            return

        generator = PDFGenerator(self.project_name)
        generator.show_print_dialog(sections, self)

    def _on_export_clicked(self) -> None:
        """Export to PDF file."""
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        from pathlib import Path
        from datetime import datetime

        sections = self._get_sections_with_data()
        if not sections:
            QMessageBox.warning(
                self,
                "No Sections Selected",
                "Please select at least one section to export."
            )
            return

        # Generate default filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"{self.project_name}_Report_{timestamp}.pdf"

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Report to PDF",
            default_name,
            "PDF Files (*.pdf)"
        )

        if not file_path:
            return

        from .pdf_generator import PDFGenerator
        generator = PDFGenerator(self.project_name)

        try:
            generator.generate(sections, file_path)
            QMessageBox.information(
                self,
                "Export Complete",
                f"Report exported successfully to:\n{file_path}"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Export Failed",
                f"Failed to export report:\n{str(e)}"
            )

    def _get_sections_with_data(self) -> list[ReportSection]:
        """Get selected sections with their datasets loaded."""
        if self._selected_result_set_id is None:
            return []

        sections = self.checkbox_tree.get_selected_sections(self._selected_result_set_id, self.analysis_context)
        return self.section_loader.get_sections_with_data(sections)

    def set_result_set(self, result_set_id: int) -> None:
        """Set the active result set programmatically."""
        index = self.result_set_combo.findData(result_set_id)
        if index >= 0:
            self.result_set_combo.setCurrentIndex(index)
