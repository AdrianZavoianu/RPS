"""Folder import dialog with progress tracking."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Sequence

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
    QTextEdit,
    QVBoxLayout,
    QWidget,
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
    ) -> None:
        super().__init__()
        self.context = context
        self.folder_path = folder_path
        self.result_set_name = result_set_name
        self.result_types = list(result_types) if result_types else None
        self._session_factory = context.session_factory()

    def run(self) -> None:  # pragma: no cover - executes in worker thread
        """Run the import in background thread."""
        try:
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
        self.setMinimumSize(700, 560)

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
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        layout.addWidget(create_styled_label("Batch Import from Folder", "header"))
        subtitle = create_styled_label(
            "Select a folder with Excel exports. Supported sheets are Story Drifts, "
            "Story Accelerations, Story Forces, and Floors Displacements.",
            "muted",
        )
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        # Folder selection -------------------------------------------------
        folder_group = QGroupBox("Folder Selection")
        folder_group.setStyleSheet(self._groupbox_style())
        folder_layout = QVBoxLayout(folder_group)

        folder_input_layout = QHBoxLayout()
        self.folder_input = QLineEdit()
        self.folder_input.setReadOnly(True)
        self.folder_input.setPlaceholderText("Select folder containing Excel files...")
        self.folder_input.setStyleSheet(self._entry_style())
        folder_input_layout.addWidget(self.folder_input)

        self.browse_btn = create_styled_button("Browse...", "secondary", "sm")
        self.browse_btn.clicked.connect(self.browse_folder)
        folder_input_layout.addWidget(self.browse_btn)

        folder_layout.addLayout(folder_input_layout)

        self.file_list = QListWidget()
        self.file_list.setMaximumHeight(130)
        self.file_list.setStyleSheet(self._list_style())
        folder_layout.addWidget(QLabel("Files to process:"))
        folder_layout.addWidget(self.file_list)

        layout.addWidget(folder_group)

        # Project information ---------------------------------------------
        project_group = QGroupBox("Project Information")
        project_group.setStyleSheet(self._groupbox_style())
        project_layout = QVBoxLayout(project_group)

        project_layout.addWidget(QLabel("Project Name:"))
        self.project_input = QLineEdit()
        self.project_input.setPlaceholderText("Enter project name...")
        self.project_input.setStyleSheet(self._entry_style())
        self.project_input.textChanged.connect(self.update_import_button)
        project_layout.addWidget(self.project_input)

        layout.addWidget(project_group)

        # Result set information ------------------------------------------
        result_group = QGroupBox("Result Set Information")
        result_group.setStyleSheet(self._groupbox_style())
        result_layout = QVBoxLayout(result_group)

        result_layout.addWidget(QLabel("Result Set Name:"))
        self.result_set_input = QLineEdit()
        self.result_set_input.setPlaceholderText("Enter result set name (e.g., DES, MCE, SLE)...")
        self.result_set_input.setStyleSheet(self._entry_style())
        self.result_set_input.textChanged.connect(self.update_import_button)
        result_layout.addWidget(self.result_set_input)

        self.result_set_validation_label = QLabel("")
        self.result_set_validation_label.setStyleSheet(f"color: {COLORS['danger']}; font-size: 13px;")
        self.result_set_validation_label.setWordWrap(True)
        result_layout.addWidget(self.result_set_validation_label)

        layout.addWidget(result_group)

        # Progress + log ---------------------------------------------------
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
        self.log_output.setMaximumHeight(120)
        self.log_output.setStyleSheet(self._log_style())
        progress_layout.addWidget(self.log_output)

        layout.addWidget(progress_group)

        # Buttons ----------------------------------------------------------
        buttons = QDialogButtonBox()
        self.import_btn = create_styled_button("Start Import", "primary")
        self.import_btn.clicked.connect(self.start_import)
        self.import_btn.setEnabled(False)
        buttons.addButton(self.import_btn, QDialogButtonBox.ButtonRole.AcceptRole)

        cancel_btn = create_styled_button("Cancel", "ghost")
        cancel_btn.clicked.connect(self.reject)
        buttons.addButton(cancel_btn, QDialogButtonBox.ButtonRole.RejectRole)

        layout.addWidget(buttons)

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
        """Populate preview list with Excel files in the selected folder."""
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

        if has_project and has_result_set:
            context = self._get_validation_context(project_name)
            if context and result_set_exists(context, result_set_name):
                validation_message = (
                    f"Result set '{result_set_name}' already exists for this project."
                )
                is_valid = False

        self.result_set_validation_label.setText(validation_message)
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

        self.worker = FolderImportWorker(
            context=context,
            folder_path=self.folder_path,
            result_set_name=result_set_name,
            result_types=self.result_types,
        )
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.error.connect(self.on_error)
        self.worker.start()

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


