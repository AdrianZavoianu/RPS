"""Pushover curve import dialog."""

from pathlib import Path
from typing import Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFileDialog, QComboBox,
    QDialogButtonBox, QMessageBox, QProgressBar, QTextEdit,
    QRadioButton, QButtonGroup
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from .design_tokens import FormStyles
from .ui_helpers import create_styled_button, create_styled_label
from .styles import COLORS
from processing.pushover_curve_importer import PushoverImporter
from processing.pushover_curve_parser import PushoverParser


class PushoverCurveImportWorker(QThread):
    """Worker thread for pushover curve import (non-blocking UI)."""

    progress = pyqtSignal(str)  # Status message
    finished = pyqtSignal(dict)  # Import statistics
    error = pyqtSignal(str)  # Error message

    def __init__(self, session, file_path: Path, project_id: int,
                 result_set_name: str, base_story: str, direction: str, overwrite: bool):
        super().__init__()
        self.session = session
        self.file_path = file_path
        self.project_id = project_id
        self.result_set_name = result_set_name
        self.base_story = base_story
        self.direction = direction
        self.overwrite = overwrite

    def run(self):
        """Execute import in background thread."""
        try:
            self.progress.emit("Initializing importer...")
            importer = PushoverImporter(self.session)

            if self.direction:
                self.progress.emit(f"Parsing Excel file (direction: {self.direction})...")
            else:
                self.progress.emit("Parsing Excel file (both X and Y directions)...")

            stats = importer.import_pushover_file(
                file_path=self.file_path,
                project_id=self.project_id,
                result_set_name=self.result_set_name,
                base_story=self.base_story,
                direction=self.direction,
                overwrite=self.overwrite
            )

            self.finished.emit(stats)

        except Exception as e:
            self.error.emit(str(e))


