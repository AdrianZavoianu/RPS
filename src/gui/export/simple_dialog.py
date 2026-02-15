"""Simple export dialog for current view."""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QRadioButton, QGroupBox, QMessageBox,
    QProgressBar,
)
from PyQt6.QtCore import QStandardPaths
from pathlib import Path
from datetime import datetime

from services.export.service import ExportOptions
from gui.design_tokens import FormStyles
from gui.ui_helpers import create_styled_button
from gui.styles import COLORS

from .workers import ExportWorker


class SimpleExportDialog(QDialog):
    """Simple dialog for exporting current view (MVP).

    Exports the currently displayed result type to Excel or CSV.

    Args:
        context: ProjectContext instance
        result_service: ResultDataService instance
        current_result_set_id: ID of current result set
        current_result_type: Current result type name (e.g., "Drifts")
        current_direction: Current direction (e.g., "X", "Y")
        project_name: Project name for filename
        parent: Parent widget
    """

    def __init__(self, context, result_service, current_result_set_id,
                 current_result_type, current_direction, project_name, parent=None):
        super().__init__(parent)

        self.context = context
        self.result_service = result_service
        self.current_result_set_id = current_result_set_id
        self.current_result_type = current_result_type
        self.current_direction = current_direction
        self.project_name = project_name

        # Build full result type name (e.g., "Drifts_X")
        if current_direction:
            self.full_result_type = f"{current_result_type}_{current_direction}"
        else:
            self.full_result_type = current_result_type

        self.setWindowTitle("Export Results")
        self.setMinimumWidth(500)
        self.setMinimumHeight(300)
        self.setStyleSheet(FormStyles.dialog())

        self._setup_ui()
        self._apply_styling()

    def _setup_ui(self):
        """Build dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # Header info
        info_label = QLabel(f"Export: {self.full_result_type}")
        info_label.setStyleSheet(
            f"font-size: 16px; font-weight: 600; color: {COLORS['text']};"
        )
        layout.addWidget(info_label)

        # Format selection group
        format_group = QGroupBox("Export Format")
        format_layout = QHBoxLayout()

        self.excel_radio = QRadioButton("Excel (.xlsx)")
        self.excel_radio.setChecked(True)
        self.excel_radio.setToolTip("Export to Excel spreadsheet")
        format_layout.addWidget(self.excel_radio)

        self.csv_radio = QRadioButton("CSV (.csv)")
        self.csv_radio.setToolTip("Export to comma-separated values file")
        format_layout.addWidget(self.csv_radio)

        format_layout.addStretch()
        format_group.setLayout(format_layout)
        layout.addWidget(format_group)

        # Output file information group
        file_group = QGroupBox("Output Location")
        file_layout = QVBoxLayout()

        # Show where file will be saved
        downloads_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation)
        location_label = QLabel(f"Files will be saved to: {downloads_path}")
        location_label.setStyleSheet(f"color: {COLORS['muted']}; font-size: 12px;")
        location_label.setWordWrap(True)
        file_layout.addWidget(location_label)

        # Show auto-generated filename
        self.filename_preview = QLabel()
        self.filename_preview.setStyleSheet(f"color: {COLORS['text']}; font-size: 13px; font-weight: 600; margin-top: 8px;")
        self.filename_preview.setWordWrap(True)
        file_layout.addWidget(self.filename_preview)

        file_group.setLayout(file_layout)
        layout.addWidget(file_group)

        # Update filename preview when format changes
        self.excel_radio.toggled.connect(self._update_filename_preview)
        self._update_filename_preview()

        # Add stretch to push progress to bottom
        layout.addStretch()

        # Progress bar (initially hidden)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)

        # Status label (initially hidden)
        self.status_label = QLabel("")
        self.status_label.setStyleSheet(f"color: {COLORS['muted']}; font-size: 13px;")
        self.status_label.setVisible(False)
        layout.addWidget(self.status_label)

        # Button row
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        export_btn = create_styled_button("Export", "primary", "md")
        export_btn.clicked.connect(self._start_export)
        button_layout.addWidget(export_btn)

        cancel_btn = create_styled_button("Cancel", "secondary", "md")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

    def _update_filename_preview(self):
        """Update the filename preview label."""
        filename = self._build_auto_filename()
        self.filename_preview.setText(f"Filename: {filename}")

    def _build_auto_filename(self) -> str:
        """Build automatic filename with project name, result type, and timestamp.

        Format: {ProjectName}_{ResultType}_{YYYYMMDD_HHMMSS}.{ext}
        Example: 160Wil_Drifts_X_20241108_153045.xlsx
        """
        format_type = "excel" if self.excel_radio.isChecked() else "csv"
        ext = "xlsx" if format_type == "excel" else "csv"

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.project_name}_{self.full_result_type}_{timestamp}.{ext}"

        return filename

    def _get_output_path(self) -> Path:
        """Get full output path in Downloads folder."""
        downloads_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation)
        filename = self._build_auto_filename()
        return Path(downloads_path) / filename

    def _start_export(self):
        """Start export process in background thread."""
        # Get auto-generated output path
        output_path = self._get_output_path()

        # Build export options (use full_result_type with direction)
        options = ExportOptions(
            result_set_id=self.current_result_set_id,
            result_type=self.full_result_type,
            output_path=output_path,
            format="excel" if self.excel_radio.isChecked() else "csv",
        )

        # Show progress UI
        self.progress_bar.setVisible(True)
        self.status_label.setVisible(True)

        # Start background worker
        self.worker = ExportWorker(self.context, self.result_service, options)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()

    def _on_progress(self, message: str, current: int, total: int):
        """Handle progress update from worker thread."""
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.status_label.setText(message)

    def _on_finished(self, success: bool, message: str):
        """Handle export completion from worker thread."""
        self.progress_bar.setVisible(False)
        self.status_label.setVisible(False)

        if success:
            # Show success message with file location
            output_path = self._get_output_path()
            QMessageBox.information(
                self,
                "Export Complete",
                f"{message}\n\nSaved to:\n{output_path}"
            )
            self.accept()
        else:
            QMessageBox.critical(
                self,
                "Export Failed",
                message
            )

    def _apply_styling(self):
        """Apply GMP design system styling."""
        self.setStyleSheet(f"""
            QGroupBox {{
                font-size: 14px;
                font-weight: 600;
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                margin-top: 12px;
                padding: 16px;
                background-color: rgba(255, 255, 255, 0.02);
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px;
            }}
            QLineEdit[empty="true"] {{
                border: 1px solid #ff8c00;  /* Orange for empty */
            }}
            QLineEdit:focus {{
                border: 1px solid {COLORS['accent']};  /* Teal for focus */
            }}
            QCheckBox {{
                color: {COLORS['text']};
                spacing: 8px;
            }}
            QRadioButton {{
                color: {COLORS['text']};
                spacing: 8px;
            }}
        """)
        self.progress_bar.setStyleSheet(FormStyles.progress_bar())


