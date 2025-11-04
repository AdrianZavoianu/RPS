"""Folder import dialog with progress tracking."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
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
from services.project_service import (
    ProjectContext,
    ensure_project_context,
    get_project_context,
    result_set_exists,
)


EXCEL_PATTERNS: Sequence[str] = ("*.xlsx", "*.xls")


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
        self._session_factory = context.session_factory()

    def run(self) -> None:  # pragma: no cover - executes in worker thread
        """Run the import in background thread."""
        try:
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
                )
                stats = importer.import_all()
                self.finished.emit(stats)
        except Exception as exc:  # pragma: no cover - UI feedback
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
        self.setWindowTitle("Import from Folder")
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

        self.worker: Optional[FolderImportWorker] = None

        self._build_ui()
        self._apply_defaults()

    # ------------------------------------------------------------------ #
    # UI setup
    # ------------------------------------------------------------------ #

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        # Header
        main_layout.addWidget(create_styled_label("Batch Import from Folder", "header"))
        subtitle = create_styled_label(
            "Select a folder with Excel exports. Supported sheets are Story Drifts, "
            "Story Accelerations, Story Forces, and Floors Displacements.",
            "muted",
        )
        subtitle.setWordWrap(True)
        main_layout.addWidget(subtitle)

        # ============ TOP ROW: All Configuration in Horizontal Layout ============
        config_row = QHBoxLayout()
        config_row.setSpacing(12)

        # Folder selection
        folder_group = QGroupBox("Folder Selection")
        folder_group.setStyleSheet(self._groupbox_style())
        folder_layout = QVBoxLayout(folder_group)

        folder_input_layout = QHBoxLayout()
        self.folder_input = QLineEdit()
        self.folder_input.setReadOnly(True)
        self.folder_input.setPlaceholderText("Select folder...")
        self.folder_input.setStyleSheet(self._entry_style())
        folder_input_layout.addWidget(self.folder_input)

        self.browse_btn = create_styled_button("Browse", "secondary", "sm")
        self.browse_btn.clicked.connect(self.browse_folder)
        folder_input_layout.addWidget(self.browse_btn)

        folder_layout.addLayout(folder_input_layout)
        config_row.addWidget(folder_group, stretch=2)

        # Project information - with required indicator
        project_group = QGroupBox("Project *")  # Asterisk indicates required
        project_group.setStyleSheet(self._groupbox_style())
        project_layout = QVBoxLayout(project_group)

        self.project_input = QLineEdit()
        self.project_input.setPlaceholderText("Required: Project name...")
        self.project_input.setStyleSheet(self._entry_style())
        self.project_input.textChanged.connect(self.update_import_button)
        project_layout.addWidget(self.project_input)
        config_row.addWidget(project_group, stretch=1)

        # Result set information - with required indicator
        result_group = QGroupBox("Result Set *")  # Asterisk indicates required
        result_group.setStyleSheet(self._groupbox_style())
        result_layout = QVBoxLayout(result_group)

        self.result_set_input = QLineEdit()
        self.result_set_input.setPlaceholderText("Required: e.g., DES, MCE, SLE...")
        self.result_set_input.setStyleSheet(self._entry_style())
        self.result_set_input.textChanged.connect(self.update_import_button)
        result_layout.addWidget(self.result_set_input)

        self.result_set_validation_label = QLabel("Required field")
        self.result_set_validation_label.setStyleSheet(f"color: {COLORS['warning']}; font-size: 12px; font-style: italic;")
        self.result_set_validation_label.setWordWrap(True)
        result_layout.addWidget(self.result_set_validation_label)
        config_row.addWidget(result_group, stretch=1)

        main_layout.addLayout(config_row)

        # ============ MIDDLE ROW: Files | Load Cases | Progress ============
        data_row = QHBoxLayout()
        data_row.setSpacing(12)

        # Files to process (compact)
        files_group = QGroupBox("Files to Process")
        files_group.setStyleSheet(self._groupbox_style())
        files_layout = QVBoxLayout(files_group)

        self.file_list = QListWidget()
        self.file_list.setStyleSheet(self._list_style())
        files_layout.addWidget(self.file_list)
        data_row.addWidget(files_group, stretch=1)

        # Load Cases Selection (middle)
        loadcases_group = QGroupBox("Load Cases")
        loadcases_group.setStyleSheet(self._groupbox_style())
        loadcases_layout = QVBoxLayout(loadcases_group)

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

        data_row.addWidget(loadcases_group, stretch=1)

        # Track load case checkboxes
        self.load_case_checkboxes = {}  # load_case_name → QCheckBox
        self.load_case_sources = {}  # load_case_name → [(file, sheet), ...]
        self.all_load_cases = set()

        # Progress (compact)
        progress_group = QGroupBox("Import Progress")
        progress_group.setStyleSheet(self._groupbox_style())
        progress_layout = QVBoxLayout(progress_group)

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
        data_row.addWidget(progress_group, stretch=1)

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
                margin-top: 8px;
                padding-top: 16px;
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
    def _entry_style() -> str:
        return f"""
            QLineEdit {{
                background-color: {COLORS['background']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                padding: 8px 12px;
                color: {COLORS['text']};
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
        """Scan Excel files for load cases and populate the load case list."""
        from processing.enhanced_folder_importer import EnhancedFolderImporter

        # Clear previous load cases
        self._clear_load_case_list()

        if not self.folder_path or not self._excel_files:
            return

        self.log_output.append("- Scanning files for load cases...")

        # Convert result_types to set if present
        result_types_set = None
        if self.result_types:
            result_types_set = {rt.strip().lower() for rt in self.result_types}

        try:
            # Prescan folder for load cases
            file_load_cases = EnhancedFolderImporter.prescan_folder_for_load_cases(
                self.folder_path,
                result_types_set,
                None  # No progress callback for inline scan
            )

            if not file_load_cases:
                self.log_output.append("- No load cases found")
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

            # Populate UI
            self._populate_load_case_list(sorted(all_load_cases))

            self.log_output.append(f"- Found {len(all_load_cases)} unique load case(s)")

        except Exception as exc:
            self.log_output.append(f"- Error scanning load cases: {exc}")

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

        # Add checkboxes for each load case
        for lc in load_cases:
            checkbox = QCheckBox(lc)
            checkbox.setChecked(True)  # Default: all selected
            checkbox.setStyleSheet(f"""
                QCheckBox {{
                    color: {COLORS['text']};
                    font-size: 13px;
                    padding: 6px 12px;
                    spacing: 8px;
                }}
                QCheckBox::indicator {{
                    width: 18px;
                    height: 18px;
                    border: 2px solid {COLORS['border']};
                    border-radius: 4px;
                    background-color: {COLORS['background']};
                }}
                QCheckBox::indicator:hover {{
                    border-color: {COLORS['accent']};
                    background-color: {COLORS['card']};
                }}
                QCheckBox::indicator:checked {{
                    background-color: {COLORS['accent']};
                    border-color: {COLORS['accent']};
                }}
                QCheckBox::indicator:checked:hover {{
                    background-color: #7fedfa;
                    border-color: #7fedfa;
                }}
                QCheckBox:hover {{
                    background-color: rgba(255, 255, 255, 0.03);
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

        validation_message = ""
        is_valid = True

        # Show different messages based on what's missing
        if not has_result_set:
            validation_message = "Required field - enter a result set name"
        elif has_project and has_result_set:
            context = self._get_validation_context(project_name)
            if context and result_set_exists(context, result_set_name):
                validation_message = f"⚠ Result set '{result_set_name}' already exists"
                is_valid = False
            else:
                validation_message = "✓ Ready to import"

        # Update validation label styling based on state
        if not is_valid:
            color = COLORS['danger']
        elif has_result_set and is_valid:
            color = COLORS['success']
        else:
            color = COLORS['warning']

        self.result_set_validation_label.setText(validation_message)
        self.result_set_validation_label.setStyleSheet(f"color: {color}; font-size: 12px; font-style: italic;")

        self.import_btn.setEnabled(
            has_folder and has_files and has_project and has_result_set and is_valid
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
        if not self.folder_path:
            self.log_output.append("- Select a folder before importing.")
            return

        project_name = self.project_input.text().strip()
        result_set_name = self.result_set_input.text().strip()

        if not project_name:
            self.log_output.append("- Enter a project name before importing.")
            return

        if not result_set_name:
            self.log_output.append("- Enter a result set name before importing.")
            return

        try:
            context = ensure_project_context(project_name)
        except Exception as exc:  # pragma: no cover - UI feedback
            self.log_output.append(f"- Could not prepare project database: {exc}")
            return

        if result_set_exists(context, result_set_name):
            self.log_output.append(
                f"- Result set '{result_set_name}' already exists for this project."
            )
            return

        self.context = context
        self.project_name = context.name
        self.result_set_name = result_set_name

        self._set_controls_enabled(False)

        self.progress_bar.setValue(0)
        self.progress_label.setText("Starting import...")
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

        self.worker = FolderImportWorker(
            context=context,
            folder_path=self.folder_path,
            result_set_name=result_set_name,
            result_types=self.result_types,
            use_enhanced=use_enhanced,
            parent_widget=self,
            selected_load_cases=selected_load_cases,
            conflict_resolution=conflict_resolution,
        )
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.error.connect(self.on_error)
        self.worker.start()

    def _handle_conflicts(self, selected_load_cases: Set[str]) -> Optional[Dict]:
        """
        Check for conflicts and show resolution dialog if needed.

        Returns:
            conflict_resolution dict or None if cancelled
        """
        from processing.enhanced_folder_importer import EnhancedFolderImporter
        from gui.load_case_conflict_dialog import LoadCaseConflictDialog

        # Convert result_types to set if present
        result_types_set = None
        if self.result_types:
            result_types_set = {rt.strip().lower() for rt in self.result_types}

        # Rescan to build file_load_cases structure for conflict detection
        file_load_cases = EnhancedFolderImporter.prescan_folder_for_load_cases(
            self.folder_path,
            result_types_set,
            None  # No progress callback
        )

        # Detect conflicts for selected load cases only
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

        if not conflicts:
            self.log_output.append("- No conflicts detected")
            return {}

        # Show conflict resolution dialog
        self.log_output.append(f"- Detected {len(conflicts)} conflicting load case(s)")
        conflict_dialog = LoadCaseConflictDialog(conflicts, self)

        if not conflict_dialog.exec():
            return None  # User cancelled

        # Get resolution in format: {load_case: file_name}
        lc_resolution = conflict_dialog.get_resolution()

        # Transform to format expected by worker: {sheet: {load_case: file}}
        sheet_resolution = {}
        for lc, file_name in lc_resolution.items():
            # Find all sheets this load case appears in
            if lc in conflicts:
                for sheet_name in conflicts[lc].keys():
                    if sheet_name not in sheet_resolution:
                        sheet_resolution[sheet_name] = {}
                    sheet_resolution[sheet_name][lc] = file_name

        self.log_output.append("- Conflicts resolved")
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
        self.worker = None
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
        self.worker = None

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