class PushoverImportDialog(QDialog):
    """Dialog for importing pushover curve data from Excel files."""

    import_completed = pyqtSignal(dict)  # Emit stats when import succeeds

    def __init__(self, project_id: int, project_name: str, session, parent=None):
        super().__init__(parent)
        self.project_id = project_id
        self.project_name = project_name
        self.session = session
        self.file_path = None
        self.worker = None

        self.setWindowTitle(f"Import Pushover Curves - {project_name}")
        self.setModal(True)
        self.setMinimumWidth(600)
        self.resize(600, 500)

        self._setup_ui()
        self.setStyleSheet(FormStyles.dialog())

    def _setup_ui(self):
        """Create dialog layout."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # Title
        title = create_styled_label("Import Pushover Curves", "header")
        layout.addWidget(title)

        # Description
        desc = QLabel(
            "Import pushover capacity curves from ETABS/SAP2000 Excel export.\n"
            "Required sheets: Joint Displacements, Story Forces"
        )
        desc.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # File selection
        file_layout = QHBoxLayout()
        file_label = QLabel("Excel File:")
        file_label.setFixedWidth(120)
        self.file_edit = QLineEdit()
        self.file_edit.setReadOnly(True)
        self.file_edit.setPlaceholderText("Select pushover Excel file...")
        browse_btn = create_styled_button("Browse...", "secondary", "sm")
        browse_btn.clicked.connect(self._browse_file)
        file_layout.addWidget(file_label)
        file_layout.addWidget(self.file_edit)
        file_layout.addWidget(browse_btn)
        layout.addLayout(file_layout)

        # Result set name
        result_set_layout = QHBoxLayout()
        result_set_label = QLabel("Result Set Name:")
        result_set_label.setFixedWidth(120)
        self.result_set_edit = QLineEdit()
        self.result_set_edit.setPlaceholderText("e.g., 160Will_Push, Project_Pushover...")
        result_set_layout.addWidget(result_set_label)
        result_set_layout.addWidget(self.result_set_edit)
        layout.addLayout(result_set_layout)

        # Base story selection
        story_layout = QHBoxLayout()
        story_label = QLabel("Base Story:")
        story_label.setFixedWidth(120)
        self.story_combo = QComboBox()
        self.story_combo.setEnabled(False)
        self.story_combo.setPlaceholderText("Select file first...")
        story_layout.addWidget(story_label)
        story_layout.addWidget(self.story_combo)
        layout.addLayout(story_layout)

        # Help text for base story
        story_help = QLabel("↑ Select the story at building base for shear extraction (typically foundation or first floor)")
        story_help.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px; font-style: italic;")
        story_help.setWordWrap(True)
        layout.addWidget(story_help)

        # Overwrite option
        # self.overwrite_check = QCheckBox("Overwrite existing data")
        # self.overwrite_check.setChecked(True)
        # layout.addWidget(self.overwrite_check)

        # Progress area
        progress_group = QLabel("Import Progress:")
        progress_group.setStyleSheet(f"color: {COLORS['text']}; font-weight: bold; margin-top: 8px;")
        layout.addWidget(progress_group)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        layout.addWidget(self.progress_bar)

        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMaximumHeight(150)
        self.status_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLORS['background']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                padding: 8px;
                color: {COLORS['text_secondary']};
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
            }}
        """)
        layout.addWidget(self.status_text)

        layout.addStretch()

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.cancel_btn = create_styled_button("Cancel", "secondary", "md")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        self.import_btn = create_styled_button("Import Curves", "primary", "md")
        self.import_btn.clicked.connect(self._on_import)
        self.import_btn.setEnabled(False)
        button_layout.addWidget(self.import_btn)

        layout.addLayout(button_layout)

    def _browse_file(self):
        """Open file browser to select Excel file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Pushover Excel File",
            "",
            "Excel Files (*.xlsx *.xls)"
        )

        if file_path:
            self.file_path = Path(file_path)
            self.file_edit.setText(str(self.file_path))
            self._log(f"Selected file: {self.file_path.name}")

            # Load available stories
            self._load_stories()

    def _load_stories(self):
        """Load available stories from the selected Excel file."""
        try:
            self._log("Scanning Excel file for stories...")
            parser = PushoverParser(self.file_path)
            stories = parser.get_available_stories()

            if not stories:
                self._log("⚠ No stories found in file!", error=True)
                QMessageBox.warning(
                    self,
                    "No Stories Found",
                    "Could not find any stories in the Story Forces sheet."
                )
                return

            self.story_combo.clear()
            self.story_combo.addItems(stories)
            self.story_combo.setEnabled(True)
            self._log(f"Found {len(stories)} stories: {', '.join(stories)}")

            # Auto-select first story (usually base)
            if stories:
                self.story_combo.setCurrentIndex(0)

            # Enable import button
            self.import_btn.setEnabled(True)

        except Exception as e:
            self._log(f"✗ Error reading file: {str(e)}", error=True)
            QMessageBox.critical(
                self,
                "File Read Error",
                f"Failed to read Excel file:\n{str(e)}"
            )

    def _on_import(self):
        """Start import process."""
        # Validation
        if not self.file_path:
            QMessageBox.warning(self, "No File", "Please select an Excel file.")
            return

        result_set_name = self.result_set_edit.text().strip()
        if not result_set_name:
            QMessageBox.warning(self, "No Result Set", "Please enter a result set name.")
            return

        base_story = self.story_combo.currentText()
        if not base_story:
            QMessageBox.warning(self, "No Base Story", "Please select a base story.")
            return

        # Disable controls during import
        self.import_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.status_text.clear()

        self._log(f"Starting import...")
        self._log(f"  File: {self.file_path.name}")
        self._log(f"  Result Set: {result_set_name}")
        self._log(f"  Base Story: {base_story}")

        # Start worker thread
        self.worker = PushoverCurveImportWorker(
            session=self.session,
            file_path=self.file_path,
            project_id=self.project_id,
            result_set_name=result_set_name,
            base_story=base_story,
            direction=None,  # Import both X and Y
            overwrite=True  # self.overwrite_check.isChecked()
        )
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_import_finished)
        self.worker.error.connect(self._on_import_error)
        self.worker.start()

    def _on_progress(self, message: str):
        """Handle progress updates."""
        self._log(message)

    def _on_import_finished(self, stats: dict):
        """Handle successful import completion."""
        self.progress_bar.setVisible(False)
        self.import_btn.setEnabled(True)
        self.cancel_btn.setEnabled(True)

        self._log("")
        self._log("✓ Import completed successfully!")
        self._log(f"  Result Set: {stats['result_set_name']} (ID: {stats['result_set_id']})")
        self._log(f"  Curves imported: {stats['curves_imported']}")
        self._log(f"  Total data points: {stats['total_points']}")

        # Show success message
        QMessageBox.information(
            self,
            "Import Successful",
            f"Successfully imported {stats['curves_imported']} pushover curves.\n\n"
            f"Result Set: {stats['result_set_name']}\n"
            f"Total Points: {stats['total_points']}"
        )

        # Emit signal for parent to refresh
        self.import_completed.emit(stats)

        # Close dialog
        self.accept()

    def _on_import_error(self, error_msg: str):
        """Handle import error."""
        self.progress_bar.setVisible(False)
        self.import_btn.setEnabled(True)
        self.cancel_btn.setEnabled(True)

        self._log("")
        self._log(f"✗ Import failed: {error_msg}", error=True)

        QMessageBox.critical(
            self,
            "Import Failed",
            f"Failed to import pushover curves:\n\n{error_msg}"
        )

    def _log(self, message: str, error: bool = False):
        """Add message to status log."""
        if error:
            self.status_text.append(f'<span style="color: #ef4444;">{message}</span>')
        else:
            self.status_text.append(message)
