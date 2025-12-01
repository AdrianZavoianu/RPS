"""Folder import dialog with progress tracking."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QLineEdit,
    QProgressBar,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QCheckBox,
)

from .styles import COLORS
from .ui_helpers import create_styled_button, create_styled_label
from services.import_preparation import ImportPreparationService, PrescanResult
from services.project_service import (
    ProjectContext,
    ensure_project_context,
    get_project_context,
    result_set_exists,
)
from processing.folder_importer import TARGET_SHEETS


EXCEL_PATTERNS: Sequence[str] = ("*.xlsx", "*.xls")


logger = logging.getLogger(__name__)


def create_checkbox_icons() -> tuple[QIcon, QIcon]:
    """Create checkbox icons for unchecked and checked states."""
    size = 20

    # Unchecked icon (empty)
    unchecked_pixmap = QPixmap(size, size)
    unchecked_pixmap.fill(Qt.GlobalColor.transparent)
    unchecked_icon = QIcon(unchecked_pixmap)

    # Checked icon (with checkmark)
    checked_pixmap = QPixmap(size, size)
    checked_pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(checked_pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Draw checkmark
    painter.setPen(QPen(QColor("#ffffff"), 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    # Checkmark path (optimized for visibility)
    painter.drawLine(int(size * 0.25), int(size * 0.5), int(size * 0.4), int(size * 0.65))
    painter.drawLine(int(size * 0.4), int(size * 0.65), int(size * 0.75), int(size * 0.3))

    painter.end()
    checked_icon = QIcon(checked_pixmap)

    return unchecked_icon, checked_icon


class LoadCaseScanWorker(QThread):
    """Worker thread for scanning files for load cases."""

    progress = pyqtSignal(str, int, int)  # message, current, total
    finished = pyqtSignal(object)  # PrescanResult
    error = pyqtSignal(str)  # error message

    def __init__(
        self,
        folder_path: Path,
        result_types: Optional[Sequence[str]] = None,
    ) -> None:
        super().__init__()
        self.folder_path = folder_path
        self.result_types = result_types

    def run(self) -> None:  # pragma: no cover - executes in worker thread
        """Scan files for load cases in background thread."""
        try:
            result_types_set = None
            if self.result_types:
                result_types_set = {rt.strip().lower() for rt in self.result_types}

            service = ImportPreparationService(TARGET_SHEETS)
            prescan = service.prescan_folder(
                self.folder_path,
                result_types_set,
                self._on_progress,
            )
            logger.info(
                "Folder prescan finished",
                extra={
                    "event": "prescan.complete",
                    "folder": str(self.folder_path),
                    "files": prescan.files_scanned,
                    "errors": len(prescan.errors),
                },
            )
            self.finished.emit(prescan)
        except Exception as exc:  # pragma: no cover - UI feedback
            logger.exception(
                "Folder prescan failed",
                extra={
                    "event": "prescan.failure",
                    "folder": str(self.folder_path),
                },
            )
            self.error.emit(str(exc))

    def _on_progress(self, message: str, current: int, total: int) -> None:
        """Relay progress updates back to the dialog thread."""
        self.progress.emit(message, current, total)


class FolderImportWorker(QThread):
    """Worker thread for folder import to avoid blocking UI."""

    progress = pyqtSignal(str, int, int)  # message, current, total
    finished = pyqtSignal(dict)  # stats
    error = pyqtSignal(str)  # error message

    def __init__(
        self,
        context: ProjectContext,
        folder_path: Path,
        result_set_name: str,
        result_types: Optional[Sequence[str]] = None,
        use_enhanced: bool = False,
        parent_widget: Optional[QWidget] = None,
        selected_load_cases: Optional[Set[str]] = None,
        conflict_resolution: Optional[Dict[str, Dict[str, Optional[str]]]] = None,
        prescan_result: Optional[PrescanResult] = None,
    ) -> None:
        super().__init__()
        self.context = context
        self.folder_path = folder_path
        self.result_set_name = result_set_name
        self.result_types = list(result_types) if result_types else None
        self.use_enhanced = use_enhanced
        self.parent_widget = parent_widget
        self.selected_load_cases = selected_load_cases
        self.conflict_resolution = conflict_resolution
        self.prescan_result = prescan_result
        self._session_factory = context.session_factory()

    def run(self) -> None:  # pragma: no cover - executes in worker thread
        """Run the import in background thread."""
        try:
            logger.info(
                "Folder import worker starting",
                extra={
                    "event": "import.folder.start",
                    "project": self.context.name,
                    "result_set": self.result_set_name,
                    "folder": str(self.folder_path),
                    "enhanced": self.use_enhanced,
                },
            )
            if self.use_enhanced:
                from processing.enhanced_folder_importer import EnhancedFolderImporter

                importer = EnhancedFolderImporter(
                    folder_path=str(self.folder_path),
                    project_name=self.context.name,
                    result_set_name=self.result_set_name,
                    result_types=self.result_types,
                    session_factory=self._session_factory,
                    progress_callback=self._on_progress,
                    parent_widget=self.parent_widget,
                    selected_load_cases=self.selected_load_cases,
                    conflict_resolution=self.conflict_resolution,
                    prescan_result=self.prescan_result,
                )
                stats = importer.import_all()
                self.finished.emit(stats)
            else:
                from processing.folder_importer import FolderImporter

                importer = FolderImporter(
                    folder_path=str(self.folder_path),
                    project_name=self.context.name,
                    result_set_name=self.result_set_name,
                    result_types=self.result_types,
                    session_factory=self._session_factory,
                    progress_callback=self._on_progress,
                    file_summaries=self.prescan_result.file_summaries if self.prescan_result else None,
                )
                stats = importer.import_all()
                self.finished.emit(stats)
                logger.info(
                    "Folder import worker finished",
                    extra={
                        "event": "import.folder.complete",
                        "project": self.context.name,
                        "result_set": self.result_set_name,
                        "files_processed": stats.get("files_processed"),
                        "files_total": stats.get("files_total"),
                        "errors": len(stats.get("errors") or []),
                    },
                )
        except Exception as exc:  # pragma: no cover - UI feedback
            logger.exception(
                "Folder import worker failed",
                extra={
                    "event": "import.folder.failure",
                    "project": self.context.name,
                    "result_set": self.result_set_name,
                },
            )
            self.error.emit(str(exc))

    def _on_progress(self, message: str, current: int, total: int) -> None:
        """Relay progress updates back to the dialog thread."""
        self.progress.emit(message, current, total)


class FolderImportDialog(QDialog):
    """Dialog for batch importing Excel files from a folder."""

    def __init__(
        self,
        parent=None,
        context: Optional[ProjectContext] = None,
        result_types: Optional[Sequence[str]] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Import Data")
        # Much wider, less tall - horizontal layout optimization
        self.setMinimumSize(1200, 700)
        self.resize(1400, 750)

        self.context: Optional[ProjectContext] = context
        self.result_types = list(result_types) if result_types else None

        self.folder_path: Optional[Path] = None
        self.project_name: Optional[str] = context.name if context else None
        self.result_set_name: Optional[str] = None
        self.import_stats: Optional[dict] = None
        self._excel_files: List[Path] = []
        self._lock_project_name = context is not None
        self._prescan_result: Optional[PrescanResult] = None

        self.scan_worker: Optional[LoadCaseScanWorker] = None
        self.import_worker: Optional[FolderImportWorker] = None

        self._build_ui()
        self._apply_defaults()

    # ------------------------------------------------------------------ #
    # UI setup
    # ------------------------------------------------------------------ #

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 8, 16, 16)  # Reduced top margin from 24 to 8
        main_layout.setSpacing(12)  # Reduced from 16 to 12

        # Header with larger font
        header = create_styled_label("Import Project Data", "header")
        header.setStyleSheet(f"color: {COLORS['text']}; font-size: 24px; font-weight: 600;")
        main_layout.addWidget(header)

        # ============ TOP ROW: All Configuration in Horizontal Layout ============
        config_row = QHBoxLayout()
        config_row.setSpacing(8)  # Reduced from 12 to 8

        # Folder selection (reduced vertical padding)
        folder_group = QGroupBox("Folder Selection")
        folder_group.setStyleSheet(self._groupbox_style())
        folder_layout = QVBoxLayout(folder_group)
        folder_layout.setContentsMargins(8, 8, 8, 8)  # Reduced from 12 to 8

        folder_input_layout = QHBoxLayout()
        self.folder_input = QLineEdit()
        self.folder_input.setReadOnly(True)
        self.folder_input.setPlaceholderText("Select folder...")
        self.folder_input.setStyleSheet(self._entry_style(required=True))
        self.folder_input.setProperty("empty", "true")  # Initially empty
        self.folder_input.textChanged.connect(lambda: self._update_empty_state(self.folder_input))
        folder_input_layout.addWidget(self.folder_input)

        self.browse_btn = create_styled_button("Browse", "secondary", "sm")
        self.browse_btn.clicked.connect(self.browse_folder)
        folder_input_layout.addWidget(self.browse_btn)

        folder_layout.addLayout(folder_input_layout)
        config_row.addWidget(folder_group, stretch=2)

        # Project information (reduced vertical padding, normal border)
        project_group = QGroupBox("Project")
        project_group.setStyleSheet(self._groupbox_style())
        project_layout = QVBoxLayout(project_group)
        project_layout.setContentsMargins(8, 8, 8, 8)  # Reduced from 12 to 8

        self.project_input = QLineEdit()
        self.project_input.setPlaceholderText("Project name...")
        self.project_input.setStyleSheet(self._entry_style(required=False))  # Normal border
        self.project_input.textChanged.connect(self.update_import_button)
        project_layout.addWidget(self.project_input)
        config_row.addWidget(project_group, stretch=1)

        # Result set information (reduced vertical padding, orange border, NO validation label)
        result_group = QGroupBox("Result Set")
        result_group.setStyleSheet(self._groupbox_style())
        result_layout = QVBoxLayout(result_group)
        result_layout.setContentsMargins(8, 8, 8, 8)  # Reduced from 12 to 8

        self.result_set_input = QLineEdit()
        self.result_set_input.setPlaceholderText("e.g., DES, MCE, SLE...")
        self.result_set_input.setStyleSheet(self._entry_style(required=True))
        self.result_set_input.setProperty("empty", "true")  # Initially empty
        self.result_set_input.textChanged.connect(self.update_import_button)
        self.result_set_input.textChanged.connect(lambda: self._update_empty_state(self.result_set_input))
        result_layout.addWidget(self.result_set_input)

        config_row.addWidget(result_group, stretch=1)

        main_layout.addLayout(config_row)

        # ============ MIDDLE ROW: Files | Load Cases | Progress ============
        # Alignment strategy:
        # Top row: Folder(2) + Project(1) + ResultSet(1) = 4 total
        # Bottom row: Files + LoadCases(3) should align right edge with Folder
        # Progress should align left edge with Project
        # Adjusting Files and Progress only, keeping LoadCases at 3
        # Using higher numbers for finer control: multiply all by 10 for precision

        data_row = QHBoxLayout()
        data_row.setSpacing(8)  # Reduced from 12 to 8

        # Files to process - Was 5, reduce by tiny amount (50 → 49)
        files_group = QGroupBox("Files to Process")
        files_group.setStyleSheet(self._groupbox_style())
        files_layout = QVBoxLayout(files_group)

        self.file_list = QListWidget()
        self.file_list.setStyleSheet(self._list_style())
        files_layout.addWidget(self.file_list)
        data_row.addWidget(files_group, stretch=49)

        # Load Cases Selection - Narrow (stretch=2), with reduced margins
        loadcases_group = QGroupBox("Load Cases")
        loadcases_group.setStyleSheet(self._groupbox_style())
        loadcases_layout = QVBoxLayout(loadcases_group)
        loadcases_layout.setContentsMargins(8, 12, 8, 8)  # Reduced padding

        # Quick actions at top
        lc_actions_layout = QHBoxLayout()
        self.select_all_lc_btn = create_styled_button("All", "ghost", "sm")
        self.select_all_lc_btn.clicked.connect(self._select_all_load_cases)
        self.select_all_lc_btn.setEnabled(False)
        lc_actions_layout.addWidget(self.select_all_lc_btn)

        self.select_none_lc_btn = create_styled_button("None", "ghost", "sm")
        self.select_none_lc_btn.clicked.connect(self._select_none_load_cases)
        self.select_none_lc_btn.setEnabled(False)
        lc_actions_layout.addWidget(self.select_none_lc_btn)

        lc_actions_layout.addStretch()
        loadcases_layout.addLayout(lc_actions_layout)

        # Scrollable load case list
        self.load_case_scroll = QScrollArea()
        self.load_case_scroll.setWidgetResizable(True)
        self.load_case_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.load_case_scroll.setStyleSheet(f"""
            QScrollArea {{
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                background-color: {COLORS['background']};
            }}
        """)

        # Container for load case checkboxes
        self.load_case_container = QWidget()
        self.load_case_layout = QVBoxLayout(self.load_case_container)
        self.load_case_layout.setContentsMargins(0, 0, 0, 0)
        self.load_case_layout.setSpacing(0)

        self.load_case_placeholder = QLabel("No load cases detected.\nSelect files to scan.")
        self.load_case_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.load_case_placeholder.setStyleSheet(f"color: {COLORS['muted']}; padding: 20px;")
        self.load_case_layout.addWidget(self.load_case_placeholder)
        self.load_case_layout.addStretch()

        self.load_case_scroll.setWidget(self.load_case_container)
        loadcases_layout.addWidget(self.load_case_scroll)

        # Load cases - Keep at 3, multiply by 10 for precision (30)
        data_row.addWidget(loadcases_group, stretch=30)

        # Track load case checkboxes
        self.load_case_checkboxes = {}  # load_case_name → QCheckBox
        self.load_case_sources = {}  # load_case_name → [(file, sheet), ...]
        self.all_load_cases = set()

        # Progress - Was 8, increase by tiny amount (80 → 81)
        # Files(49) + LoadCases(30) = 79, Progress = 81
        # Fine 1px adjustment for perfect alignment
        progress_group = QGroupBox("Import Progress")
        progress_group.setStyleSheet(self._groupbox_style())
        progress_layout = QVBoxLayout(progress_group)
        progress_layout.setContentsMargins(8, 12, 8, 8)  # Reduced padding

        self.progress_label = QLabel("Ready to import")
        self.progress_label.setStyleSheet(f"color: {COLORS['muted']};")
        progress_layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet(self._progress_style())
        progress_layout.addWidget(self.progress_bar)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet(self._log_style())
        progress_layout.addWidget(self.log_output)
        data_row.addWidget(progress_group, stretch=81)  # 1px fine adjustment

        main_layout.addLayout(data_row, stretch=1)

        # ============ BOTTOM ROW: Buttons ============
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(12)

        bottom_row.addStretch()

        # Buttons on right
        self.import_btn = create_styled_button("Start Import", "primary")
        self.import_btn.clicked.connect(self.start_import)
        self.import_btn.setEnabled(False)
        bottom_row.addWidget(self.import_btn)

        cancel_btn = create_styled_button("Cancel", "ghost")
        cancel_btn.clicked.connect(self.reject)
        bottom_row.addWidget(cancel_btn)

        main_layout.addLayout(bottom_row)

    def _apply_defaults(self) -> None:
        if self.context:
            self.project_input.setText(self.context.name)
            self.project_input.setEnabled(False)
            self.project_name = self.context.name
        self.update_import_button()

    # ------------------------------------------------------------------ #
    # Styling helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _groupbox_style() -> str:
        return f"""
            QGroupBox {{
                background-color: {COLORS['card']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                margin-top: 6px;
                padding-top: 12px;
                color: {COLORS['text']};
                font-weight: 600;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 4px;
            }}
        """

    @staticmethod
    def _entry_style(required: bool = False) -> str:
        # Show orange only when empty, blue when focused, gray otherwise
        return f"""
            QLineEdit {{
                background-color: {COLORS['background']};
                border: 2px solid {COLORS['border']};
                border-radius: 4px;
                padding: 6px 10px;
                color: {COLORS['text']};
            }}
            QLineEdit:focus {{
                border-color: {COLORS['accent']};
            }}
            QLineEdit[empty="true"] {{
                border-color: #ff8c00;
            }}
            QLineEdit[empty="true"]:focus {{
                border-color: {COLORS['accent']};
            }}
        """

    @staticmethod
    def _list_style() -> str:
        return f"""
            QListWidget {{
                background-color: {COLORS['background']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                padding: 4px;
                color: {COLORS['muted']};
            }}
            QListWidget::item {{
                padding: 4px 8px;
                border-radius: 2px;
            }}
            QListWidget::item:hover {{
                background-color: {COLORS['card']};
            }}
        """

    @staticmethod
    def _progress_style() -> str:
        return f"""
            QProgressBar {{
                background-color: {COLORS['background']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                height: 24px;
                text-align: center;
                color: {COLORS['text']};
            }}
            QProgressBar::chunk {{
                background-color: {COLORS['accent']};
                border-radius: 3px;
            }}
        """

    @staticmethod
    def _log_style() -> str:
        return f"""
            QTextEdit {{
                background-color: {COLORS['background']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                padding: 8px;
                color: {COLORS['muted']};
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 13px;
            }}
        """

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _update_empty_state(self, line_edit: QLineEdit) -> None:
        """Update the 'empty' property based on whether the field has text."""
        is_empty = not line_edit.text().strip()
        line_edit.setProperty("empty", "true" if is_empty else "false")
        line_edit.style().unpolish(line_edit)
        line_edit.style().polish(line_edit)

    def browse_folder(self) -> None:
        """Prompt the user to select a folder of Excel files."""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Folder with Excel Files",
            str(Path.home()),
        )
        if not folder:
            return

        self.folder_path = Path(folder)
        self.folder_input.setText(folder)

        if not self.project_input.text():
            self.project_input.setText(self.folder_path.name)

        self._preview_files()
        self.update_import_button()

    def _preview_files(self) -> None:
        """Populate preview list with Excel files and scan for load cases."""
        self.file_list.clear()
        self._excel_files = []
        self._prescan_result = None

        if not self.folder_path:
            return

        files: List[Path] = []
        for pattern in EXCEL_PATTERNS:
            files.extend(sorted(self.folder_path.glob(pattern)))

        self._excel_files = [f for f in files if not f.name.startswith("~$")]

        if not self._excel_files:
            self.log_output.append("- No Excel files found in folder.")
            return

        for file in self._excel_files:
            self.file_list.addItem(file.name)
        self.log_output.append(f"- Found {len(self._excel_files)} Excel file(s).")

        # Scan for load cases
        self._scan_load_cases()

    def _scan_load_cases(self) -> None:
        """Scan Excel files for load cases in background thread."""
        # Clear previous load cases
        self._clear_load_case_list()
        self._prescan_result = None

        if not self.folder_path or not self._excel_files:
            return

        # Disable controls during scan
        self._set_scan_controls_enabled(False)
        self.log_output.append("- Scanning files for load cases...")
        self.progress_label.setText("Scanning files...")

        # Start background scan
        self.scan_worker = LoadCaseScanWorker(
            folder_path=self.folder_path,
            result_types=self.result_types,
        )
        self.scan_worker.progress.connect(self._on_scan_progress)
        self.scan_worker.finished.connect(self._on_scan_finished)
        self.scan_worker.error.connect(self._on_scan_error)
        self.scan_worker.start()

        # Update button state (will be disabled during scan)
        self.update_import_button()

    def _on_scan_progress(self, message: str, current: int, total: int) -> None:
        """Update UI with scan progress."""
        self.progress_label.setText(message)
        if total > 0:
            percent = int((current / total) * 100)
            self.progress_bar.setValue(percent)
        # Also log scan progress to output
        self.log_output.append(f"  {message} ({current}/{total})")

    def _on_scan_finished(self, prescan: PrescanResult) -> None:
        """Handle scan completion."""
        self.scan_worker = None
        self.progress_label.setText("Ready to import")
        self.progress_bar.setValue(0)
        self._prescan_result = prescan

        file_load_cases = prescan.file_load_cases
        errors = prescan.errors

        if errors:
            self.log_output.append("- Scan completed with warnings:")
            for message in errors[:5]:
                self.log_output.append(f"  • {message}")
            if len(errors) > 5:
                self.log_output.append(f"  • ...and {len(errors) - 5} more")

        if not file_load_cases:
            self.log_output.append("- No load cases found")
            self._set_scan_controls_enabled(True)
            self.update_import_button()  # Re-enable button now that scan is complete
            return

        # Collect all unique load cases
        all_load_cases = set()
        load_case_sources = {}  # load_case → [(file, sheet), ...]

        for file_name, sheets in file_load_cases.items():
            for sheet_name, load_cases in sheets.items():
                for lc in load_cases:
                    all_load_cases.add(lc)
                    if lc not in load_case_sources:
                        load_case_sources[lc] = []
                    load_case_sources[lc].append((file_name, sheet_name))

        self.all_load_cases = all_load_cases
        self.load_case_sources = load_case_sources

        # Debug: Log load cases with multiple sources
        multi_source_lcs = [(lc, sources) for lc, sources in load_case_sources.items() if len(sources) > 1]
        if multi_source_lcs:
            self.log_output.append(f"- Load cases in multiple files ({len(multi_source_lcs)}):")
            for lc, sources in sorted(multi_source_lcs)[:5]:  # Show first 5
                file_list = ', '.join(set(f for f, s in sources))
                self.log_output.append(f"  {lc}: {len(sources)} occurrences in {file_list}")
            if len(multi_source_lcs) > 5:
                self.log_output.append(f"  ... and {len(multi_source_lcs) - 5} more")

        # Populate UI
        self._populate_load_case_list(sorted(all_load_cases))

        self.log_output.append(f"- Found {len(all_load_cases)} unique load case(s)")
        self._set_scan_controls_enabled(True)
        self.update_import_button()  # Re-enable button now that scan is complete

    def _on_scan_error(self, error_message: str) -> None:
        """Handle scan error."""
        self.scan_worker = None
        self.progress_label.setText("Scan failed")
        self.progress_bar.setValue(0)
        self.log_output.append(f"- Error scanning load cases: {error_message}")
        self._set_scan_controls_enabled(True)
        self.update_import_button()  # Re-enable button even after error

    def _set_scan_controls_enabled(self, enabled: bool) -> None:
        """Enable/disable controls during scan."""
        self.browse_btn.setEnabled(enabled)
        self.select_all_lc_btn.setEnabled(enabled and bool(self.load_case_checkboxes))
        self.select_none_lc_btn.setEnabled(enabled and bool(self.load_case_checkboxes))

    def _clear_load_case_list(self) -> None:
        """Clear all load case widgets from the container."""
        # Remove all checkbox widgets
        while self.load_case_layout.count() > 0:
            item = self.load_case_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.load_case_checkboxes.clear()
        self.all_load_cases = set()
        self.load_case_sources = {}

        # Show placeholder
        self.load_case_placeholder = QLabel("No load cases detected.\nSelect files to scan.")
        self.load_case_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.load_case_placeholder.setStyleSheet(f"color: {COLORS['muted']}; padding: 20px;")
        self.load_case_layout.addWidget(self.load_case_placeholder)
        self.load_case_layout.addStretch()

        # Disable action buttons
        self.select_all_lc_btn.setEnabled(False)
        self.select_none_lc_btn.setEnabled(False)

    def _populate_load_case_list(self, load_cases: List[str]) -> None:
        """Populate the load case list with checkboxes."""
        # Remove placeholder
        while self.load_case_layout.count() > 0:
            item = self.load_case_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Create checkmark image and save to temp file
        import tempfile
        import os

        checkmark_pixmap = QPixmap(18, 18)
        checkmark_pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(checkmark_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#ffffff"), 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        # Draw checkmark
        painter.drawLine(4, 9, 7, 12)
        painter.drawLine(7, 12, 14, 5)
        painter.end()

        # Save to temp file
        temp_dir = tempfile.gettempdir()
        checkmark_path = os.path.join(temp_dir, "rps_checkbox_check.png")
        checkmark_pixmap.save(checkmark_path, "PNG")

        # Convert path to URL format for stylesheet
        checkmark_url = checkmark_path.replace("\\", "/")

        # Add checkboxes for each load case
        for lc in load_cases:
            checkbox = QCheckBox(lc)  # Classic label without extra checkmark
            checkbox.setChecked(True)  # Default: all selected

            # Classic checkbox styling with visible checkmark
            checkbox.setStyleSheet(f"""
                QCheckBox {{
                    color: {COLORS['text']};
                    font-size: 13px;
                    padding: 6px 8px;
                    spacing: 8px;
                }}
                QCheckBox::indicator {{
                    width: 18px;
                    height: 18px;
                    border: 2px solid {COLORS['border']};
                    border-radius: 3px;
                    background-color: {COLORS['background']};
                }}
                QCheckBox::indicator:hover {{
                    border-color: {COLORS['accent']};
                    background-color: {COLORS['card']};
                }}
                QCheckBox::indicator:checked {{
                    background-color: {COLORS['accent']};
                    border-color: {COLORS['accent']};
                    image: url({checkmark_url});
                }}
                QCheckBox::indicator:checked:hover {{
                    background-color: #5a99a8;
                    border-color: #5a99a8;
                    image: url({checkmark_url});
                }}
                QCheckBox:hover {{
                    background-color: rgba(255, 255, 255, 0.03);
                    border-radius: 4px;
                }}
            """)

            self.load_case_layout.addWidget(checkbox)
            self.load_case_checkboxes[lc] = checkbox

        self.load_case_layout.addStretch()

        # Enable action buttons
        self.select_all_lc_btn.setEnabled(True)
        self.select_none_lc_btn.setEnabled(True)

    def _select_all_load_cases(self) -> None:
        """Select all load case checkboxes."""
        for checkbox in self.load_case_checkboxes.values():
            checkbox.setChecked(True)

    def _select_none_load_cases(self) -> None:
        """Deselect all load case checkboxes."""
        for checkbox in self.load_case_checkboxes.values():
            checkbox.setChecked(False)

    def _get_selected_load_cases(self) -> Set[str]:
        """Get the set of selected load cases from checkboxes."""
        selected = set()
        for lc, checkbox in self.load_case_checkboxes.items():
            if checkbox.isChecked():
                selected.add(lc)
        return selected

    def update_import_button(self) -> None:
        """Enable/disable the import button based on current inputs."""
        project_name = self.project_input.text().strip()
        result_set_name = self.result_set_input.text().strip()

        has_folder = self.folder_path is not None
        has_files = bool(self._excel_files)
        has_project = bool(project_name)
        has_result_set = bool(result_set_name)
        scan_complete = self.scan_worker is None  # Scanning is not in progress

        validation_message = ""
        is_valid = True

        # Check for duplicate result set
        if has_project and has_result_set:
            context = self._get_validation_context(project_name)
            if context and result_set_exists(context, result_set_name):
                is_valid = False

        self.import_btn.setEnabled(
            has_folder and has_files and has_project and has_result_set and is_valid and scan_complete
        )

    def _get_validation_context(self, project_name: str) -> Optional[ProjectContext]:
        if self.context and self.context.name == project_name:
            return self.context
        return get_project_context(project_name)

    # ------------------------------------------------------------------ #
    # Import execution
    # ------------------------------------------------------------------ #

    def start_import(self) -> None:
        """Kick off the background import."""
        # Immediate visual feedback
        self.progress_label.setText("Preparing import...")
        self.import_btn.setEnabled(False)
        QApplication.processEvents()  # Force UI update

        if not self.folder_path:
            self.log_output.append("- Select a folder before importing.")
            self.import_btn.setEnabled(True)
            self.progress_label.setText("Ready to import")
            return

        project_name = self.project_input.text().strip()
        result_set_name = self.result_set_input.text().strip()

        if not project_name:
            self.log_output.append("- Enter a project name before importing.")
            self.import_btn.setEnabled(True)
            self.progress_label.setText("Ready to import")
            return

        if not result_set_name:
            self.log_output.append("- Enter a result set name before importing.")
            self.import_btn.setEnabled(True)
            self.progress_label.setText("Ready to import")
            return

        self.progress_label.setText("Validating project...")
        try:
            context = ensure_project_context(project_name)
        except Exception as exc:  # pragma: no cover - UI feedback
            self.log_output.append(f"- Could not prepare project database: {exc}")
            self.import_btn.setEnabled(True)
            self.progress_label.setText("Ready to import")
            return

        if result_set_exists(context, result_set_name):
            self.log_output.append(
                f"- Result set '{result_set_name}' already exists for this project."
            )
            self.import_btn.setEnabled(True)
            self.progress_label.setText("Ready to import")
            return

        self.context = context
        self.project_name = context.name
        self.result_set_name = result_set_name

        self._set_controls_enabled(False)

        self.progress_bar.setValue(0)
        self.progress_label.setText("Preparing import...")
        self.log_output.append("")
        self.log_output.append(f"- Importing into project: {context.name}")
        self.log_output.append(f"- Result set: {result_set_name}")
        if self.result_types:
            joined = ", ".join(self.result_types)
            self.log_output.append(f"- Result types: {joined}")
        else:
            self.log_output.append("- Result types: all supported sheets")
        self.log_output.append(f"- Processing {len(self._excel_files)} file(s)...")

        # Get selected load cases from inline UI
        selected_load_cases = self._get_selected_load_cases()
        use_enhanced = len(selected_load_cases) > 0  # Use enhanced if load cases are selected

        if use_enhanced:
            self.log_output.append(f"- Enhanced import: {len(selected_load_cases)} load case(s) selected")

            # Check for conflicts and resolve if needed
            conflict_resolution = self._handle_conflicts(selected_load_cases)
            if conflict_resolution is None:
                # User cancelled conflict resolution
                self.log_output.append("- Import cancelled by user")
                self._set_controls_enabled(True)
                return
        else:
            self.log_output.append("- Standard import: all load cases will be imported")
            selected_load_cases = None
            conflict_resolution = None

        prescan_result = self._prescan_result
        if use_enhanced and prescan_result is None:
            self.log_output.append("- Load case scan missing; importer will perform a fresh prescan.")

        self.import_worker = FolderImportWorker(
            context=context,
            folder_path=self.folder_path,
            result_set_name=result_set_name,
            result_types=self.result_types,
            use_enhanced=use_enhanced,
            parent_widget=self,
            selected_load_cases=selected_load_cases,
            conflict_resolution=conflict_resolution,
            prescan_result=prescan_result,
        )
        self.import_worker.progress.connect(self.on_progress)
        self.import_worker.finished.connect(self.on_finished)
        self.import_worker.error.connect(self.on_error)
        self.import_worker.start()

    def _handle_conflicts(self, selected_load_cases: Set[str]) -> Optional[Dict]:
        """
        Check for conflicts and show resolution dialog if needed.

        Returns:
            conflict_resolution dict or None if cancelled
        """
        from gui.load_case_conflict_dialog import LoadCaseConflictDialog

        # Update UI to show we're checking for conflicts
        self.progress_label.setText("Checking for conflicts...")
        QApplication.processEvents()  # Force UI update

        # Detect conflicts for selected load cases only
        # Use cached load_case_sources from initial scan (no need to rescan!)
        # Build conflicts in the format expected by LoadCaseConflictDialog:
        # { load_case: { sheet_name: [file1, file2, ...] } }
        conflicts = {}
        for lc in selected_load_cases:
            sources = self.load_case_sources.get(lc, [])  # [(file, sheet), ...]
            if len(sources) > 1:
                # This load case appears in multiple files - group by sheet
                sheet_files = {}
                for file_name, sheet_name in sources:
                    if sheet_name not in sheet_files:
                        sheet_files[sheet_name] = []
                    sheet_files[sheet_name].append(file_name)

                # Only add if there are actual conflicts (same sheet in multiple files)
                has_conflict = any(len(files) > 1 for files in sheet_files.values())
                if has_conflict:
                    conflicts[lc] = sheet_files
                    # Debug logging
                    self.log_output.append(f"  Conflict: {lc} in {len(sources)} locations")
                    for sheet, files in sheet_files.items():
                        if len(files) > 1:
                            self.log_output.append(f"    {sheet}: {', '.join(files)}")

        if not conflicts:
            self.log_output.append("- No conflicts detected")
            self.progress_label.setText("Starting import...")
            return {}

        # Show conflict resolution dialog
        self.log_output.append(f"- Detected {len(conflicts)} conflicting load case(s)")
        self.progress_label.setText("Waiting for user input...")
        conflict_dialog = LoadCaseConflictDialog(conflicts, self)

        if not conflict_dialog.exec():
            return None  # User cancelled

        # Get resolution in format: {sheet: {load_case: file_name}}
        # Already in the correct format for the worker!
        sheet_resolution = conflict_dialog.get_resolution()

        self.log_output.append("- Conflicts resolved")
        self.progress_label.setText("Starting import...")
        return sheet_resolution

    def _set_controls_enabled(self, enabled: bool) -> None:
        self.import_btn.setEnabled(enabled)
        self.browse_btn.setEnabled(enabled)
        if not self._lock_project_name:
            self.project_input.setEnabled(enabled)
        self.result_set_input.setEnabled(enabled)

    def on_progress(self, message: str, current: int, total: int) -> None:
        """Update UI with background progress."""
        self.progress_label.setText(message)
        if total:
            percent = int((current / total) * 100)
            self.progress_bar.setValue(percent)
        self.log_output.append(f"  {message} ({current}/{total})")

    def on_finished(self, stats: dict) -> None:
        """Handle successful import completion."""
        self.import_stats = stats
        self.import_worker = None
        self.progress_bar.setValue(100)
        self.progress_label.setText("Import completed!")
        self.log_output.append("- Import completed successfully.")
        self.log_output.append(f"  Files processed: {stats.get('files_processed', 0)}/{stats.get('files_total', 0)}")
        self.log_output.append(f"  Load cases: {stats.get('load_cases', 0)}")
        self.log_output.append(f"  Stories: {stats.get('stories', 0)}")
        self.log_output.append(f"  Drifts: {stats.get('drifts', 0)}")
        self.log_output.append(f"  Accelerations: {stats.get('accelerations', 0)}")
        self.log_output.append(f"  Forces: {stats.get('forces', 0)}")
        self.log_output.append(f"  Displacements: {stats.get('displacements', 0)}")
        self._log_phase_timings(stats)

        errors = stats.get("errors") or []
        if errors:
            self.log_output.append(f"- {len(errors)} error(s) encountered:")
            for error in errors:
                self.log_output.append(f"  ! {error}")

        # Re-purpose import button as a close button
        self.import_btn.setText("Close")
        self.import_btn.setEnabled(True)
        self.import_btn.clicked.disconnect()
        self.import_btn.clicked.connect(self.accept)
        self.result_set_input.setEnabled(False)
        self.browse_btn.setEnabled(False)

    def on_error(self, error_message: str) -> None:
        """Handle worker errors."""
        self.progress_label.setText("Import failed")
        self.log_output.append(f"- Import failed: {error_message}")
        self._set_controls_enabled(True)
        self.import_btn.setText("Retry Import")
        self.import_worker = None

    # ------------------------------------------------------------------ #
    # Accessors
    # ------------------------------------------------------------------ #

    def get_project_name(self) -> Optional[str]:
        """Return the project name associated with this import."""
        return self.project_name

    def get_result_set_name(self) -> Optional[str]:
        """Return the result set name used for the import."""
        return self.result_set_name

    def get_import_stats(self) -> Optional[dict]:
        """Return the statistics from the most recent import."""
        return self.import_stats

    # ------------------------------------------------------------------ #
    # Diagnostics
    # ------------------------------------------------------------------ #

    def _log_phase_timings(self, stats: dict) -> None:
        """Emit the slowest sheet/file phases for troubleshooting."""
        timings = stats.get("phase_timings") or []
        if not timings:
            return

        # Aggregate per phase
        phase_totals: Dict[str, float] = {}
        for entry in timings:
            phase = entry.get("phase", "unknown")
            phase_totals[phase] = phase_totals.get(phase, 0.0) + float(entry.get("duration", 0.0))

        top_phases = sorted(phase_totals.items(), key=lambda item: item[1], reverse=True)[:3]
        top_runs = sorted(timings, key=lambda entry: entry.get("duration", 0.0), reverse=True)[:5]

        self.log_output.append("- Slowest phases (aggregate):")
        for phase, total in top_phases:
            self.log_output.append(f"    • {phase}: {total:.2f}s total")

        self.log_output.append("- Slowest sheets/files:")
        for entry in top_runs:
            phase = entry.get("phase", "unknown")
            file_name = entry.get("file", "?")
            duration = entry.get("duration", 0.0)
            extra_bits = []
            if entry.get("source"):
                extra_bits.append(entry["source"])
            if entry.get("sheet"):
                extra_bits.append(entry["sheet"])
            extra = f" ({', '.join(extra_bits)})" if extra_bits else ""
            self.log_output.append(f"    • {file_name}: {phase} {duration:.2f}s{extra}")
