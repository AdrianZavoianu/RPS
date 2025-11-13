"""
Export dialogs for RPS.

Provides UI for exporting result data to Excel and CSV formats.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QRadioButton, QGroupBox, QCheckBox,
    QFileDialog, QMessageBox, QProgressBar, QTreeWidget,
    QTreeWidgetItem, QApplication
)
from PyQt6.QtCore import QThread, pyqtSignal, QStandardPaths, Qt
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set

from services.export_service import ExportService, ExportOptions
from gui.ui_helpers import create_styled_button
from gui.styles import COLORS
from database.models import GlobalResultsCache, ElementResultsCache, JointResultsCache


class ComprehensiveExportDialog(QDialog):
    """Comprehensive export dialog for exporting multiple result types.

    Exports all results by default with ability to filter specific types.
    Works independently of current browser selection.

    Args:
        context: ProjectContext instance
        result_service: ResultDataService instance
        current_result_set_id: ID of current result set
        project_name: Project name for filename
        parent: Parent widget
    """

    def __init__(self, context, result_service, current_result_set_id,
                 project_name, parent=None):
        super().__init__(parent)

        self.context = context
        self.result_service = result_service
        self.current_result_set_id = current_result_set_id
        self.project_name = project_name

        # Discovered result types (populated on init)
        self.available_types: Dict[str, List[str]] = {
            'global': [],  # ['Drifts_X', 'Drifts_Y', 'Accelerations_X', ...]
            'element': [],  # ['WallShears_V2', 'QuadRotations', ...]
            'joint': []  # ['SoilPressures', 'VerticalDisplacements']
        }

        # Available result sets (populated on init)
        self.available_result_sets = []  # List of (id, name) tuples

        self.setWindowTitle("Export Results")
        self.setMinimumSize(750, 400)

        # Default output folder
        self.output_folder = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation))

        # Discover available result sets and types from cache
        self._discover_result_sets()
        self._discover_result_types()

        self._setup_ui()
        self._apply_styling()

        # Auto-fit window height to content after UI is built
        self._auto_fit_height()

    def _discover_result_sets(self):
        """Query database to find all result sets in the project."""
        from database.repository import ResultSetRepository, ProjectRepository

        with self.context.session() as session:
            # Get project ID from database
            project_repo = ProjectRepository(session)
            project = project_repo.get_by_name(self.context.name)

            if not project:
                self.available_result_sets = []
                return

            # Get all result sets for this project
            result_set_repo = ResultSetRepository(session)
            result_sets = result_set_repo.get_by_project(project.id)
            self.available_result_sets = [(rs.id, rs.name) for rs in result_sets]

    def _discover_result_types(self):
        """Query cache to find all result types with data.

        Note: Cache stores base types (e.g., "Drifts"). We'll show only base types
        in the UI, and export will automatically include all directions for each type.
        """
        with self.context.session() as session:
            # Query GlobalResultsCache for base types only
            global_base_types = session.query(
                GlobalResultsCache.result_type
            ).filter(
                GlobalResultsCache.result_set_id == self.current_result_set_id
            ).distinct().all()

            # Store base types only (e.g., "Drifts", "Accelerations", "Forces")
            self.available_types['global'] = sorted([r[0] for r in global_base_types])

            # Query ElementResultsCache - extract base types by removing direction suffix
            element_results = session.query(
                ElementResultsCache.result_type
            ).filter(
                ElementResultsCache.result_set_id == self.current_result_set_id
            ).distinct().all()

            # Extract base types from element results (remove _V2, _V3, etc.)
            element_base_types = set()
            for result_type, in element_results:
                # Remove direction suffix if present
                if '_V2' in result_type or '_V3' in result_type:
                    base_type = result_type.rsplit('_', 1)[0]
                    element_base_types.add(base_type)
                else:
                    # No direction suffix (e.g., QuadRotations)
                    element_base_types.add(result_type)

            self.available_types['element'] = sorted(element_base_types)

            # Query JointResultsCache - extract base types by removing suffix
            joint_results = session.query(
                JointResultsCache.result_type
            ).filter(
                JointResultsCache.result_set_id == self.current_result_set_id
            ).distinct().all()

            # Extract base types from joint results (remove _Min suffix)
            joint_base_types = set()
            for result_type, in joint_results:
                # Remove suffix (e.g., 'SoilPressures_Min' -> 'SoilPressures')
                if '_Min' in result_type:
                    base_type = result_type.rsplit('_', 1)[0]
                    joint_base_types.add(base_type)
                else:
                    joint_base_types.add(result_type)

            self.available_types['joint'] = sorted(joint_base_types)

    def _setup_ui(self):
        """Build dialog UI with vertical layout."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # Header
        header = QLabel("Export Results")
        header.setStyleSheet(f"color: {COLORS['text']}; font-size: 24px; font-weight: 600; margin: 0px; padding: 0px; line-height: 1.0;")
        layout.addWidget(header)

        # Info label
        total_types = len(self.available_types['global']) + len(self.available_types['element']) + len(self.available_types['joint'])
        info_label = QLabel(
            f"Found {total_types} result types with data. "
            f"All types selected by default - uncheck to exclude."
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
        result_types_layout.setSpacing(4)

        # Quick actions for result types
        rt_actions = QHBoxLayout()
        rt_all_btn = create_styled_button("All", "ghost", "sm")
        rt_all_btn.clicked.connect(lambda: self._set_all_checked(True))
        rt_none_btn = create_styled_button("None", "ghost", "sm")
        rt_none_btn.clicked.connect(lambda: self._set_all_checked(False))
        rt_actions.addWidget(rt_all_btn)
        rt_actions.addWidget(rt_none_btn)
        rt_actions.addStretch()
        result_types_layout.addLayout(rt_actions)

        self.result_tree = QTreeWidget()
        self.result_tree.setHeaderHidden(True)
        self._build_result_tree()
        result_types_layout.addWidget(self.result_tree)

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

        self.result_sets_tree = QTreeWidget()
        self.result_sets_tree.setHeaderHidden(True)
        self.result_sets_tree.setMaximumHeight(150)  # Compact height
        self._build_result_sets_tree()
        result_sets_layout.addWidget(self.result_sets_tree)

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

    def _build_result_sets_tree(self):
        """Build tree widget with all available result sets (all checked by default)."""
        for rs_id, rs_name in self.available_result_sets:
            item = QTreeWidgetItem(self.result_sets_tree, [rs_name])
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(0, Qt.CheckState.Checked)  # All checked by default
            item.setData(0, Qt.ItemDataRole.UserRole, rs_id)  # Store ID for later retrieval

    def _set_result_sets_checked(self, checked: bool):
        """Set all result set items to checked or unchecked state."""
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        for i in range(self.result_sets_tree.topLevelItemCount()):
            item = self.result_sets_tree.topLevelItem(i)
            item.setCheckState(0, state)

    def _get_selected_result_set_ids(self) -> List[int]:
        """Get list of checked result set IDs."""
        selected_ids = []
        for i in range(self.result_sets_tree.topLevelItemCount()):
            item = self.result_sets_tree.topLevelItem(i)
            if item.checkState(0) == Qt.CheckState.Checked:
                rs_id = item.data(0, Qt.ItemDataRole.UserRole)
                selected_ids.append(rs_id)
        return selected_ids

    def _build_result_tree(self):
        """Build tree widget with all available result types."""
        # Global Results section
        if self.available_types['global']:
            global_item = QTreeWidgetItem(self.result_tree, ["Global Results"])
            global_item.setFlags(global_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            global_item.setCheckState(0, Qt.CheckState.Checked)
            global_item.setExpanded(True)

            for result_type in self.available_types['global']:
                child = QTreeWidgetItem(global_item, [result_type])
                child.setFlags(child.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                child.setCheckState(0, Qt.CheckState.Checked)

        # Element Results section
        if self.available_types['element']:
            element_item = QTreeWidgetItem(self.result_tree, ["Element Results"])
            element_item.setFlags(element_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            element_item.setCheckState(0, Qt.CheckState.Checked)
            element_item.setExpanded(True)

            for result_type in self.available_types['element']:
                child = QTreeWidgetItem(element_item, [result_type])
                child.setFlags(child.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                child.setCheckState(0, Qt.CheckState.Checked)

        # Joint Results section
        if self.available_types['joint']:
            joint_item = QTreeWidgetItem(self.result_tree, ["Joint Results"])
            joint_item.setFlags(joint_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            joint_item.setCheckState(0, Qt.CheckState.Checked)
            joint_item.setExpanded(True)

            for result_type in self.available_types['joint']:
                child = QTreeWidgetItem(joint_item, [result_type])
                child.setFlags(child.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                child.setCheckState(0, Qt.CheckState.Checked)

    def _set_all_checked(self, checked: bool):
        """Set all tree items to checked or unchecked state."""
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked

        # Iterate all top-level items
        for i in range(self.result_tree.topLevelItemCount()):
            parent = self.result_tree.topLevelItem(i)
            parent.setCheckState(0, state)

            # Iterate children
            for j in range(parent.childCount()):
                child = parent.child(j)
                child.setCheckState(0, state)

    def _get_selected_result_types(self) -> List[str]:
        """Get list of checked result types from tree.

        Expands base types (e.g., "Drifts") to include all directions
        (e.g., "Drifts_X", "Drifts_Y") for export service.
        """
        from config.result_config import RESULT_CONFIGS

        selected_base_types = []

        for i in range(self.result_tree.topLevelItemCount()):
            parent = self.result_tree.topLevelItem(i)

            for j in range(parent.childCount()):
                child = parent.child(j)
                if child.checkState(0) == Qt.CheckState.Checked:
                    selected_base_types.append(child.text(0))

        # Expand base types to include all directions
        expanded_types = []
        for base_type in selected_base_types:
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
                # Check cache for actual full type names
                with self.context.session() as session:
                    element_full_types = session.query(
                        ElementResultsCache.result_type
                    ).filter(
                        ElementResultsCache.result_set_id == self.current_result_set_id
                    ).distinct().all()

                    # Find all variants of this base type
                    for full_type, in element_full_types:
                        if full_type.startswith(base_type):
                            expanded_types.append(full_type)
            elif base_type in self.available_types['joint']:
                # Joint type - need to expand with suffix (_Min)
                # Check cache for actual full type names
                with self.context.session() as session:
                    joint_full_types = session.query(
                        JointResultsCache.result_type
                    ).filter(
                        JointResultsCache.result_set_id == self.current_result_set_id
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
                f"{selected_count} files: {self.project_name}_<ResultType>_<timestamp>.{format_ext}"
            )

    def _build_combined_filename(self) -> str:
        """Build filename for combined export."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{self.project_name}_AllResults_{timestamp}.xlsx"

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
            output_folder = self.output_folder / f"{self.project_name}_Export_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
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
            output_folder=output_folder
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

        # Apply tree widget styling to both trees
        tree_style = self._tree_style()
        self.result_tree.setStyleSheet(tree_style)
        self.result_sets_tree.setStyleSheet(tree_style)

        # Apply progress bar styling
        self.progress_bar.setStyleSheet(self._progress_style())

    @staticmethod
    def _groupbox_style() -> str:
        """GroupBox style matching folder import dialog."""
        return f"""
            QGroupBox {{
                background-color: {COLORS['card']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                margin-top: 6px;
                padding-top: 12px;
                color: {COLORS['text']};
                font-weight: 600;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 4px;
            }}
            /* Remove black background for Export Options group */
            QGroupBox#exportOptionsGroup {{
                background-color: transparent;
            }}
            QGroupBox#exportOptionsGroup QRadioButton,
            QGroupBox#exportOptionsGroup QCheckBox {{
                background-color: transparent;
            }}
        """

    @staticmethod
    def _lineedit_style() -> str:
        """LineEdit style matching folder import dialog."""
        return f"""
            QLineEdit {{
                background-color: {COLORS['background']};
                border: 2px solid {COLORS['border']};
                border-radius: 4px;
                padding: 6px 10px;
                color: {COLORS['text']};
            }}
            QLineEdit:focus {{
                border-color: {COLORS['accent']};
            }}
        """

    @staticmethod
    def _tree_style() -> str:
        """TreeWidget style matching folder import dialog with custom checkbox indicators."""
        # Create checkmark image for checkboxes
        from PyQt6.QtGui import QPixmap, QPainter, QColor, QPen
        from PyQt6.QtCore import Qt
        import tempfile
        import os

        checkmark_pixmap = QPixmap(18, 18)
        checkmark_pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(checkmark_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#ffffff"), 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(4, 9, 7, 12)
        painter.drawLine(7, 12, 14, 5)
        painter.end()

        temp_dir = tempfile.gettempdir()
        checkmark_path = os.path.join(temp_dir, "rps_export_checkbox_check.png")
        checkmark_pixmap.save(checkmark_path, "PNG")
        checkmark_url = checkmark_path.replace("\\", "/")

        return f"""
            QTreeWidget {{
                background-color: {COLORS['background']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                padding: 8px 4px 4px 4px;
                color: {COLORS['text']};
            }}
            QTreeWidget::item {{
                padding: 4px 8px;
                border-radius: 2px;
            }}
            QTreeWidget::item:hover {{
                background-color: {COLORS['card']};
            }}
            QTreeWidget::item:selected {{
                background-color: {COLORS['accent']};
                color: white;
            }}
            QTreeWidget::indicator {{
                width: 18px;
                height: 18px;
                border: 2px solid {COLORS['border']};
                border-radius: 3px;
                background-color: {COLORS['background']};
            }}
            QTreeWidget::indicator:hover {{
                border-color: {COLORS['accent']};
                background-color: {COLORS['card']};
            }}
            QTreeWidget::indicator:checked {{
                background-color: {COLORS['accent']};
                border-color: {COLORS['accent']};
                image: url({checkmark_url});
            }}
            QTreeWidget::indicator:checked:hover {{
                background-color: #5a99a8;
                border-color: #5a99a8;
                image: url({checkmark_url});
            }}
        """

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
        """Auto-fit dialog height based on tree content."""
        # Calculate required height based on tree items
        tree_item_height = 30  # Approximate height per item including padding

        # Count total items (top-level + children)
        total_items = 0
        for i in range(self.result_tree.topLevelItemCount()):
            parent = self.result_tree.topLevelItem(i)
            total_items += 1  # Count parent
            if parent.isExpanded():
                total_items += parent.childCount()  # Count children

        # Calculate tree height (add extra for padding, borders, and buttons)
        tree_content_height = (total_items * tree_item_height) + 100  # 100px for buttons and padding

        # Add fixed heights for other UI elements
        header_height = 80  # Header + info label
        options_height = 150  # Export options group
        output_height = 150  # Output location group
        buttons_height = 80  # Bottom buttons
        padding = 50  # Additional padding

        # Calculate total required height
        required_height = max(
            tree_content_height,  # Based on tree content
            options_height + output_height  # Right column minimum
        ) + header_height + buttons_height + padding

        # Cap at reasonable maximum (don't exceed screen height)
        screen = QApplication.primaryScreen()
        if screen:
            screen_height = screen.availableGeometry().height()
            max_height = int(screen_height * 0.85)  # Use 85% of screen height max
            required_height = min(required_height, max_height)

        # Set the dialog height
        current_width = self.width()
        self.resize(current_width, required_height)


class ComprehensiveExportWorker(QThread):
    """Background worker for comprehensive export operations."""

    progress = pyqtSignal(str, int, int)
    finished = pyqtSignal(bool, str, str)  # success, message, output_path

    def __init__(self, context, result_service, result_set_ids, result_types,
                 format_type, is_combined, output_file, output_folder):
        super().__init__()
        self.context = context
        self.result_service = result_service
        self.result_set_ids = result_set_ids
        self.result_types = result_types
        self.format_type = format_type
        self.is_combined = is_combined
        self.output_file = output_file
        self.output_folder = output_folder

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
                        # Determine if this is a global, element, or joint result
                        is_element = any(x in result_type for x in ['Wall', 'Quad', 'Column', 'Beam'])
                        is_joint = any(x in result_type for x in ['SoilPressures', 'VerticalDisplacements'])

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
                    # Determine if this is a global, element, or joint result
                    is_element = any(x in result_type for x in ['Wall', 'Quad', 'Column', 'Beam'])
                    is_joint = any(x in result_type for x in ['SoilPressures', 'VerticalDisplacements'])

                    # Build output path with single timestamp (clean display name for joints)
                    display_type = result_type.replace('_Min', '') if is_joint else result_type
                    ext = "xlsx" if self.format_type == "excel" else "csv"
                    filename = f"{result_set_name}_{display_type}_{timestamp}.{ext}"
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

    @staticmethod
    def _groupbox_style() -> str:
        """GroupBox style matching export results dialog."""
        return f"""
            QGroupBox {{
                background-color: {COLORS['card']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                margin-top: 0px;
                padding-top: 12px;
                color: {COLORS['text']};
                font-weight: 600;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 4px;
            }}
            /* Remove background for Export Options group */
            QGroupBox#exportOptionsGroup {{
                background-color: transparent;
            }}
            QGroupBox#exportOptionsGroup QCheckBox {{
                background-color: transparent;
            }}
        """

    @staticmethod
    def _lineedit_style() -> str:
        """LineEdit style matching export results dialog."""
        return f"""
            QLineEdit {{
                background-color: {COLORS['background']};
                border: 2px solid {COLORS['border']};
                border-radius: 4px;
                padding: 6px 10px;
                color: {COLORS['text']};
            }}
            QLineEdit:focus {{
                border-color: {COLORS['accent']};
            }}
        """

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
