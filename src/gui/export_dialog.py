"""
Export dialogs for RPS.

Provides UI for exporting result data to Excel and CSV formats.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QRadioButton, QGroupBox, QCheckBox,
    QFileDialog, QMessageBox, QProgressBar,
    QApplication
)
from PyQt6.QtCore import QThread, pyqtSignal, QStandardPaths, Qt
from pathlib import Path
from datetime import datetime
from typing import Dict, List

from gui.components.export_selectors import ResultSetSelector, ResultTypeSelector
from services.export_discovery import ExportDiscoveryService
from services.export_service import ExportService, ExportOptions
from gui.design_tokens import FormStyles, PALETTE
from gui.ui_helpers import create_styled_button
from gui.styles import COLORS
from database.models import ElementResultsCache, JointResultsCache


class ComprehensiveExportDialog(QDialog):
    """Comprehensive export dialog for exporting multiple result types.

    Exports all results by default with ability to filter specific types.
    Works independently of current browser selection.

    Args:
        context: ProjectContext instance
        result_service: ResultDataService instance
        current_result_set_id: ID of current result set
        project_name: Project name for filename
        analysis_context: 'NLTHA' or 'Pushover' - filters what result types to show
        parent: Parent widget
    """

    def __init__(self, context, result_service, current_result_set_id,
                 project_name, analysis_context='NLTHA', parent=None):
        super().__init__(parent)

        self.context = context
        self.result_service = result_service
        self.current_result_set_id = current_result_set_id
        self.project_name = project_name
        self.analysis_context = analysis_context  # 'NLTHA' or 'Pushover'
        self.discovery_service = ExportDiscoveryService(self.context.session)

        # Discovered result types (populated on init)
        self.available_types: Dict[str, List[str]] = {
            'global': [],  # ['Drifts_X', 'Drifts_Y', 'Accelerations_X', ...]
            'element': [],  # ['WallShears_V2', 'QuadRotations', ...]
            'joint': []  # ['SoilPressures', 'VerticalDisplacements']
        }

        # Available result sets (populated on init)
        self.available_result_sets = []  # List of (id, name) tuples

        # Set window title based on context
        title = f"Export {self.analysis_context} Results" if self.analysis_context else "Export Results"
        self.setWindowTitle(title)
        self.setMinimumSize(750, 400)
        self.setStyleSheet(FormStyles.dialog())

        # Default output folder
        self.output_folder = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation))

        # Discover available result sets and types from cache
        self._discover_result_sets()
        self._discover_result_types()

        # Check if we have any result sets for this context
        if not self.available_result_sets:
            from PyQt6.QtWidgets import QMessageBox
            context_name = self.analysis_context if self.analysis_context else "analysis"
            QMessageBox.warning(
                parent,
                f"No {context_name} Data",
                f"No {context_name} result sets found in this project.\n\n"
                f"Please import {context_name} data first."
            )
            # Set a flag to close immediately
            self._no_data = True
        else:
            self._no_data = False

        self._setup_ui()
        self._apply_styling()

        # Auto-fit window height to content after UI is built
        self._auto_fit_height()

    def exec(self):
        """Override exec to reject immediately if no data."""
        if self._no_data:
            return QDialog.DialogCode.Rejected
        return super().exec()

    def _discover_result_sets(self):
        """Query database to find result sets matching the analysis context.

        - NLTHA context: Only shows result sets where analysis_type != 'Pushover'
        - Pushover context: Only shows result sets where analysis_type == 'Pushover'
        """
        discovered_sets = self.discovery_service.discover_result_sets(
            project_name=self.context.name,
            analysis_context=self.analysis_context
        )
        self.available_result_sets = [(rs.id, rs.name) for rs in discovered_sets]

    def _discover_result_types(self):
        """Query cache to find all result types with data across ALL result sets of this analysis type.

        Note: Cache stores base types (e.g., "Drifts"). We'll show only base types
        in the UI, and export will automatically include all directions for each type.

        Filters result types based on analysis_context:
        - NLTHA: Shows only cache-based results (Drifts, Forces, etc.) from NLTHA result sets
        - Pushover: Shows Curves + pushover global/element/joint results from Pushover result sets
        """
        result_set_ids = [rs_id for rs_id, _ in self.available_result_sets]
        types = self.discovery_service.discover_result_types(
            result_set_ids=result_set_ids,
            analysis_context=self.analysis_context
        )

        self.available_types['global'] = types.global_types
        self.available_types['element'] = types.element_types
        self.available_types['joint'] = types.joint_types

    def _setup_ui(self):
        """Build dialog UI with vertical layout."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # Header
        header_text = f"Export {self.analysis_context} Results" if self.analysis_context else "Export Results"
        header = QLabel(header_text)
        header.setStyleSheet(f"color: {COLORS['text']}; font-size: 24px; font-weight: 600; margin: 0px; padding: 0px; line-height: 1.0;")
        layout.addWidget(header)

        # Info label
        total_types = len(self.available_types['global']) + len(self.available_types['element']) + len(self.available_types['joint'])
        total_sets = len(self.available_result_sets)

        context_name = self.analysis_context if self.analysis_context else "analysis"
        info_label = QLabel(
            f"Found {total_sets} {context_name} result set(s) with {total_types} result type(s). "
            f"All selected by default - uncheck to exclude."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet(f"color: {COLORS['muted']}; font-size: 13px; margin-bottom: 8px;")
        layout.addWidget(info_label)

        # Two-column layout: Result Types (left, full height) | Right column (stacked sections)
        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(12)

        # LEFT COLUMN: Result Types (full height)
        left_column = QVBoxLayout()
        left_column.setSpacing(0)

        result_types_group = QGroupBox("Result Types to Export")
        result_types_layout = QVBoxLayout()
        result_types_layout.setContentsMargins(8, 8, 8, 8)
        result_types_layout.setSpacing(6)

        rt_actions = QHBoxLayout()
        rt_all_btn = create_styled_button("All", "ghost", "sm")
        rt_all_btn.clicked.connect(lambda: self._set_result_types_checked(True))
        rt_none_btn = create_styled_button("None", "ghost", "sm")
        rt_none_btn.clicked.connect(lambda: self._set_result_types_checked(False))
        rt_actions.addWidget(rt_all_btn)
        rt_actions.addWidget(rt_none_btn)
        rt_actions.addStretch()
        result_types_layout.addLayout(rt_actions)

        self.type_selector = ResultTypeSelector(self.available_types)
        result_types_layout.addWidget(self.type_selector)

        result_types_group.setLayout(result_types_layout)
        left_column.addWidget(result_types_group)

        columns_layout.addLayout(left_column, 40)  # 40% width for result types

        # RIGHT COLUMN: Result Sets + Export Options + Output (stacked vertically)
        right_column = QVBoxLayout()
        right_column.setSpacing(12)

        # Result Sets selector (compact)
        result_sets_group = QGroupBox("Result Sets to Export")
        result_sets_layout = QVBoxLayout()
        result_sets_layout.setContentsMargins(8, 8, 8, 8)
        result_sets_layout.setSpacing(4)

        # Quick actions for result sets
        rs_actions = QHBoxLayout()
        rs_all_btn = create_styled_button("All", "ghost", "sm")
        rs_all_btn.clicked.connect(lambda: self._set_result_sets_checked(True))
        rs_none_btn = create_styled_button("None", "ghost", "sm")
        rs_none_btn.clicked.connect(lambda: self._set_result_sets_checked(False))
        rs_actions.addWidget(rs_all_btn)
        rs_actions.addWidget(rs_none_btn)
        rs_actions.addStretch()
        result_sets_layout.addLayout(rs_actions)

        self.result_set_selector = ResultSetSelector(self.available_result_sets)
        result_sets_layout.addWidget(self.result_set_selector)

        result_sets_group.setLayout(result_sets_layout)
        right_column.addWidget(result_sets_group)

        # Export format options
        format_group = QGroupBox("Export Options")
        format_group.setObjectName("exportOptionsGroup")
        format_layout = QVBoxLayout()
        format_layout.setContentsMargins(8, 8, 8, 8)
        format_layout.setSpacing(8)

        # Excel format
        excel_row = QHBoxLayout()
        self.excel_radio = QRadioButton("Excel (.xlsx)")
        self.excel_radio.setChecked(True)
        self.excel_radio.toggled.connect(self._on_format_changed)
        excel_row.addWidget(self.excel_radio)
        excel_row.addStretch()
        format_layout.addLayout(excel_row)

        # CSV format
        csv_row = QHBoxLayout()
        self.csv_radio = QRadioButton("CSV (.csv)")
        csv_row.addWidget(self.csv_radio)
        csv_row.addStretch()
        format_layout.addLayout(csv_row)

        # Combine mode (Excel only)
        self.combine_check = QCheckBox("Combine all results into single Excel file")
        self.combine_check.setChecked(True)
        self.combine_check.setToolTip("Create one .xlsx workbook with multiple sheets (Excel only)")
        format_layout.addWidget(self.combine_check)

        format_group.setLayout(format_layout)
        right_column.addWidget(format_group)

        # Output location
        output_group = QGroupBox("Output Location")
        output_layout = QVBoxLayout()
        output_layout.setContentsMargins(8, 8, 8, 8)
        output_layout.setSpacing(8)

        # Folder selection
        folder_layout = QHBoxLayout()
        folder_layout.setSpacing(8)

        self.folder_edit = QLineEdit()
        self.folder_edit.setText(str(self.output_folder))
        self.folder_edit.setReadOnly(True)
        folder_layout.addWidget(self.folder_edit)

        browse_btn = create_styled_button("Browse...", "secondary", "sm")
        browse_btn.clicked.connect(self._browse_folder)
        folder_layout.addWidget(browse_btn)

        output_layout.addLayout(folder_layout)

        # Filename preview
        self.filename_preview = QLabel()
        self.filename_preview.setStyleSheet(
            f"color: {COLORS['text']}; font-size: 13px; font-weight: 600; margin-top: 8px;"
        )
        self.filename_preview.setWordWrap(True)
        output_layout.addWidget(self.filename_preview)

        output_group.setLayout(output_layout)
        right_column.addWidget(output_group)

        right_column.addStretch()  # Push content to top

        columns_layout.addLayout(right_column, 60)  # 60% width for options

        layout.addLayout(columns_layout)

        # Update filename preview when options change
        self.excel_radio.toggled.connect(self._update_filename_preview)
        self.combine_check.toggled.connect(self._update_filename_preview)
        self._update_filename_preview()

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet(f"color: {COLORS['muted']}; font-size: 13px;")
        self.status_label.setVisible(False)
        layout.addWidget(self.status_label)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        export_btn = create_styled_button("Export", "primary", "md")
        export_btn.clicked.connect(self._start_export)
        button_layout.addWidget(export_btn)

        cancel_btn = create_styled_button("Cancel", "secondary", "md")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

    def _set_result_types_checked(self, checked: bool):
        self.type_selector.set_all(checked)

    def _set_result_sets_checked(self, checked: bool):
        self.result_set_selector.set_all(checked)

    def _get_selected_result_set_ids(self) -> List[int]:
        return self.result_set_selector.selected_ids()

    def _get_selected_result_types(self) -> List[str]:
        """Get list of checked result types from checkbox groups.

        Expands base types (e.g., "Drifts") to include all directions
        (e.g., "Drifts_X", "Drifts_Y") for export service.

        Special handling for "Curves" which doesn't need expansion.
        """
        from config.result_config import RESULT_CONFIGS

        selected_base_types = self.type_selector.selected_base_types()

        # Expand base types to include all directions
        expanded_types = []
        for base_type in selected_base_types:
            # Special case: "Curves" doesn't need expansion
            if base_type == "Curves":
                expanded_types.append(base_type)
                continue

            # Check if this is a global result type that needs direction expansion
            if base_type in self.available_types['global']:
                # Find all directional variants in RESULT_CONFIGS
                found_variant = False
                for config_key in RESULT_CONFIGS.keys():
                    # Match base_type_X, base_type_Y patterns
                    if config_key.startswith(f"{base_type}_"):
                        expanded_types.append(config_key)
                        found_variant = True

                # If no directional variants found, use base type as-is
                if not found_variant:
                    expanded_types.append(base_type)
            elif base_type in self.available_types['element']:
                # Element type - need to expand with directions if applicable
                # Check cache for actual full type names across all result sets of this context
                with self.context.session() as session:
                    result_set_ids = [rs_id for rs_id, _ in self.available_result_sets]
                    element_full_types = session.query(
                        ElementResultsCache.result_type
                    ).filter(
                        ElementResultsCache.result_set_id.in_(result_set_ids)
                    ).distinct().all()

                    # Find all variants of this base type
                    for full_type, in element_full_types:
                        if full_type.startswith(base_type):
                            expanded_types.append(full_type)
            elif base_type in self.available_types['joint']:
                # Joint type - need to expand with suffix (_Min, _Ux, _Uy, _Uz)
                # Check cache for actual full type names across all result sets of this context
                with self.context.session() as session:
                    result_set_ids = [rs_id for rs_id, _ in self.available_result_sets]
                    joint_full_types = session.query(
                        JointResultsCache.result_type
                    ).filter(
                        JointResultsCache.result_set_id.in_(result_set_ids)
                    ).distinct().all()

                    # Find all variants of this base type
                    for full_type, in joint_full_types:
                        if full_type.startswith(base_type):
                            expanded_types.append(full_type)

        return expanded_types

    def _on_format_changed(self):
        """Handle format radio button change."""
        is_excel = self.excel_radio.isChecked()
        self.combine_check.setEnabled(is_excel)
        if not is_excel:
            self.combine_check.setChecked(False)

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
            self._update_filename_preview()

    def _update_filename_preview(self):
        """Update filename preview based on current options."""
        is_combined = self.combine_check.isChecked() and self.excel_radio.isChecked()

        if is_combined:
            # Single file
            filename = self._build_combined_filename()
            self.filename_preview.setText(f"File: {filename}")
        else:
            # Multiple files
            selected_count = len(self._get_selected_result_types())
            format_ext = "xlsx" if self.excel_radio.isChecked() else "csv"

            self.filename_preview.setText(
                f"{selected_count} files: {self.project_name}_{self.analysis_context}_<ResultType>_<timestamp>.{format_ext}"
            )

    def _build_combined_filename(self) -> str:
        """Build filename for combined export."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{self.project_name}_{self.analysis_context}_AllResults_{timestamp}.xlsx"

    def _start_export(self):
        """Start comprehensive export process."""
        selected_types = self._get_selected_result_types()

        if not selected_types:
            QMessageBox.warning(
                self,
                "No Results Selected",
                "Please select at least one result type to export."
            )
            return

        # Get selected result sets
        selected_result_set_ids = self._get_selected_result_set_ids()

        if not selected_result_set_ids:
            QMessageBox.warning(
                self,
                "No Result Sets Selected",
                "Please select at least one result set to export."
            )
            return

        # Show progress
        self.progress_bar.setVisible(True)
        self.status_label.setVisible(True)

        # Determine export mode
        is_combined = self.combine_check.isChecked() and self.excel_radio.isChecked()
        format_type = "excel" if self.excel_radio.isChecked() else "csv"

        # Build output paths using selected folder
        if is_combined:
            output_file = self.output_folder / self._build_combined_filename()
            output_folder = None
        else:
            output_folder = self.output_folder / f"{self.project_name}_{self.analysis_context}_Export_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            output_file = None

        # Start worker with multiple result sets
        self.worker = ComprehensiveExportWorker(
            context=self.context,
            result_service=self.result_service,
            result_set_ids=selected_result_set_ids,
            result_types=selected_types,
            format_type=format_type,
            is_combined=is_combined,
            output_file=output_file,
            output_folder=output_folder,
            analysis_context=self.analysis_context
        )

        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()

    def _on_progress(self, message: str, current: int, total: int):
        """Handle progress update."""
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.status_label.setText(message)

    def _on_finished(self, success: bool, message: str, output_path: str):
        """Handle export completion."""
        self.progress_bar.setVisible(False)
        self.status_label.setVisible(False)

        if success:
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
        """Apply GMP design system styling matching folder import dialog."""
        # Apply group box styling
        for widget in self.findChildren(QGroupBox):
            widget.setStyleSheet(self._groupbox_style())

        # Apply line edit styling
        for widget in self.findChildren(QLineEdit):
            widget.setStyleSheet(self._lineedit_style())

        # Apply checkbox styling for standalone options
        checkbox_style = self._checkbox_style()
        for widget in self.findChildren(QCheckBox):
            widget.setStyleSheet(checkbox_style)

        # Apply progress bar styling
        self.progress_bar.setStyleSheet(self._progress_style())

    @staticmethod
    def _groupbox_style() -> str:
        """GroupBox style matching folder import dialog."""
        base = FormStyles.group_box()
        extras = f"""
            /* Remove black background for Export Options group */
            QGroupBox#exportOptionsGroup {{
                background-color: transparent;
                border: none;
            }}
            QGroupBox#exportOptionsGroup QRadioButton,
            QGroupBox#exportOptionsGroup QCheckBox {{
                background-color: transparent;
            }}
        """
        return base + extras

    @staticmethod
    def _lineedit_style() -> str:
        """LineEdit style matching folder import dialog."""
        c = PALETTE
        return f"""
            QLineEdit {{
                background-color: {c['bg_tertiary']};
                border: 1px solid {c['border_default']};
                border-radius: 6px;
                padding: 8px 12px;
                color: {c['text_primary']};
            }}
            QLineEdit:focus {{
                border-color: {c['accent_primary']};
            }}
        """

    @staticmethod
    def _checkbox_style() -> str:
        return FormStyles.checkbox(indent=False)

    @staticmethod
    def _progress_style() -> str:
        """ProgressBar style matching folder import dialog."""
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

    def _auto_fit_height(self):
        """Set a reasonable default height for the scroll layouts."""
        screen = QApplication.primaryScreen()
        default_height = 720
        if screen:
            max_height = int(screen.availableGeometry().height() * 0.85)
            default_height = min(default_height, max_height)
        self.resize(self.width(), default_height)


class ComprehensiveExportWorker(QThread):
    """Background worker for comprehensive export operations."""

    progress = pyqtSignal(str, int, int)
    finished = pyqtSignal(bool, str, str)  # success, message, output_path

    def __init__(self, context, result_service, result_set_ids, result_types,
                 format_type, is_combined, output_file, output_folder, analysis_context='NLTHA'):
        super().__init__()
        self.context = context
        self.result_service = result_service
        self.result_set_ids = result_set_ids
        self.result_types = result_types
        self.format_type = format_type
        self.is_combined = is_combined
        self.output_file = output_file
        self.output_folder = output_folder
        self.analysis_context = analysis_context

    def run(self):
        """Execute comprehensive export."""
        try:
            if self.is_combined:
                self._export_combined()
            else:
                self._export_per_file()
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.finished.emit(False, f"Export failed: {str(e)}", "")

    def _export_combined(self):
        """Export all result types from all result sets to single Excel file."""
        import pandas as pd
        from database.repository import ResultSetRepository

        # Calculate total operations
        total_operations = len(self.result_types) * len(self.result_set_ids)
        current_operation = 0

        self.progress.emit("Preparing combined export...", 0, total_operations)

        export_service = ExportService(self.context, self.result_service)
        exported_count = 0
        skipped = []

        # Get result set names
        with self.context.session() as session:
            result_set_repo = ResultSetRepository(session)
            result_set_names = {}
            for rs_id in self.result_set_ids:
                rs = result_set_repo.get_by_id(rs_id)
                if rs:
                    result_set_names[rs_id] = rs.name

        # Generate single timestamp for this export
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        with pd.ExcelWriter(self.output_file, engine='openpyxl') as writer:
            for result_set_id in self.result_set_ids:
                result_set_name = result_set_names.get(result_set_id, f"RS{result_set_id}")

                for result_type in self.result_types:
                    current_operation += 1
                    self.progress.emit(
                        f"Exporting {result_set_name} - {result_type}...",
                        current_operation,
                        total_operations
                    )

                    try:
                        # Special handling for pushover curves
                        if result_type == "Curves":
                            # Export pushover curves to separate sheets (one per case)
                            from database.repository import PushoverCaseRepository

                            with self.context.session() as session:
                                pushover_repo = PushoverCaseRepository(session)
                                cases = pushover_repo.get_by_result_set(result_set_id)

                                for case in cases:
                                    curve_points = pushover_repo.get_curve_data(case.id)

                                    if not curve_points:
                                        continue

                                    # Build DataFrame for this curve
                                    data = {
                                        'Step Number': [pt.step_number for pt in curve_points],
                                        'Base Shear (kN)': [pt.base_shear for pt in curve_points],
                                        'Displacement (mm)': [pt.displacement for pt in curve_points]
                                    }
                                    df = pd.DataFrame(data)

                                    # Sheet name: ResultSetName_CaseName (truncate to 31 chars)
                                    sheet_name = f"{result_set_name}_{case.name}"[:31]
                                    df.to_excel(writer, sheet_name=sheet_name, index=False)
                                    exported_count += 1

                            continue  # Move to next result type

                        # Determine if this is a global, element, or joint result
                        is_element = any(x in result_type for x in ['Wall', 'Quad', 'Column', 'Beam'])
                        is_joint = any(x in result_type for x in ['SoilPressures', 'VerticalDisplacements', 'JointDisplacements'])

                        if is_element:
                            # Get combined element data
                            df = export_service.get_element_export_dataframe(
                                result_type=result_type,
                                result_set_id=result_set_id
                            )

                            if df is None or df.empty:
                                skipped.append(f"{result_set_name}_{result_type}")
                                continue

                            # Write to sheet with result set name prefix
                            sheet_name = f"{result_set_name}_{result_type}"[:31]
                            df.to_excel(writer, sheet_name=sheet_name, index=False)
                            exported_count += 1

                        elif is_joint:
                            # Get joint result data
                            # result_type already includes _Min suffix from _get_selected_result_types()
                            dataset = self.result_service.get_joint_dataset(
                                result_type=result_type,
                                result_set_id=result_set_id
                            )

                            if dataset is None or dataset.data is None or dataset.data.empty:
                                skipped.append(f"{result_set_name}_{result_type}")
                                continue

                            # Write to sheet (remove _Min from sheet name for cleaner display)
                            display_type = result_type.replace('_Min', '')
                            sheet_name = f"{result_set_name}_{display_type}"[:31]
                            dataset.data.to_excel(writer, sheet_name=sheet_name, index=False)
                            exported_count += 1

                        else:
                            # Get global result data
                            config = export_service._get_result_config(result_type)
                            direction = export_service._extract_direction(result_type, config)
                            base_type = export_service._extract_base_type(result_type)

                            dataset = self.result_service.get_standard_dataset(
                                result_type=base_type,
                                direction=direction,
                                result_set_id=result_set_id
                            )

                            if dataset is None or dataset.data is None or dataset.data.empty:
                                skipped.append(f"{result_set_name}_{result_type}")
                                continue

                            # Write to sheet with result set name prefix
                            sheet_name = f"{result_set_name}_{result_type}"[:31]
                            dataset.data.to_excel(writer, sheet_name=sheet_name, index=False)
                            exported_count += 1

                    except Exception as e:
                        print(f"Error exporting {result_set_name} - {result_type}: {str(e)}")
                        import traceback
                        traceback.print_exc()
                        skipped.append(f"{result_set_name}_{result_type}")
                        continue

        # Build success message
        message = f"Successfully exported {exported_count} sheets ({len(self.result_set_ids)} result sets × {len(self.result_types)} result types)!"
        if skipped:
            message += f"\n\nSkipped {len(skipped)} items (no data): {', '.join(skipped[:5])}"
            if len(skipped) > 5:
                message += f" and {len(skipped) - 5} more..."

        self.finished.emit(True, message, str(self.output_file))

    def _export_per_file(self):
        """Export each result type from each result set to separate files."""
        import pandas as pd
        from database.repository import ResultSetRepository

        self.output_folder.mkdir(parents=True, exist_ok=True)

        # Calculate total operations
        total_operations = len(self.result_types) * len(self.result_set_ids)
        current_operation = 0

        self.progress.emit("Preparing export folder...", 0, total_operations)

        export_service = ExportService(self.context, self.result_service)
        exported_count = 0
        skipped = []

        # Generate single timestamp for this export
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Get result set names
        with self.context.session() as session:
            result_set_repo = ResultSetRepository(session)
            result_set_names = {}
            for rs_id in self.result_set_ids:
                rs = result_set_repo.get_by_id(rs_id)
                if rs:
                    result_set_names[rs_id] = rs.name

        for result_set_id in self.result_set_ids:
            result_set_name = result_set_names.get(result_set_id, f"RS{result_set_id}")

            for result_type in self.result_types:
                current_operation += 1
                self.progress.emit(
                    f"Exporting {result_set_name} - {result_type}...",
                    current_operation,
                    total_operations
                )

                try:
                    # Special handling for pushover curves
                    if result_type == "Curves":
                        # Export pushover curves to single Excel file
                        from database.repository import PushoverCaseRepository

                        if self.format_type != "excel":
                            # Curves can only be exported to Excel (multiple sheets)
                            skipped.append(f"{result_set_name}_Curves (CSV not supported)")
                            continue

                        ext = "xlsx"
                        filename = f"{result_set_name}_{self.analysis_context}_Curves_{timestamp}.{ext}"
                        output_path = self.output_folder / filename

                        with self.context.session() as session:
                            pushover_repo = PushoverCaseRepository(session)
                            cases = pushover_repo.get_by_result_set(result_set_id)

                            if not cases:
                                skipped.append(f"{result_set_name}_Curves")
                                continue

                            # Use pandas ExcelWriter to create multi-sheet workbook
                            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                                curve_count = 0
                                for case in cases:
                                    curve_points = pushover_repo.get_curve_data(case.id)

                                    if not curve_points:
                                        continue

                                    # Build DataFrame for this curve
                                    data = {
                                        'Step Number': [pt.step_number for pt in curve_points],
                                        'Base Shear (kN)': [pt.base_shear for pt in curve_points],
                                        'Displacement (mm)': [pt.displacement for pt in curve_points]
                                    }
                                    df = pd.DataFrame(data)

                                    # Sheet name: Case name (truncate to 31 chars)
                                    sheet_name = case.name[:31]
                                    df.to_excel(writer, sheet_name=sheet_name, index=False)
                                    curve_count += 1

                            if curve_count > 0:
                                exported_count += 1
                            else:
                                skipped.append(f"{result_set_name}_Curves")

                        continue  # Move to next result type

                    # Determine if this is a global, element, or joint result
                    is_element = any(x in result_type for x in ['Wall', 'Quad', 'Column', 'Beam'])
                    is_joint = any(x in result_type for x in ['SoilPressures', 'VerticalDisplacements', 'JointDisplacements'])

                    # Build output path with single timestamp (clean display name for joints)
                    display_type = result_type.replace('_Min', '') if is_joint else result_type
                    ext = "xlsx" if self.format_type == "excel" else "csv"
                    filename = f"{result_set_name}_{self.analysis_context}_{display_type}_{timestamp}.{ext}"
                    output_path = self.output_folder / filename

                    if is_element:
                        # Get combined element data
                        df = export_service.get_element_export_dataframe(
                            result_type=result_type,
                            result_set_id=result_set_id
                        )

                        if df is None or df.empty:
                            skipped.append(f"{result_set_name}_{result_type}")
                            continue

                        # Write file
                        if self.format_type == "excel":
                            df.to_excel(output_path, index=False)
                        else:
                            df.to_csv(output_path, index=False)
                        exported_count += 1

                    elif is_joint:
                        # Get joint result data
                        # result_type already includes _Min suffix from _get_selected_result_types()
                        dataset = self.result_service.get_joint_dataset(
                            result_type=result_type,
                            result_set_id=result_set_id
                        )

                        if dataset is None or dataset.data is None or dataset.data.empty:
                            skipped.append(f"{result_set_name}_{result_type}")
                            continue

                        # Write file (output_path already has clean name)
                        if self.format_type == "excel":
                            dataset.data.to_excel(output_path, index=False)
                        else:
                            dataset.data.to_csv(output_path, index=False)
                        exported_count += 1

                    else:
                        # Export using service (for global results)
                        options = ExportOptions(
                            result_set_id=result_set_id,
                            result_type=result_type,
                            output_path=output_path,
                            format=self.format_type
                        )

                        export_service.export_result_type(options)
                        exported_count += 1

                except Exception as e:
                    print(f"Error exporting {result_set_name} - {result_type}: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    skipped.append(f"{result_set_name}_{result_type}")
                    continue

        # Build success message
        message = f"Successfully exported {exported_count} files ({len(self.result_set_ids)} result sets × {len(self.result_types)} result types)!"
        if skipped:
            message += f"\n\nSkipped {len(skipped)} items (no data): {', '.join(skipped[:5])}"
            if len(skipped) > 5:
                message += f" and {len(skipped) - 5} more..."

        self.finished.emit(True, message, str(self.output_folder))


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
        """Handle progress update from worker thread.

        Args:
            message: Progress message to display
            current: Current step number
            total: Total number of steps
        """
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.status_label.setText(message)

    def _on_finished(self, success: bool, message: str):
        """Handle export completion from worker thread.

        Args:
            success: Whether export succeeded
            message: Success or error message
        """
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
            QProgressBar {{
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                background-color: {COLORS['card']};
                text-align: center;
                color: {COLORS['text']};
            }}
            QProgressBar::chunk {{
                background-color: {COLORS['accent']};
                border-radius: 3px;
            }}
        """)


