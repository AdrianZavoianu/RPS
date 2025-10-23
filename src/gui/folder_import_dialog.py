"""Folder import dialog with progress tracking."""

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QTextEdit,
    QProgressBar,
    QFileDialog,
    QListWidget,
    QGroupBox,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from pathlib import Path

from .ui_helpers import create_styled_button, create_styled_label


class FolderImportWorker(QThread):
    """Worker thread for folder import to avoid blocking UI."""

    progress = pyqtSignal(str, int, int)  # message, current, total
    finished = pyqtSignal(dict)  # stats
    error = pyqtSignal(str)  # error message

    def __init__(self, folder_path: str, project_name: str, result_set_name: str):
        super().__init__()
        self.folder_path = folder_path
        self.project_name = project_name
        self.result_set_name = result_set_name

    def run(self):
        """Run the import in background thread."""
        try:
            from processing.folder_importer import FolderImporter

            importer = FolderImporter(
                folder_path=self.folder_path,
                project_name=self.project_name,
                result_set_name=self.result_set_name,
                result_types=["Story Drifts"],
                progress_callback=self._on_progress,
            )

            stats = importer.import_all()
            self.finished.emit(stats)

        except Exception as e:
            self.error.emit(str(e))

    def _on_progress(self, message: str, current: int, total: int):
        """Emit progress signal."""
        self.progress.emit(message, current, total)


