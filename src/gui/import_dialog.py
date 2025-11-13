"""Simple import dialog for single Excel file import."""

from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFileDialog, QComboBox,
    QDialogButtonBox
)
from PyQt6.QtCore import Qt

from gui.ui_helpers import create_styled_button, create_styled_label
from gui.styles import COLORS


class ImportDialog(QDialog):
    """Dialog for importing a single Excel data file into a project."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.file_path = None

        self.setWindowTitle("Import Data File")
        self.setModal(True)
        self.resize(500, 300)

        self._setup_ui()
        self._apply_styles()

    def _setup_ui(self):
        """Create dialog layout."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # Title
        title = create_styled_label("Import Excel Data", "header")
        layout.addWidget(title)

        # File selection
        file_layout = QHBoxLayout()
        file_label = QLabel("Excel File:")
        file_label.setFixedWidth(100)
        self.file_edit = QLineEdit()
        self.file_edit.setReadOnly(True)
        self.file_edit.setPlaceholderText("Select an Excel file...")
        browse_btn = create_styled_button("Browse...", "secondary", "sm")
        browse_btn.clicked.connect(self._browse_file)
        file_layout.addWidget(file_label)
        file_layout.addWidget(self.file_edit)
        file_layout.addWidget(browse_btn)
        layout.addLayout(file_layout)

        # Project name
        project_layout = QHBoxLayout()
        project_label = QLabel("Project Name:")
        project_label.setFixedWidth(100)
        self.project_edit = QLineEdit()
        self.project_edit.setPlaceholderText("Enter project name...")
        project_layout.addWidget(project_label)
        project_layout.addWidget(self.project_edit)
        layout.addLayout(project_layout)

        # Result set name
        result_set_layout = QHBoxLayout()
        result_set_label = QLabel("Result Set:")
        result_set_label.setFixedWidth(100)
        self.result_set_edit = QLineEdit()
        self.result_set_edit.setPlaceholderText("e.g., DES, MCE, SLE...")
        result_set_layout.addWidget(result_set_label)
        result_set_layout.addWidget(self.result_set_edit)
        layout.addLayout(result_set_layout)

        # Analysis type
        analysis_layout = QHBoxLayout()
        analysis_label = QLabel("Analysis Type:")
        analysis_label.setFixedWidth(100)
        self.analysis_combo = QComboBox()
        self.analysis_combo.addItems(["Response Spectrum", "Time History", "Static"])
        analysis_layout.addWidget(analysis_label)
        analysis_layout.addWidget(self.analysis_combo)
        layout.addLayout(analysis_layout)

        layout.addStretch()

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = create_styled_button("Cancel", "secondary", "md")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        import_btn = create_styled_button("Import", "primary", "md")
        import_btn.clicked.connect(self._on_import)
        button_layout.addWidget(import_btn)

        layout.addLayout(button_layout)

    def _apply_styles(self):
        """Apply GMP design system styles."""
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {COLORS['background']};
            }}

            QLabel {{
                color: {COLORS['text_primary']};
                font-size: 14px;
            }}

            QLineEdit {{
                background-color: {COLORS['card']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                padding: 8px;
                color: {COLORS['text_primary']};
                font-size: 14px;
            }}

            QLineEdit:focus {{
                border-color: {COLORS['accent']};
            }}

            QComboBox {{
                background-color: {COLORS['card']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                padding: 8px;
                color: {COLORS['text_primary']};
                font-size: 14px;
            }}

            QComboBox:focus {{
                border-color: {COLORS['accent']};
            }}

            QComboBox::drop-down {{
                border: none;
            }}

            QComboBox::down-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 6px solid {COLORS['text_secondary']};
                margin-right: 8px;
            }}
        """)

    def _browse_file(self):
        """Open file browser to select Excel file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Excel Data File",
            str(Path.home()),
            "Excel Files (*.xlsx *.xls)"
        )

        if file_path:
            self.file_path = file_path
            self.file_edit.setText(file_path)

    def _on_import(self):
        """Validate and accept dialog."""
        if not self.file_path:
            return

        if not self.project_edit.text().strip():
            return

        if not self.result_set_edit.text().strip():
            return

        self.accept()

    def get_selected_file(self) -> str:
        """Get the selected file path."""
        return self.file_path

    def get_project_name(self) -> str:
        """Get the project name."""
        return self.project_edit.text().strip()

    def get_result_set_name(self) -> str:
        """Get the result set name."""
        return self.result_set_edit.text().strip()

    def get_analysis_type(self) -> str:
        """Get the selected analysis type."""
        return self.analysis_combo.currentText()
