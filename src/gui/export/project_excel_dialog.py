"""Project export dialog for Excel workbook output."""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QGroupBox, QFileDialog,
    QMessageBox, QProgressBar, QCheckBox,
)
from PyQt6.QtCore import QStandardPaths
from pathlib import Path
from datetime import datetime

from gui.design_tokens import FormStyles
from gui.ui_helpers import create_styled_button
from gui.styles import COLORS

from .workers import ExportProjectExcelWorker


class ExportProjectExcelDialog(QDialog):
    """Dialog for exporting project to Excel workbook."""

    def __init__(self, context, result_service, project_name: str, parent=None):
        super().__init__(parent)
        self.context = context
        self.result_service = result_service
        self.project_name = project_name

        # Default output folder
        self.output_folder = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation))

        # Generate default filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"{self.project_name}_{timestamp}.xlsx"
        self.default_file_path = self.output_folder / default_filename

        self.setWindowTitle("Export Project to Excel")
        self.setMinimumWidth(750)  # Only set width, let height auto-adjust
        self.setStyleSheet(FormStyles.dialog())
        self._setup_ui()
        self._apply_styling()

    def _setup_ui(self):
        """Build dialog UI - copied from Export Results for consistency."""
        layout = QVBoxLayout(self)
        layout.setSpacing(8)  # Reduced from 12 to 8
        layout.setContentsMargins(16, 8, 16, 16)  # Reduced top margin from 16 to 8

        # Header
        header = QLabel("Export Project to Excel")
        header.setStyleSheet(f"color: {COLORS['text']}; font-size: 24px; font-weight: 600; margin: 0px; padding: 0px; line-height: 1.0;")
        layout.addWidget(header)

        # Info label
        info_label = QLabel(
            "Export complete project as Excel workbook (.xlsx) with human-readable sheets, "
            "metadata, and import data for re-importing into RPS."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet(f"color: {COLORS['muted']}; font-size: 13px; margin-bottom: 4px;")
        layout.addWidget(info_label)

        # Output location
        output_group = QGroupBox("Output Location")
        output_layout = QVBoxLayout()
        output_layout.setContentsMargins(8, 8, 8, 8)
        output_layout.setSpacing(8)

        # Folder selection
        folder_layout = QHBoxLayout()
        folder_layout.setSpacing(8)

        folder_label = QLabel("Folder:")
        folder_label.setStyleSheet(f"color: {COLORS['text']}; font-size: 14px;")
        folder_label.setFixedWidth(60)
        folder_layout.addWidget(folder_label)

        self.folder_edit = QLineEdit()
        self.folder_edit.setText(str(self.output_folder))
        self.folder_edit.setReadOnly(True)
        folder_layout.addWidget(self.folder_edit)

        browse_folder_btn = create_styled_button("Browse...", "secondary", "sm")
        browse_folder_btn.clicked.connect(self._browse_folder)
        folder_layout.addWidget(browse_folder_btn)

        output_layout.addLayout(folder_layout)

        # Filename input
        filename_layout = QHBoxLayout()
        filename_layout.setSpacing(8)

        filename_label = QLabel("Filename:")
        filename_label.setStyleSheet(f"color: {COLORS['text']}; font-size: 14px;")
        filename_label.setFixedWidth(60)
        filename_layout.addWidget(filename_label)

        self.filename_edit = QLineEdit()
        self.filename_edit.setText(self.default_file_path.name)
        self.filename_edit.setPlaceholderText("Enter filename...")
        filename_layout.addWidget(self.filename_edit)

        output_layout.addLayout(filename_layout)

        output_group.setLayout(output_layout)
        layout.addWidget(output_group)

        # Spacing before progress bar (12px)
        layout.addSpacing(12)

        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet(f"color: {COLORS['muted']}; font-size: 13px;")
        self.status_label.setVisible(False)
        layout.addWidget(self.status_label)

        # Spacing before buttons (12px)
        layout.addSpacing(12)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        export_btn = create_styled_button("Export to Excel", "primary", "md")
        export_btn.clicked.connect(self._start_export)
        button_layout.addWidget(export_btn)

        cancel_btn = create_styled_button("Cancel", "secondary", "md")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

    def _browse_folder(self):
        """Open folder browser to select output location."""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Output Folder",
            str(self.output_folder),
            QFileDialog.Option.ShowDirsOnly
        )

        if folder:
            self.output_folder = Path(folder)
            self.folder_edit.setText(str(self.output_folder))

    def _start_export(self):
        # Validate filename
        filename = self.filename_edit.text().strip()
        if not filename:
            QMessageBox.warning(self, "Export Error", "Please enter a filename.")
            return

        # Ensure .xlsx extension
        if not filename.endswith('.xlsx'):
            filename += '.xlsx'

        # Build full output path
        output_path = self.output_folder / filename

        from services.export.service import ProjectExportExcelOptions

        options = ProjectExportExcelOptions(
            output_path=output_path,
            include_all_results=True  # Always include all results
        )

        self.progress_bar.setVisible(True)
        self.status_label.setVisible(True)

        self.worker = ExportProjectExcelWorker(self.context, self.result_service, options)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()

    def _on_progress(self, message: str, current: int, total: int):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.status_label.setText(message)

    def _on_finished(self, success: bool, message: str, output_path: str):
        self.progress_bar.setVisible(False)
        self.status_label.setVisible(False)

        if success:
            QMessageBox.information(
                self, "Export Complete",
                f"{message}\n\nSaved to:\n{output_path}\n\nYou can now open this file in Excel."
            )
            self.accept()
        else:
            QMessageBox.critical(self, "Export Failed", message)

    def _apply_styling(self):
        """Apply GMP design system styling matching export results dialog."""
        # Apply group box styling
        for widget in self.findChildren(QGroupBox):
            widget.setStyleSheet(self._groupbox_style())

        # Apply progress bar styling
        self.progress_bar.setStyleSheet(FormStyles.progress_bar())
        for widget in self.findChildren(QCheckBox):
            widget.setStyleSheet(self._checkbox_style())

    @staticmethod
    def _groupbox_style() -> str:
        """GroupBox style matching export results dialog."""
        base = FormStyles.group_box()
        extras = """
            /* Remove background for Export Options group */
            QGroupBox#exportOptionsGroup {{
                background-color: transparent;
                border: none;
            }}
            QGroupBox#exportOptionsGroup QCheckBox {{
                background-color: transparent;
            }}
        """
        return base + extras


    @staticmethod
    def _checkbox_style() -> str:
        return FormStyles.checkbox(indent=False)