class FolderImportDialog(QDialog):
    """Dialog for batch importing Excel files from a folder."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Import from Folder")
        self.setMinimumSize(700, 550)

        self.folder_path = None
        self.project_name = None
        self.worker = None

        self.setup_ui()

    def setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Title
        title = create_styled_label("Batch Import from Folder", "header")
        layout.addWidget(title)

        subtitle = create_styled_label(
            "Select a folder containing Excel files with structural analysis results",
            "muted",
        )
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        # Folder selection
        folder_group = QGroupBox("Folder Selection")
        folder_group.setStyleSheet("""
            QGroupBox {
                background-color: #161b22;
                border: 1px solid #2c313a;
                border-radius: 6px;
                margin-top: 8px;
                padding-top: 16px;
                color: #d1d5db;
                font-weight: 600;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 4px;
            }
        """)
        folder_layout = QVBoxLayout(folder_group)

        # Folder path input
        folder_input_layout = QHBoxLayout()
        self.folder_input = QLineEdit()
        self.folder_input.setPlaceholderText("Select folder containing Excel files...")
        self.folder_input.setReadOnly(True)
        self.folder_input.setStyleSheet("""
            QLineEdit {
                background-color: #0a0c10;
                border: 1px solid #2c313a;
                border-radius: 4px;
                padding: 8px 12px;
                color: #d1d5db;
            }
        """)
        folder_input_layout.addWidget(self.folder_input)

        browse_btn = create_styled_button("Browse...", "secondary", "sm")
        browse_btn.clicked.connect(self.browse_folder)
        folder_input_layout.addWidget(browse_btn)

        folder_layout.addLayout(folder_input_layout)

        # File list preview
        self.file_list = QListWidget()
        self.file_list.setMaximumHeight(120)
        self.file_list.setStyleSheet("""
            QListWidget {
                background-color: #0a0c10;
                border: 1px solid #2c313a;
                border-radius: 4px;
                padding: 4px;
                color: #7f8b9a;
            }
            QListWidget::item {
                padding: 4px 8px;
                border-radius: 2px;
            }
            QListWidget::item:hover {
                background-color: #161b22;
            }
        """)
        folder_layout.addWidget(QLabel("Files to process:"))
        folder_layout.addWidget(self.file_list)

        layout.addWidget(folder_group)

        # Project name
        project_group = QGroupBox("Project Information")
        project_group.setStyleSheet(folder_group.styleSheet())
        project_layout = QVBoxLayout(project_group)

        self.project_input = QLineEdit()
        self.project_input.setPlaceholderText("Enter project name...")
        self.project_input.setStyleSheet(self.folder_input.styleSheet())
        project_layout.addWidget(QLabel("Project Name:"))
        project_layout.addWidget(self.project_input)

        layout.addWidget(project_group)

        # Result Set name
        result_set_group = QGroupBox("Result Set Information")
        result_set_group.setStyleSheet(folder_group.styleSheet())
        result_set_layout = QVBoxLayout(result_set_group)

        self.result_set_input = QLineEdit()
        self.result_set_input.setPlaceholderText("Enter result set name (e.g., DES, MCE, SLE)...")
        self.result_set_input.setStyleSheet(self.folder_input.styleSheet())
        self.result_set_input.textChanged.connect(self.update_import_button)
        result_set_layout.addWidget(QLabel("Result Set Name:"))
        result_set_layout.addWidget(self.result_set_input)

        self.result_set_validation_label = QLabel("")
        self.result_set_validation_label.setStyleSheet("color: #ef4444; font-size: 12px;")
        self.result_set_validation_label.setWordWrap(True)
        result_set_layout.addWidget(self.result_set_validation_label)

        layout.addWidget(result_set_group)

        # Progress section
        progress_group = QGroupBox("Import Progress")
        progress_group.setStyleSheet(folder_group.styleSheet())
        progress_layout = QVBoxLayout(progress_group)

        self.progress_label = QLabel("Ready to import")
        self.progress_label.setStyleSheet("color: #7f8b9a;")
        progress_layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #0a0c10;
                border: 1px solid #2c313a;
                border-radius: 4px;
                height: 24px;
                text-align: center;
                color: #d1d5db;
            }
            QProgressBar::chunk {
                background-color: #4a7d89;
                border-radius: 3px;
            }
        """)
        progress_layout.addWidget(self.progress_bar)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMaximumHeight(100)
        self.log_output.setStyleSheet("""
            QTextEdit {
                background-color: #0a0c10;
                border: 1px solid #2c313a;
                border-radius: 4px;
                padding: 8px;
                color: #7f8b9a;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
            }
        """)
        progress_layout.addWidget(self.log_output)

        layout.addWidget(progress_group)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.import_btn = create_styled_button("Start Import", "primary")
        self.import_btn.clicked.connect(self.start_import)
        self.import_btn.setEnabled(False)
        button_layout.addWidget(self.import_btn)

        self.cancel_btn = create_styled_button("Cancel", "ghost")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        layout.addLayout(button_layout)

    def browse_folder(self):
        """Browse for folder."""
        folder = QFileDialog.getExistingDirectory(
            self, "Select Folder with Excel Files", str(Path.home())
        )

        if folder:
            self.folder_path = folder
            self.folder_input.setText(folder)

            # Auto-fill project name from folder name
            if not self.project_input.text():
                folder_name = Path(folder).name
                self.project_input.setText(folder_name)

            # Preview files
            self.preview_files()

            # Enable import button
            self.update_import_button()

    def preview_files(self):
        """Preview Excel files in selected folder."""
        if not self.folder_path:
            return

        self.file_list.clear()

        try:
            from processing.folder_importer import FolderImporter

            # Create temporary importer to get file list
            importer = FolderImporter(self.folder_path, "temp", "temp")
            files = importer.get_file_list()

            if files:
                self.file_list.addItems(files)
                self.log_output.append(f"✓ Found {len(files)} Excel file(s)")
            else:
                self.log_output.append("⚠ No Excel files found in folder")

        except Exception as e:
            self.log_output.append(f"✗ Error: {str(e)}")

    def update_import_button(self):
        """Update import button state."""
        has_folder = bool(self.folder_path)
        has_project = bool(self.project_input.text().strip())
        has_files = self.file_list.count() > 0

        # Validate result set name
        result_set_name = self.result_set_input.text().strip()
        has_result_set = bool(result_set_name)

        is_valid = True
        validation_message = ""

        if has_result_set and has_project:
            # Check for duplicates
            from database.base import get_session
            from database.repository import ProjectRepository, ResultSetRepository

            session = get_session()
            try:
                project_repo = ProjectRepository(session)
                project = project_repo.get_by_name(self.project_input.text().strip())

                if project:
                    result_set_repo = ResultSetRepository(session)
                    if result_set_repo.check_duplicate(project.id, result_set_name):
                        is_valid = False
                        validation_message = f"⚠ Result set '{result_set_name}' already exists for this project"
            finally:
                session.close()

        self.result_set_validation_label.setText(validation_message)
        self.import_btn.setEnabled(has_folder and has_project and has_result_set and has_files and is_valid)

    def start_import(self):
        """Start the import process."""
        self.project_name = self.project_input.text().strip()
        result_set_name = self.result_set_input.text().strip()

        if not self.project_name:
            self.log_output.append("✗ Please enter a project name")
            return

        if not result_set_name:
            self.log_output.append("✗ Please enter a result set name")
            return

        # Disable controls during import
        self.import_btn.setEnabled(False)
        self.browse_btn = self.findChild(QPushButton)
        self.project_input.setEnabled(False)
        self.result_set_input.setEnabled(False)

        self.log_output.append(f"\n▶ Starting batch import for project: {self.project_name}")
        self.log_output.append(f"▶ Result set: {result_set_name}")
        self.log_output.append(f"▶ Processing {self.file_list.count()} files...")

        # Create and start worker thread
        self.worker = FolderImportWorker(self.folder_path, self.project_name, result_set_name)
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.error.connect(self.on_error)
        self.worker.start()

    def on_progress(self, message: str, current: int, total: int):
        """Handle progress updates."""
        self.progress_label.setText(message)
        if total > 0:
            percentage = int((current / total) * 100)
            self.progress_bar.setValue(percentage)

        self.log_output.append(f"  {message} ({current}/{total})")

    def on_finished(self, stats: dict):
        """Handle import completion."""
        self.progress_bar.setValue(100)
        self.progress_label.setText("Import completed!")

        self.log_output.append("\n✓ Import completed successfully!")
        self.log_output.append(f"  Project: {stats['project']}")
        self.log_output.append(f"  Files processed: {stats['files_processed']}/{stats['files_total']}")
        self.log_output.append(f"  Load cases: {stats['load_cases']}")
        self.log_output.append(f"  Stories: {stats['stories']}")
        self.log_output.append(f"  Drift records: {stats['drifts']}")

        if stats['errors']:
            self.log_output.append(f"\n⚠ Errors: {len(stats['errors'])}")
            for error in stats['errors']:
                self.log_output.append(f"  • {error}")

        # Change button to close
        self.import_btn.setText("Close")
        self.import_btn.setEnabled(True)
        self.import_btn.clicked.disconnect()
        self.import_btn.clicked.connect(self.accept)

    def on_error(self, error_message: str):
        """Handle import error."""
        self.progress_label.setText("Import failed")
        self.log_output.append(f"\n✗ Import failed: {error_message}")

        # Re-enable controls
        self.import_btn.setEnabled(True)
        self.project_input.setEnabled(True)
        self.result_set_input.setEnabled(True)

    def get_project_name(self) -> str:
        """Get the project name.

        Returns:
            Project name
        """
        return self.project_name