class ExportWorker(QThread):
    """Background worker for executing export operations.

    Runs export in separate thread to prevent UI freezing.

    Signals:
        progress: Emitted with (message, current, total) during export
        finished: Emitted with (success, message) when complete
    """

    progress = pyqtSignal(str, int, int)
    finished = pyqtSignal(bool, str)

    def __init__(self, context, result_service, options: ExportOptions):
        """Initialize export worker.

        Args:
            context: ProjectContext instance
            result_service: ResultDataService instance
            options: ExportOptions specifying what to export
        """
        super().__init__()
        self.context = context
        self.result_service = result_service
        self.options = options

    def run(self):
        """Execute export in background thread."""
        try:
            export_service = ExportService(self.context, self.result_service)

            export_service.export_result_type(
                self.options,
                progress_callback=self._emit_progress
            )

            file_format = "Excel" if self.options.format == "excel" else "CSV"
            self.finished.emit(
                True,
                f"Successfully exported {self.options.result_type} to {file_format} file!"
            )

        except Exception as e:
            self.finished.emit(
                False,
                f"Export failed: {str(e)}"
            )

    def _emit_progress(self, message: str, current: int, total: int):
        """Emit progress signal.

        Args:
            message: Progress message
            current: Current step number
            total: Total number of steps
        """
        self.progress.emit(message, current, total)


