"""Import project dialog for restoring projects from Excel files."""

from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QProgressBar, QTextEdit, QMessageBox, QLineEdit
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from gui.ui_helpers import create_styled_button, create_styled_label
from gui.styles import COLORS
from services.import_service import ImportService, ImportProjectExcelOptions


class ImportProjectWorker(QThread):
    """Background worker for importing project from Excel."""

    progress = pyqtSignal(str, int, int)  # message, current, total
    finished = pyqtSignal(bool, str, str)  # success, message, error_detail

    def __init__(self, options: ImportProjectExcelOptions):
        super().__init__()
        self.options = options
        self.import_service = ImportService()

    def run(self):
        """Execute import in background thread."""
        try:
            context = self.import_service.import_project_excel(
                options=self.options,
                progress_callback=self._on_progress
            )
            self.finished.emit(True, f"Project '{context.name}' imported successfully!", "")

        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            self.finished.emit(False, f"Import failed: {str(e)}", error_detail)

    def _on_progress(self, message: str, current: int, total: int):
        """Forward progress updates to UI."""
        self.progress.emit(message, current, total)


class ImportProjectDialog(QDialog):
    """Dialog for importing complete projects from Excel files."""

    def __init__(self, excel_path: Path, parent=None):
        super().__init__(parent)
        self.excel_path = excel_path
        self.import_service = ImportService()
        self.worker = None
        self.preview_data = None

        self.setWindowTitle("Import Project from Excel")
        self.setModal(True)
        self.resize(700, 600)

        self._setup_ui()
        self._apply_styles()
        self._preview_file()

    def _setup_ui(self):
        """Create dialog layout."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # Title
        title = create_styled_label("Import Project", "header")
        layout.addWidget(title)

        # File path display
        file_label = QLabel(f"<b>File:</b> {self.excel_path.name}")
        file_label.setWordWrap(True)
        file_label.setStyleSheet(f"color: {COLORS['muted']}; font-size: 13px;")
        layout.addWidget(file_label)

        # Project name input
        name_layout = QHBoxLayout()
        name_label = QLabel("Import as:")
        name_label.setFixedWidth(80)
        name_label.setStyleSheet(f"color: {COLORS['text']}; font-size: 14px;")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter new project name...")
        self.name_input.textChanged.connect(self._validate_project_name)
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_input)
        layout.addLayout(name_layout)

        # Validation message
        self.validation_label = QLabel("")
        self.validation_label.setStyleSheet(f"color: {COLORS['danger']}; font-size: 12px;")
        self.validation_label.setVisible(False)
        layout.addWidget(self.validation_label)

        # Preview section
        preview_label = create_styled_label("Project Preview", "subheader")
        layout.addWidget(preview_label)

        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setMaximumHeight(300)
        layout.addWidget(self.preview_text)

        # Progress section
        self.progress_label = QLabel("Ready to import")
        self.progress_label.setStyleSheet(f"color: {COLORS['muted']}; font-size: 13px;")
        layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.cancel_btn = create_styled_button("Cancel", "secondary", "md")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        self.import_btn = create_styled_button("Import Project", "primary", "md")
        self.import_btn.clicked.connect(self._start_import)
        button_layout.addWidget(self.import_btn)

        layout.addLayout(button_layout)

    def _apply_styles(self):
        """Apply GMP design system styles."""
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {COLORS['background']};
            }}

            QTextEdit {{
                background-color: {COLORS['card']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                padding: 12px;
                color: {COLORS['text']};
                font-size: 13px;
                font-family: 'Consolas', 'Monaco', monospace;
            }}

            QProgressBar {{
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                background-color: {COLORS['card']};
                height: 20px;
                text-align: center;
            }}

            QProgressBar::chunk {{
                background-color: {COLORS['accent']};
                border-radius: 3px;
            }}
        """)

    def _preview_file(self):
        """Preview Excel file and validate structure."""
        self.preview_text.setPlainText("Loading preview...")
        self.import_btn.setEnabled(False)

        try:
            preview = self.import_service.preview_import(self.excel_path)
            self.preview_data = preview

            # Build preview text
            preview_lines = []
            preview_lines.append(f"Project Name: {preview.project_name}")
            preview_lines.append(f"Description: {preview.description or '(none)'}")
            preview_lines.append(f"")
            preview_lines.append(f"Created: {preview.created_at}")
            preview_lines.append(f"Exported: {preview.exported_at}")
            preview_lines.append(f"")
            preview_lines.append(f"Contents:")
            preview_lines.append(f"  - Result Sets: {preview.result_sets_count}")
            preview_lines.append(f"  - Load Cases: {preview.load_cases_count}")
            preview_lines.append(f"  - Stories: {preview.stories_count}")
            preview_lines.append(f"  - Elements: {preview.elements_count}")
            preview_lines.append(f"")
            preview_lines.append(f"Result Types ({len(preview.result_types)}):")
            for rt in preview.result_types:
                preview_lines.append(f"  - {rt}")

            # Warnings
            if preview.warnings:
                preview_lines.append(f"")
                preview_lines.append(f"Warnings:")
                for warning in preview.warnings:
                    preview_lines.append(f"  - {warning}")

            # Validation status
            preview_lines.append(f"")
            if preview.can_import:
                preview_lines.append("Ready to import")
            else:
                preview_lines.append("Cannot import - validation failed")

            self.preview_text.setPlainText("\n".join(preview_lines))

            # Set default project name
            if preview.can_import:
                self.name_input.setText(preview.project_name)
                self._validate_project_name(preview.project_name)
            else:
                self.import_btn.setEnabled(False)

        except Exception as e:
            self.preview_text.setPlainText(f"Failed to preview file:\n\n{str(e)}")
            self.import_btn.setEnabled(False)

    def _validate_project_name(self, name: str = None):
        """Validate project name and check if it already exists."""
        if name is None:
            name = self.name_input.text()

        name = name.strip()

        if not name:
            self.validation_label.setText("Project name is required")
            self.validation_label.setVisible(True)
            self.import_btn.setEnabled(False)
            return

        # Check if project already exists
        from database.catalog_repository import CatalogProjectRepository
        from database.session import get_catalog_session

        catalog_session = get_catalog_session()
        try:
            catalog_repo = CatalogProjectRepository(catalog_session)
            existing_project = catalog_repo.get_by_name(name)

            if existing_project:
                self.validation_label.setText(f"Project '{name}' already exists. Please choose a different name.")
                self.validation_label.setVisible(True)
                self.import_btn.setEnabled(False)
            else:
                self.validation_label.setVisible(False)
                self.import_btn.setEnabled(True)
        finally:
            catalog_session.close()

    def _start_import(self):
        """Start import process after user confirmation."""
        if not self.preview_data or not self.preview_data.can_import:
            QMessageBox.warning(
                self, "Cannot Import",
                "File validation failed. Please check the preview for errors."
            )
            return

        # Get user-provided project name
        new_project_name = self.name_input.text().strip()

        if not new_project_name:
            QMessageBox.warning(
                self, "Invalid Name",
                "Please enter a project name."
            )
            return

        # Confirm with user
        reply = QMessageBox.question(
            self, "Confirm Import",
            f"Import project as '{new_project_name}'?\n\n"
            f"This will create a new project with all data from the Excel file.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # Disable controls
        self.name_input.setEnabled(False)
        self.import_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        # Create import options with user-provided name
        options = ImportProjectExcelOptions(
            excel_path=self.excel_path,
            new_project_name=new_project_name,
            overwrite_existing=False
        )

        # Start worker
        self.worker = ImportProjectWorker(options)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()

    def _on_progress(self, message: str, current: int, total: int):
        """Update progress display."""
        self.progress_label.setText(message)
        if total > 0:
            progress_percent = int((current / total) * 100)
            self.progress_bar.setValue(progress_percent)

    def _on_finished(self, success: bool, message: str, error_detail: str):
        """Handle import completion."""
        self.progress_bar.setVisible(False)
        self.cancel_btn.setEnabled(True)

        if success:
            QMessageBox.information(self, "Import Complete", message)
            self.accept()
        else:
            # Show error with details
            error_msg = QMessageBox(self)
            error_msg.setIcon(QMessageBox.Icon.Critical)
            error_msg.setWindowTitle("Import Failed")
            error_msg.setText(message)
            error_msg.setDetailedText(error_detail)
            error_msg.exec()

            # Re-enable import button
            self.import_btn.setEnabled(True)
