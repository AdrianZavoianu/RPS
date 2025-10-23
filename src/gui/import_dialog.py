"""Dialog for importing Excel files."""

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFileDialog,
    QDialogButtonBox,
    QGroupBox,
    QFormLayout,
)
from PyQt6.QtCore import Qt
from pathlib import Path
from .ui_helpers import create_styled_button, create_styled_label, apply_button_style


class ImportDialog(QDialog):
    """Dialog for selecting and importing Excel files."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Import Excel Results")
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)

        self.selected_file = None
        self.project_name = None
        self.result_set_name = None

        self._create_ui()

        # Apply modern styling
        self.setStyleSheet("""
            QDialog {
                background-color: #161b22;
            }
        """)

    def _create_ui(self):
        """Create modern dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(24, 24, 24, 24)

        # Header with GMP styling
        header_label = create_styled_label("Import Results", "header")
        layout.addWidget(header_label)

        subtitle_label = create_styled_label("Import structural analysis results from Excel files", "muted")
        layout.addWidget(subtitle_label)

        # File selection group with modern styling
        file_group = QGroupBox("Excel File")
        file_group.setStyleSheet("margin-top: 8px;")
        file_layout = QVBoxLayout()
        file_layout.setSpacing(8)

        self.file_path_edit = QLineEdit()
        self.file_path_edit.setReadOnly(True)
        self.file_path_edit.setPlaceholderText("No file selected...")
        self.file_path_edit.setMinimumHeight(40)

        browse_button = create_styled_button("📁 Browse Files...", "secondary")
        browse_button.setMinimumHeight(40)
        browse_button.clicked.connect(self._on_browse)

        file_layout.addWidget(self.file_path_edit)
        file_layout.addWidget(browse_button)
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)

        # Project info group
        project_group = QGroupBox("Project Information")
        project_group.setStyleSheet("margin-top: 8px;")
        project_layout = QVBoxLayout()
        project_layout.setSpacing(12)

        # Project name
        name_label = create_styled_label("Project Name", "small")
        self.project_name_edit = QLineEdit()
        self.project_name_edit.setPlaceholderText("e.g., 160Wil")
        self.project_name_edit.setMinimumHeight(40)

        # Result set name
        result_set_label = create_styled_label("Result Set Name", "small")
        self.result_set_edit = QLineEdit()
        self.result_set_edit.setPlaceholderText("e.g., DES, MCE, SLE")
        self.result_set_edit.setMinimumHeight(40)

        self.result_set_validation_label = QLabel("")
        self.result_set_validation_label.setStyleSheet("color: #ef4444; font-size: 12px;")
        self.result_set_validation_label.setWordWrap(True)

        # Analysis type
        analysis_label = create_styled_label("Analysis Type (Optional)", "small")
        self.subfolder_edit = QLineEdit()
        self.subfolder_edit.setPlaceholderText("e.g., DERG, MCR")
        self.subfolder_edit.setMinimumHeight(40)

        project_layout.addWidget(name_label)
        project_layout.addWidget(self.project_name_edit)
        project_layout.addWidget(result_set_label)
        project_layout.addWidget(self.result_set_edit)
        project_layout.addWidget(self.result_set_validation_label)
        project_layout.addWidget(analysis_label)
        project_layout.addWidget(self.subfolder_edit)

        project_group.setLayout(project_layout)
        layout.addWidget(project_group)

        # Info label
        info_label = QLabel(
            "💡 The importer will process Story Drifts, Accelerations, and Forces from the Excel file."
        )
        info_label.setWordWrap(True)
        info_label.setProperty("styleClass", "muted")
        info_label.setStyleSheet("font-size: 12px; padding: 12px; background-color: #1c2128; border-radius: 6px;")
        layout.addWidget(info_label)

        layout.addStretch()

        # Dialog buttons with GMP styling
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)

        cancel_button = create_styled_button("Cancel", "secondary")
        cancel_button.setMinimumHeight(40)
        cancel_button.setMinimumWidth(100)
        cancel_button.clicked.connect(self.reject)

        self.ok_button = create_styled_button("Import", "primary")
        self.ok_button.setMinimumHeight(40)
        self.ok_button.setMinimumWidth(100)
        self.ok_button.setEnabled(False)  # Disabled until file selected
        self.ok_button.clicked.connect(self._on_accept)

        button_layout.addStretch()
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(self.ok_button)

        layout.addLayout(button_layout)

        # Connect signals
        self.file_path_edit.textChanged.connect(self._validate_inputs)
        self.project_name_edit.textChanged.connect(self._validate_inputs)
        self.result_set_edit.textChanged.connect(self._validate_inputs)

    def _on_browse(self):
        """Open file browser to select Excel file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Excel File",
            str(Path.home()),
            "Excel Files (*.xlsx *.xls);;All Files (*)",
        )

        if file_path:
            self.file_path_edit.setText(file_path)

            # Auto-fill project name from file if empty
            if not self.project_name_edit.text():
                file_name = Path(file_path).stem
                # Try to extract project name (e.g., "160Wil_DES_Global" -> "160Wil")
                parts = file_name.split("_")
                if parts:
                    self.project_name_edit.setText(parts[0])

    def _validate_inputs(self):
        """Validate that required inputs are filled."""
        has_file = bool(self.file_path_edit.text())
        has_project = bool(self.project_name_edit.text().strip())

        # Validate result set name
        result_set_name = self.result_set_edit.text().strip()
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
                project = project_repo.get_by_name(self.project_name_edit.text().strip())

                if project:
                    result_set_repo = ResultSetRepository(session)
                    if result_set_repo.check_duplicate(project.id, result_set_name):
                        is_valid = False
                        validation_message = f"⚠ Result set '{result_set_name}' already exists for this project"
            finally:
                session.close()

        self.result_set_validation_label.setText(validation_message)
        self.ok_button.setEnabled(has_file and has_project and has_result_set and is_valid)

    def _on_accept(self):
        """Handle OK button click."""
        self.selected_file = self.file_path_edit.text()
        self.project_name = self.project_name_edit.text().strip()
        self.result_set_name = self.result_set_edit.text().strip()
        self.accept()

    def get_selected_file(self):
        """Get the selected file path."""
        return self.selected_file

    def get_project_name(self):
        """Get the project name."""
        return self.project_name

    def get_result_set_name(self):
        """Get the result set name."""
        return self.result_set_name

    def get_analysis_type(self):
        """Get the analysis type/subfolder."""
        return self.subfolder_edit.text().strip()
