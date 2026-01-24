"""Time history import dialog for NLTHA Time Series data."""

import os
import tempfile
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFileDialog, QCheckBox,
    QMessageBox, QProgressBar, QTextEdit, QScrollArea,
    QWidget, QComboBox, QGroupBox, QListWidget, QApplication,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPixmap, QPen

from gui.design_tokens import FormStyles
from gui.ui_helpers import create_styled_button, create_styled_label
from gui.styles import COLORS
from gui.dialogs.import_.time_history_import_workers import (
    EXCEL_PATTERNS,
    TimeHistoryImportWorker,
    TimeHistoryPrescanWorker,
)


class TimeHistoryImportDialog(QDialog):
    """Dialog for importing time history (time series) data from a folder of Excel files.

    Thread Safety: Uses session_factory to create thread-safe sessions in worker threads.
    """

    import_completed = pyqtSignal(int)  # Emit count when import succeeds

    def __init__(self, project_id: int, project_name: str, session_factory: Callable[[], object], parent=None):
        super().__init__(parent)
        self.project_id = project_id
        self.project_name = project_name
        self.session_factory = session_factory
        self.folder_path: Optional[Path] = None
        self.worker = None
        self.prescan_worker = None
        self._file_load_cases: Dict[str, str] = {}  # file_path -> load_case_name
        self._load_case_files: Dict[str, List[str]] = {}  # load_case -> [file_paths]
        self._conflict_resolution: Dict[str, str] = {}  # load_case -> chosen_file
        self.load_case_checkboxes: dict[str, QCheckBox] = {}

        self.setWindowTitle(f"Load Time Series - {project_name}")
        self.setModal(True)
        self.setMinimumSize(1100, 700)
        self.resize(1200, 750)

        self._setup_ui()
        self._load_result_sets()
        self.setStyleSheet(FormStyles.dialog())

    def _setup_ui(self):
        """Create dialog layout matching folder import design."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 8, 16, 16)
        main_layout.setSpacing(12)

        # Header
        header = create_styled_label("Load Time Series", "header")
        header.setStyleSheet(f"color: {COLORS['text']}; font-size: 24px; font-weight: 600;")
        main_layout.addWidget(header)

        # Description
        desc = QLabel(
            "Import step-by-step time history data from ETABS/SAP2000 Excel exports.\n"
            "Required sheets: Story Drifts, Story Forces, Joint Displacements, Diaphragm Accelerations"
        )
        desc.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px;")
        desc.setWordWrap(True)
        main_layout.addWidget(desc)

        # Top row: Folder selection and Result Set
        config_row = QHBoxLayout()
        config_row.setSpacing(8)

        # Folder selection
        folder_group = QGroupBox("Folder Selection")
        folder_group.setStyleSheet(self._groupbox_style())
        folder_layout = QVBoxLayout(folder_group)
        folder_layout.setContentsMargins(8, 8, 8, 8)

        folder_input_layout = QHBoxLayout()
        self.folder_edit = QLineEdit()
        self.folder_edit.setReadOnly(True)
        self.folder_edit.setPlaceholderText("Select folder with time history Excel files...")
        self.folder_edit.setStyleSheet(self._entry_style(required=True))
        self.folder_edit.setProperty("empty", "true")
        folder_input_layout.addWidget(self.folder_edit)

        browse_btn = create_styled_button("Browse...", "secondary", "sm")
        browse_btn.clicked.connect(self._browse_folder)
        folder_input_layout.addWidget(browse_btn)
        self.browse_btn = browse_btn

        folder_layout.addLayout(folder_input_layout)
        config_row.addWidget(folder_group, stretch=2)

        # Result set selection
        result_set_group = QGroupBox("Result Set")
        result_set_group.setStyleSheet(self._groupbox_style())
        result_set_layout = QVBoxLayout(result_set_group)
        result_set_layout.setContentsMargins(8, 8, 8, 8)

        self.result_set_combo = QComboBox()
        self.result_set_combo.setPlaceholderText("Select result set...")
        self.result_set_combo.currentIndexChanged.connect(self._update_import_button)
        self.result_set_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS['background']};
                border: 2px solid {COLORS['border']};
                border-radius: 4px;
                padding: 6px 10px;
                color: {COLORS['text']};
            }}
            QComboBox:focus {{
                border-color: {COLORS['accent']};
            }}
            QComboBox::drop-down {{
                border: none;
                padding-right: 8px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {COLORS['card']};
                border: 1px solid {COLORS['border']};
                color: {COLORS['text']};
                selection-background-color: {COLORS['accent']};
            }}
        """)
        result_set_layout.addWidget(self.result_set_combo)

        help_text = QLabel("↑ Select the NLTHA result set to add time series data to")
        help_text.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px; font-style: italic;")
        result_set_layout.addWidget(help_text)

        config_row.addWidget(result_set_group, stretch=1)
        main_layout.addLayout(config_row)

        # Middle row: Files | Load Cases | Progress
        data_row = QHBoxLayout()
        data_row.setSpacing(8)

        # Files list
        files_group = QGroupBox("Files to Process")
        files_group.setStyleSheet(self._groupbox_style())
        files_layout = QVBoxLayout(files_group)

        self.file_list = QListWidget()
        self.file_list.setStyleSheet(self._list_style())
        files_layout.addWidget(self.file_list)
        data_row.addWidget(files_group, stretch=45)

        # Load case selection
        loadcases_group = QGroupBox("Load Cases")
        loadcases_group.setStyleSheet(self._groupbox_style())
        loadcases_layout = QVBoxLayout(loadcases_group)
        loadcases_layout.setContentsMargins(8, 12, 8, 8)

        # Quick actions
        lc_actions_layout = QHBoxLayout()
        self.select_all_btn = create_styled_button("All", "ghost", "sm")
        self.select_all_btn.clicked.connect(self._select_all_load_cases)
        self.select_all_btn.setEnabled(False)
        lc_actions_layout.addWidget(self.select_all_btn)

        self.select_none_btn = create_styled_button("None", "ghost", "sm")
        self.select_none_btn.clicked.connect(self._select_none_load_cases)
        self.select_none_btn.setEnabled(False)
        lc_actions_layout.addWidget(self.select_none_btn)

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

        self.load_case_container = QWidget()
        self.load_case_layout = QVBoxLayout(self.load_case_container)
        self.load_case_layout.setContentsMargins(0, 0, 0, 0)
        self.load_case_layout.setSpacing(0)

        self.load_case_placeholder = QLabel("No load cases detected.\nSelect a folder to scan.")
        self.load_case_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.load_case_placeholder.setStyleSheet(f"color: {COLORS['muted']}; padding: 20px;")
        self.load_case_layout.addWidget(self.load_case_placeholder)
        self.load_case_layout.addStretch()

        self.load_case_scroll.setWidget(self.load_case_container)
        loadcases_layout.addWidget(self.load_case_scroll)

        data_row.addWidget(loadcases_group, stretch=30)

        # Progress section
        progress_group = QGroupBox("Import Progress")
        progress_group.setStyleSheet(self._groupbox_style())
        progress_layout = QVBoxLayout(progress_group)
        progress_layout.setContentsMargins(8, 12, 8, 8)

        self.progress_label = QLabel("Ready to import")
        self.progress_label.setStyleSheet(f"color: {COLORS['muted']};")
        progress_layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet(self._progress_style())
        progress_layout.addWidget(self.progress_bar)

        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setStyleSheet(self._log_style())
        progress_layout.addWidget(self.status_text)

        data_row.addWidget(progress_group, stretch=85)

        main_layout.addLayout(data_row, stretch=1)

        # Bottom buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.cancel_btn = create_styled_button("Cancel", "ghost")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        self.import_btn = create_styled_button("Load Time Series", "primary")
        self.import_btn.clicked.connect(self._on_import)
        self.import_btn.setEnabled(False)
        button_layout.addWidget(self.import_btn)

        main_layout.addLayout(button_layout)

    def _load_result_sets(self):
        """Load available NLTHA result sets into combo box.

        Uses a short-lived session for thread safety during dialog initialization.
        """
        from services.data_access import DataAccessService

        data_service = DataAccessService(self.session_factory)
        result_sets = data_service.get_result_sets(self.project_id)

        # Filter to NLTHA result sets only
        nltha_sets = [rs for rs in result_sets if rs.analysis_type != "Pushover"]

        self.result_set_combo.clear()
        for rs in nltha_sets:
            self.result_set_combo.addItem(rs.name, rs.id)

        if not nltha_sets:
            self.status_text.append("⚠️ No NLTHA result sets found. Import envelope data first using 'Load NLTHA Data'.")

    def _browse_folder(self):
        """Open folder browser to select folder with Excel files."""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Folder with Time History Excel Files",
            str(Path.home()),
        )

        if folder:
            self.folder_path = Path(folder)
            self.folder_edit.setText(str(self.folder_path))
            self.folder_edit.setProperty("empty", "false")
            self.folder_edit.style().unpolish(self.folder_edit)
            self.folder_edit.style().polish(self.folder_edit)
            self._preview_files()
            self._update_import_button()

    def _preview_files(self):
        """Populate preview list with Excel files and scan for load cases."""
        self.file_list.clear()
        self._file_load_cases = {}
        self._load_case_files = {}
        self._clear_load_case_list()

        if not self.folder_path:
            return

        files: List[Path] = []
        for pattern in EXCEL_PATTERNS:
            files.extend(sorted(self.folder_path.glob(pattern)))

        files = [f for f in files if not f.name.startswith("~$")]

        if not files:
            self.status_text.append("- No Excel files found in folder.")
            return

        for file in files:
            self.file_list.addItem(file.name)
        self.status_text.append(f"- Found {len(files)} Excel file(s).")

        # Start background scan
        self._scan_load_cases()

    def _scan_load_cases(self):
        """Scan Excel files for load cases in background thread."""
        self._clear_load_case_list()

        if not self.folder_path:
            return

        # Disable controls during scan
        self._set_scan_controls_enabled(False)
        self.status_text.append("- Scanning files for load cases...")
        self.progress_label.setText("Scanning files...")

        self.prescan_worker = TimeHistoryPrescanWorker(self.folder_path)
        self.prescan_worker.progress.connect(self._on_scan_progress)
        self.prescan_worker.finished.connect(self._on_scan_finished)
        self.prescan_worker.error.connect(self._on_scan_error)
        self.prescan_worker.start()

        self._update_import_button()

    def _on_scan_progress(self, message: str, current: int, total: int):
        """Update UI with scan progress."""
        self.progress_label.setText(message)
        if total > 0:
            percent = int((current / total) * 100)
            self.progress_bar.setValue(percent)

    def _on_scan_finished(self, file_load_cases: Dict[str, str]):
        """Handle scan completion."""
        self.prescan_worker = None
        self.progress_label.setText("Ready to import")
        self.progress_bar.setValue(0)

        self._file_load_cases = file_load_cases

        if not file_load_cases:
            self.status_text.append("- No time history load cases found in files.")
            self._set_scan_controls_enabled(True)
            self._update_import_button()
            return

        # Build load_case -> [files] mapping to detect conflicts
        self._load_case_files = {}
        for file_path, load_case in file_load_cases.items():
            if load_case not in self._load_case_files:
                self._load_case_files[load_case] = []
            self._load_case_files[load_case].append(file_path)

        # Log conflicts
        conflicts = {lc: files for lc, files in self._load_case_files.items() if len(files) > 1}
        if conflicts:
            self.status_text.append(f"- Found {len(conflicts)} load case(s) in multiple files:")
            for lc, files in sorted(conflicts.items())[:5]:
                file_names = ', '.join(Path(f).name for f in files)
                self.status_text.append(f"  {lc}: {file_names}")
            if len(conflicts) > 5:
                self.status_text.append(f"  ... and {len(conflicts) - 5} more")

        # Populate UI
        self._populate_load_case_list(sorted(self._load_case_files.keys()))
        self.status_text.append(f"- Found {len(self._load_case_files)} unique load case(s)")

        self._set_scan_controls_enabled(True)
        self._update_import_button()

    def _on_scan_error(self, error_msg: str):
        """Handle scan error."""
        self.prescan_worker = None
        self.progress_label.setText("Scan failed")
        self.progress_bar.setValue(0)
        self.status_text.append(f"- Error scanning files: {error_msg}")
        self._set_scan_controls_enabled(True)
        self._update_import_button()

    def _set_scan_controls_enabled(self, enabled: bool):
        """Enable/disable controls during scan."""
        self.browse_btn.setEnabled(enabled)
        self.select_all_btn.setEnabled(enabled and bool(self.load_case_checkboxes))
        self.select_none_btn.setEnabled(enabled and bool(self.load_case_checkboxes))

    def _clear_load_case_list(self):
        """Clear all load case widgets from the container."""
        while self.load_case_layout.count() > 0:
            item = self.load_case_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.load_case_checkboxes.clear()

        self.load_case_placeholder = QLabel("No load cases detected.\nSelect a folder to scan.")
        self.load_case_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.load_case_placeholder.setStyleSheet(f"color: {COLORS['muted']}; padding: 20px;")
        self.load_case_layout.addWidget(self.load_case_placeholder)
        self.load_case_layout.addStretch()

        self.select_all_btn.setEnabled(False)
        self.select_none_btn.setEnabled(False)

    def _populate_load_case_list(self, load_cases: List[str]):
        """Populate the load case list with checkboxes."""
        while self.load_case_layout.count() > 0:
            item = self.load_case_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Create checkmark image
        checkmark_pixmap = QPixmap(18, 18)
        checkmark_pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(checkmark_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#ffffff"), 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(4, 9, 7, 12)
        painter.drawLine(7, 12, 14, 5)
        painter.end()

        temp_dir = tempfile.gettempdir()
        checkmark_path = os.path.join(temp_dir, "rps_ts_checkbox_check.png")
        checkmark_pixmap.save(checkmark_path, "PNG")
        checkmark_url = checkmark_path.replace("\\", "/")

        for lc in load_cases:
            # Show file count in label if conflicts
            files = self._load_case_files.get(lc, [])
            if len(files) > 1:
                label = f"{lc} ({len(files)} files)"
            else:
                label = lc

            checkbox = QCheckBox(label)
            checkbox.setChecked(True)
            checkbox.stateChanged.connect(self._update_import_button)

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
                }}
                QCheckBox:hover {{
                    background-color: rgba(255, 255, 255, 0.03);
                    border-radius: 4px;
                }}
            """)

            self.load_case_layout.addWidget(checkbox)
            self.load_case_checkboxes[lc] = checkbox

        self.load_case_layout.addStretch()
        self.select_all_btn.setEnabled(True)
        self.select_none_btn.setEnabled(True)

    def _select_all_load_cases(self):
        """Select all load case checkboxes."""
        for checkbox in self.load_case_checkboxes.values():
            checkbox.setChecked(True)

    def _select_none_load_cases(self):
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

    def _update_import_button(self):
        """Enable import button when all requirements are met."""
        has_folder = self.folder_path is not None
        has_result_set = self.result_set_combo.currentIndex() >= 0
        has_load_cases = len(self._get_selected_load_cases()) > 0
        scan_complete = self.prescan_worker is None

        self.import_btn.setEnabled(has_folder and has_result_set and has_load_cases and scan_complete)

    def _on_import(self):
        """Start the import process."""
        if not self.folder_path:
            QMessageBox.warning(self, "No Folder", "Please select a folder first.")
            return

        result_set_id = self.result_set_combo.currentData()
        if not result_set_id:
            QMessageBox.warning(self, "No Result Set", "Please select a result set.")
            return

        selected_load_cases = self._get_selected_load_cases()
        if not selected_load_cases:
            QMessageBox.warning(self, "No Load Cases", "Please select at least one load case.")
            return

        # Check for conflicts
        self._conflict_resolution = self._handle_conflicts(selected_load_cases)
        if self._conflict_resolution is None:
            # User cancelled
            self.status_text.append("- Import cancelled by user")
            return

        # Get list of files to process
        file_paths = [Path(f) for f in self._file_load_cases.keys()]

        # Disable controls during import
        self.import_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)
        self.browse_btn.setEnabled(False)
        self.progress_bar.setValue(0)

        # Start import worker with session_factory for thread-safe session creation
        self.worker = TimeHistoryImportWorker(
            self.session_factory,
            file_paths,
            self.project_id,
            result_set_id,
            selected_load_cases,
            self._conflict_resolution,
        )
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _handle_conflicts(self, selected_load_cases: Set[str]) -> Optional[Dict[str, str]]:
        """
        Check for conflicts and show resolution dialog if needed.

        Returns:
            Dict mapping load_case -> chosen_file, or None if cancelled
        """
        from gui.load_case_conflict_dialog import LoadCaseConflictDialog

        self.progress_label.setText("Checking for conflicts...")
        QApplication.processEvents()

        # Build conflicts dict for dialog
        # For time series, we only care about load case conflicts (same load case in multiple files)
        # Format: {load_case: {sheet: [files]}}
        # Since time series has one load case per file, we use "Time Series" as the sheet
        conflicts = {}
        for lc in selected_load_cases:
            files = self._load_case_files.get(lc, [])
            if len(files) > 1:
                file_names = [Path(f).name for f in files]
                conflicts[lc] = {"Time Series": file_names}

        if not conflicts:
            self.status_text.append("- No conflicts detected")
            self.progress_label.setText("Starting import...")
            return {}

        # Show conflict resolution dialog
        self.status_text.append(f"- Detected {len(conflicts)} conflicting load case(s)")
        self.progress_label.setText("Waiting for user input...")
        conflict_dialog = LoadCaseConflictDialog(conflicts, self)

        if not conflict_dialog.exec():
            return None  # User cancelled

        # Get resolution and convert to simple format
        # Dialog returns: {sheet: {load_case: file_name}}
        # We need: {load_case: full_file_path}
        sheet_resolution = conflict_dialog.get_resolution()
        resolution = {}

        ts_resolution = sheet_resolution.get("Time Series", {})
        for load_case, file_name in ts_resolution.items():
            if file_name is None:
                # Skip this load case
                resolution[load_case] = None
            else:
                # Find full path for this file name
                for file_path in self._load_case_files.get(load_case, []):
                    if Path(file_path).name == file_name:
                        resolution[load_case] = file_path
                        break

        self.status_text.append("- Conflicts resolved")
        self.progress_label.setText("Starting import...")
        return resolution

    def _on_progress(self, message: str, current: int, total: int):
        """Handle progress updates from worker."""
        if total > 0:
            percent = int((current / total) * 100)
            self.progress_bar.setValue(percent)
        self.status_text.append(message)

    def _on_finished(self, count: int, result_set_id: int):
        """Handle import completion."""
        self.progress_bar.setValue(100)
        self.status_text.append(f"\n✅ Import complete! {count} time series records imported.")

        self.import_completed.emit(count)

        # Re-enable close button
        self.cancel_btn.setEnabled(True)
        self.cancel_btn.setText("Close")

        # Convert import button to close
        self.import_btn.setText("Close")
        self.import_btn.setEnabled(True)
        self.import_btn.clicked.disconnect()
        self.import_btn.clicked.connect(self.accept)

    def _on_error(self, error_msg: str):
        """Handle import error."""
        self.progress_bar.setValue(0)
        self.status_text.append(f"\n❌ Error: {error_msg}")

        QMessageBox.critical(self, "Import Error", f"Failed to import time history data:\n{error_msg}")

        # Re-enable controls
        self.import_btn.setEnabled(True)
        self.cancel_btn.setEnabled(True)
        self.browse_btn.setEnabled(True)

    # Styling helpers
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