# ===== PROJECT EXPORT TO EXCEL =====


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

        from services.export_service import ProjectExportExcelOptions

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

        # Apply line edit styling
        for widget in self.findChildren(QLineEdit):
            widget.setStyleSheet(self._lineedit_style())

        # Apply progress bar styling
        self.progress_bar.setStyleSheet(self._progress_style())
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
    def _lineedit_style() -> str:
        """LineEdit style matching export results dialog."""
        c = PALETTE
        return f"""
            QLineEdit {{
                background-color: {c['bg_tertiary']};
                border: 1px solid {c['border_default']};
                border-radius: 6px;
                padding: 8px 12px;
                color: {c['text_primary']};
            }}
            QLineEdit:focus {{
                border-color: {c['accent_primary']};
            }}
        """

    @staticmethod
    def _checkbox_style() -> str:
        return FormStyles.checkbox(indent=False)

    @staticmethod
    def _checkbox_style() -> str:
        return FormStyles.checkbox(indent=False)

    @staticmethod
    def _progress_style() -> str:
        """ProgressBar style matching export results dialog."""
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


class ExportProjectExcelWorker(QThread):
    """Background worker for Excel project export."""

    progress = pyqtSignal(str, int, int)
    finished = pyqtSignal(bool, str, str)

    def __init__(self, context, result_service, options):
        super().__init__()
        self.context = context
        self.result_service = result_service
        self.options = options

    def run(self):
        try:
            from services.export_service import ExportService

            export_service = ExportService(self.context, self.result_service)

            export_service.export_project_excel(
                self.options,
                progress_callback=self._emit_progress
            )

            self.finished.emit(
                True,
                "Project exported successfully to Excel!",
                str(self.options.output_path)
            )
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.finished.emit(False, f"Export failed: {str(e)}", "")

    def _emit_progress(self, message: str, current: int, total: int):
        self.progress.emit(message, current, total)
    def _checkbox_style(self) -> str:
        return FormStyles.checkbox(indent=False)
