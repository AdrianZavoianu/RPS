"""Pushover Global Results Import Dialog

Imports pushover global results (drifts, displacements, forces) from a folder.
Follows the same design pattern as NLTHA folder import.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Optional, Set

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QProgressBar,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .styles import COLORS
from .ui_helpers import create_styled_button, create_styled_label

logger = logging.getLogger(__name__)


class PushoverImportWorker(QThread):
    """Worker thread for importing pushover data (global + elements)."""

    progress = pyqtSignal(str, int, int)  # message, current, total
    finished = pyqtSignal(dict)  # stats
    error = pyqtSignal(str)  # error message

    def __init__(
        self,
        project_id: int,
        session,
        folder_path: Path,
        result_set_name: str,
        global_files: List[Path],
        wall_files: List[Path],
        column_files: List[Path],
        beam_files: List[Path],
        selected_load_cases_x: List[str],
        selected_load_cases_y: List[str],
    ):
        super().__init__()
        self.project_id = project_id
        self.session = session
        self.folder_path = folder_path
        self.result_set_name = result_set_name
        self.global_files = global_files
        self.wall_files = wall_files
        self.column_files = column_files
        self.beam_files = beam_files
        self.selected_load_cases_x = selected_load_cases_x
        self.selected_load_cases_y = selected_load_cases_y

    def run(self):
        """Run import in background thread."""
        from processing.pushover_global_importer import PushoverGlobalImporter
        from processing.pushover_wall_importer import PushoverWallImporter
        from processing.pushover_column_importer import PushoverColumnImporter
        from processing.pushover_column_shear_importer import PushoverColumnShearImporter
        from processing.pushover_beam_importer import PushoverBeamImporter
        from database.models import ResultSet

        try:
            combined_stats = {}

            # Import global results if present
            if self.global_files:
                self.progress.emit("Importing global results...", 10, 100)

                global_importer = PushoverGlobalImporter(
                    project_id=self.project_id,
                    session=self.session,
                    folder_path=self.folder_path,
                    result_set_name=self.result_set_name,
                    valid_files=self.global_files,
                    selected_load_cases_x=self.selected_load_cases_x,
                    selected_load_cases_y=self.selected_load_cases_y,
                    progress_callback=lambda msg, curr, total: self._on_progress(f"Global: {msg}", curr // 2, 100),
                )

                global_stats = global_importer.import_all()
                combined_stats.update(global_stats)

            # Get the result set ID (created by global import or need to create)
            result_set = self.session.query(ResultSet).filter(
                ResultSet.project_id == self.project_id,
                ResultSet.name == self.result_set_name
            ).first()

            if not result_set:
                # Create result set if it doesn't exist (no global files)
                result_set = ResultSet(
                    project_id=self.project_id,
                    name=self.result_set_name,
                    analysis_type='Pushover'
                )
                self.session.add(result_set)
                self.session.flush()

            # Import wall results if present
            if self.wall_files:
                self.progress.emit("Importing wall results...", 50, 100)

                for wall_file in self.wall_files:
                    wall_importer = PushoverWallImporter(
                        project_id=self.project_id,
                        session=self.session,
                        result_set_id=result_set.id,
                        file_path=wall_file,
                        selected_load_cases_x=self.selected_load_cases_x,
                        selected_load_cases_y=self.selected_load_cases_y,
                        progress_callback=lambda msg, curr, total: self._on_progress(f"Walls: {msg}", 50 + curr // 6, 100),
                    )

                    wall_stats = wall_importer.import_all()
                    self._merge_stats(combined_stats, wall_stats)

            # Import column results if present
            if self.column_files:
                self.progress.emit("Importing column rotations...", 70, 100)

                for column_file in self.column_files:
                    column_importer = PushoverColumnImporter(
                        project_id=self.project_id,
                        session=self.session,
                        result_set_id=result_set.id,
                        file_path=column_file,
                        selected_load_cases_x=self.selected_load_cases_x,
                        selected_load_cases_y=self.selected_load_cases_y,
                        progress_callback=lambda msg, curr, total: self._on_progress(f"Column Rotations: {msg}", 70 + curr // 8, 100),
                    )

                    column_stats = column_importer.import_all()
                    self._merge_stats(combined_stats, column_stats)

                # Also import column shears from the same files
                self.progress.emit("Importing column shears...", 75, 100)

                for column_file in self.column_files:
                    column_shear_importer = PushoverColumnShearImporter(
                        project_id=self.project_id,
                        session=self.session,
                        result_set_id=result_set.id,
                        file_path=column_file,
                        selected_load_cases_x=self.selected_load_cases_x,
                        selected_load_cases_y=self.selected_load_cases_y,
                        progress_callback=lambda msg, curr, total: self._on_progress(f"Column Shears: {msg}", 75 + curr // 8, 100),
                    )

                    shear_stats = column_shear_importer.import_all()
                    self._merge_stats(combined_stats, shear_stats)

            # Import beam results if present
            if self.beam_files:
                self.progress.emit("Importing beam results...", 80, 100)

                for beam_file in self.beam_files:
                    beam_importer = PushoverBeamImporter(
                        project_id=self.project_id,
                        session=self.session,
                        result_set_id=result_set.id,
                        file_path=beam_file,
                        selected_load_cases_x=self.selected_load_cases_x,
                        selected_load_cases_y=self.selected_load_cases_y,
                        progress_callback=lambda msg, curr, total: self._on_progress(f"Beams: {msg}", 80 + curr // 8, 100),
                    )

                    beam_stats = beam_importer.import_all()
                    self._merge_stats(combined_stats, beam_stats)

            # Import joint displacements if present (from global results files)
            if self.global_files:
                from processing.pushover_joint_importer import PushoverJointImporter

                self.progress.emit("Importing joint displacements...", 85, 100)

                for joint_file in self.global_files:
                    joint_importer = PushoverJointImporter(
                        project_id=self.project_id,
                        session=self.session,
                        result_set_id=result_set.id,
                        file_path=joint_file,
                        selected_load_cases_x=self.selected_load_cases_x,
                        selected_load_cases_y=self.selected_load_cases_y,
                        progress_callback=lambda msg, curr, total: self._on_progress(f"Joints: {msg}", 85 + curr // 20, 100),
                    )

                    joint_stats = joint_importer.import_all()
                    self._merge_stats(combined_stats, joint_stats)

            # Import soil pressures if present (from global results files)
            if self.global_files:
                from processing.pushover_soil_pressure_importer import PushoverSoilPressureImporter

                self.progress.emit("Importing soil pressures...", 90, 100)

                for soil_file in self.global_files:
                    soil_importer = PushoverSoilPressureImporter(
                        project_id=self.project_id,
                        session=self.session,
                        result_set_id=result_set.id,
                        file_path=soil_file,
                        selected_load_cases_x=self.selected_load_cases_x,
                        selected_load_cases_y=self.selected_load_cases_y,
                        progress_callback=lambda msg, curr, total: self._on_progress(f"Soil Pressures: {msg}", 90 + curr // 20, 100),
                    )

                    soil_stats = soil_importer.import_all()
                    self._merge_stats(combined_stats, soil_stats)

            # Import vertical displacements if present (from global results files)
            if self.global_files:
                from processing.pushover_vert_displacement_importer import PushoverVertDisplacementImporter

                self.progress.emit("Importing vertical displacements...", 95, 100)

                for vert_file in self.global_files:
                    vert_importer = PushoverVertDisplacementImporter(
                        project_id=self.project_id,
                        session=self.session,
                        result_set_id=result_set.id,
                        file_path=vert_file,
                        selected_load_cases_x=self.selected_load_cases_x,
                        selected_load_cases_y=self.selected_load_cases_y,
                        progress_callback=lambda msg, curr, total: self._on_progress(f"Vert Displ: {msg}", 95 + curr // 20, 100),
                    )

                    vert_stats = vert_importer.import_all()
                    self._merge_stats(combined_stats, vert_stats)

            self.finished.emit(combined_stats)

        except Exception as e:
            self.error.emit(str(e))
            logger.exception("Import failed")

    def _merge_stats(self, combined_stats: dict, new_stats: dict):
        """Merge stats dictionaries."""
        for key, value in new_stats.items():
            if key in combined_stats:
                if isinstance(value, int):
                    combined_stats[key] += value
                elif isinstance(value, list):
                    combined_stats[key].extend(value)
            else:
                combined_stats[key] = value

    def _on_progress(self, message: str, current: int, total: int):
        """Relay progress updates."""
        self.progress.emit(message, current, total)


class PushoverScanWorker(QThread):
    """Worker thread for scanning pushover files."""

    progress = pyqtSignal(str, int, int)  # message, current, total
    finished = pyqtSignal(object)  # scan results
    error = pyqtSignal(str)  # error message

    def __init__(self, folder_path: Path):
        super().__init__()
        self.folder_path = folder_path

    def run(self):
        """Scan folder for pushover global and element results files."""
        from processing.pushover_global_parser import PushoverGlobalParser
        from processing.pushover_wall_parser import PushoverWallParser
        from processing.pushover_column_parser import PushoverColumnParser
        from processing.pushover_beam_parser import PushoverBeamParser

        try:
            self.progress.emit("Scanning folder...", 0, 100)

            # Find Excel files
            excel_files = list(self.folder_path.glob("*.xlsx")) + list(self.folder_path.glob("*.xls"))

            if not excel_files:
                self.error.emit("No Excel files found in folder")
                return

            global_files = []
            wall_files = []
            column_files = []
            beam_files = []
            all_load_cases_x = set()
            all_load_cases_y = set()
            all_piers = set()
            all_columns = set()
            all_beams = set()

            total = len(excel_files)
            for idx, file_path in enumerate(excel_files):
                self.progress.emit(f"Scanning {file_path.name}...", idx + 1, total)

                # Try parsing as global results
                try:
                    parser = PushoverGlobalParser(file_path)
                    directions = parser.get_available_directions()

                    if directions:
                        global_files.append(file_path)

                        # Extract load cases for each direction
                        if 'X' in directions:
                            cases_x = parser.get_output_cases('X')
                            all_load_cases_x.update(cases_x)

                        if 'Y' in directions:
                            cases_y = parser.get_output_cases('Y')
                            all_load_cases_y.update(cases_y)

                except Exception as e:
                    logger.debug(f"Not a global results file: {file_path.name}")

                # Try parsing as wall results
                try:
                    wall_parser = PushoverWallParser(file_path)
                    directions = wall_parser.get_available_directions()

                    if directions:
                        wall_files.append(file_path)

                        # Extract load cases for each direction
                        if 'X' in directions:
                            cases_x = wall_parser.get_output_cases('X')
                            all_load_cases_x.update(cases_x)

                        if 'Y' in directions:
                            cases_y = wall_parser.get_output_cases('Y')
                            all_load_cases_y.update(cases_y)

                        # Extract piers
                        piers = wall_parser.get_piers()
                        all_piers.update(piers)

                except Exception as e:
                    logger.debug(f"Not a wall results file: {file_path.name}")

                # Try parsing as column results
                try:
                    column_parser = PushoverColumnParser(file_path)
                    directions = column_parser.get_available_directions()

                    if directions:
                        column_files.append(file_path)

                        # Extract load cases for each direction
                        if 'X' in directions:
                            cases_x = column_parser.get_output_cases('X')
                            all_load_cases_x.update(cases_x)

                        if 'Y' in directions:
                            cases_y = column_parser.get_output_cases('Y')
                            all_load_cases_y.update(cases_y)

                        # Extract columns
                        columns = column_parser.get_columns()
                        all_columns.update(columns)

                except Exception as e:
                    logger.debug(f"Not a column results file: {file_path.name}")

                # Try parsing as beam results
                try:
                    beam_parser = PushoverBeamParser(file_path)
                    directions = beam_parser.get_available_directions()

                    if directions:
                        beam_files.append(file_path)

                        # Extract load cases for each direction
                        if 'X' in directions:
                            cases_x = beam_parser.get_output_cases('X')
                            all_load_cases_x.update(cases_x)

                        if 'Y' in directions:
                            cases_y = beam_parser.get_output_cases('Y')
                            all_load_cases_y.update(cases_y)

                        # Extract beams
                        beams = beam_parser.get_beams()
                        all_beams.update(beams)

                except Exception as e:
                    logger.debug(f"Not a beam results file: {file_path.name}")

            if not global_files and not wall_files and not column_files and not beam_files:
                self.error.emit("No valid pushover results files found in folder")
                return

            # Return results
            results = {
                'global_files': global_files,
                'wall_files': wall_files,
                'column_files': column_files,
                'beam_files': beam_files,
                'load_cases_x': sorted(all_load_cases_x),
                'load_cases_y': sorted(all_load_cases_y),
                'piers': sorted(all_piers),
                'columns': sorted(all_columns),
                'beams': sorted(all_beams),
            }

            self.finished.emit(results)

        except Exception as e:
            self.error.emit(str(e))


class PushoverGlobalImportDialog(QDialog):
    """Dialog for importing pushover global results from a folder.

    Follows the same design pattern as NLTHA folder import dialog.
    """

    import_completed = pyqtSignal(dict)  # stats dictionary

    def __init__(
        self,
        project_id: int,
        project_name: str,
        folder_path: str,
        session,
        parent=None
    ):
        super().__init__(parent)
        self.project_id = project_id
        self.project_name = project_name
        self.folder_path = Path(folder_path)
        self.session = session

        self.setWindowTitle(f"Import Pushover Global Results - {project_name}")
        self.setMinimumSize(1200, 700)
        self.resize(1400, 750)

        # State
        self.global_files = []  # Global results files
        self.wall_files = []    # Wall results files
        self.column_files = []  # Column results files
        self.beam_files = []    # Beam results files
        self.load_case_checkboxes_x = {}  # load_case → QCheckBox
        self.load_case_checkboxes_y = {}
        self.scan_worker = None
        self.import_worker = None
        self.existing_result_sets = []  # List of existing pushover result sets

        # Check for existing pushover result sets (curves must be imported first)
        if not self._load_existing_result_sets():
            QMessageBox.warning(
                self,
                "No Pushover Result Sets",
                "You must import pushover curves first before importing global results.\n\n"
                "Please use 'Import Pushover Curves' to create a result set, then import global results."
            )
            self.reject()
            return

        self.setup_ui()
        self.start_scan()

    def setup_ui(self):
        """Setup UI following NLTHA dialog pattern."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(16, 16, 16, 16)

        # ============ TOP ROW: Folder and Result Set ============
        top_row = QHBoxLayout()
        top_row.setSpacing(12)

        # Folder path (read-only)
        folder_label = QLabel("Folder:")
        folder_label.setStyleSheet(f"color: {COLORS['text']}; font-weight: 600;")
        top_row.addWidget(folder_label)

        self.folder_display = QLineEdit()
        self.folder_display.setText(str(self.folder_path))
        self.folder_display.setReadOnly(True)
        self.folder_display.setStyleSheet(self._entry_style())
        top_row.addWidget(self.folder_display, stretch=1)

        # Result set selection (combo box with existing pushover result sets)
        rs_label = QLabel("Result Set:")
        rs_label.setStyleSheet(f"color: {COLORS['text']}; font-weight: 600;")
        top_row.addWidget(rs_label)

        self.result_set_combo = QComboBox()
        self.result_set_combo.setStyleSheet(self._combo_style())
        # Populate with existing result sets
        for rs_name in self.existing_result_sets:
            self.result_set_combo.addItem(rs_name)
        if self.existing_result_sets:
            self.result_set_combo.setCurrentIndex(0)
        top_row.addWidget(self.result_set_combo, stretch=1)

        main_layout.addLayout(top_row)

        # ============ MIDDLE ROW: Three columns ============
        data_row = QHBoxLayout()
        data_row.setSpacing(12)

        # FILES column
        files_group = QGroupBox("Files Found")
        files_group.setStyleSheet(self._groupbox_style())
        files_layout = QVBoxLayout(files_group)
        files_layout.setContentsMargins(8, 12, 8, 8)

        self.files_list = QListWidget()
        self.files_list.setStyleSheet(self._list_style())
        files_layout.addWidget(self.files_list)

        data_row.addWidget(files_group, stretch=49)

        # LOAD CASES column (X direction)
        loadcases_x_group = QGroupBox("Load Cases - X Direction")
        loadcases_x_group.setStyleSheet(self._groupbox_style())
        loadcases_x_layout = QVBoxLayout(loadcases_x_group)
        loadcases_x_layout.setContentsMargins(8, 12, 8, 8)
        loadcases_x_layout.setSpacing(4)

        # Select all/none buttons
        lc_x_buttons = QHBoxLayout()
        lc_x_buttons.setSpacing(4)
        self.select_all_x_btn = create_styled_button("All", "ghost", "sm")
        self.select_none_x_btn = create_styled_button("None", "ghost", "sm")
        self.select_all_x_btn.clicked.connect(self._select_all_x)
        self.select_none_x_btn.clicked.connect(self._select_none_x)
        self.select_all_x_btn.setEnabled(False)
        self.select_none_x_btn.setEnabled(False)
        lc_x_buttons.addWidget(self.select_all_x_btn)
        lc_x_buttons.addWidget(self.select_none_x_btn)
        lc_x_buttons.addStretch()
        loadcases_x_layout.addLayout(lc_x_buttons)

        # Scroll area for checkboxes
        self.load_case_scroll_x = QScrollArea()
        self.load_case_scroll_x.setWidgetResizable(True)
        self.load_case_scroll_x.setStyleSheet(f"""
            QScrollArea {{
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                background-color: {COLORS['background']};
            }}
        """)

        self.load_case_container_x = QWidget()
        self.load_case_layout_x = QVBoxLayout(self.load_case_container_x)
        self.load_case_layout_x.setContentsMargins(0, 0, 0, 0)
        self.load_case_layout_x.setSpacing(0)

        self.load_case_placeholder_x = QLabel("Scanning...")
        self.load_case_placeholder_x.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.load_case_placeholder_x.setStyleSheet(f"color: {COLORS['muted']}; padding: 20px;")
        self.load_case_layout_x.addWidget(self.load_case_placeholder_x)
        self.load_case_layout_x.addStretch()

        self.load_case_scroll_x.setWidget(self.load_case_container_x)
        loadcases_x_layout.addWidget(self.load_case_scroll_x)

        data_row.addWidget(loadcases_x_group, stretch=30)

        # LOAD CASES column (Y direction)
        loadcases_y_group = QGroupBox("Load Cases - Y Direction")
        loadcases_y_group.setStyleSheet(self._groupbox_style())
        loadcases_y_layout = QVBoxLayout(loadcases_y_group)
        loadcases_y_layout.setContentsMargins(8, 12, 8, 8)
        loadcases_y_layout.setSpacing(4)

        # Select all/none buttons
        lc_y_buttons = QHBoxLayout()
        lc_y_buttons.setSpacing(4)
        self.select_all_y_btn = create_styled_button("All", "ghost", "sm")
        self.select_none_y_btn = create_styled_button("None", "ghost", "sm")
        self.select_all_y_btn.clicked.connect(self._select_all_y)
        self.select_none_y_btn.clicked.connect(self._select_none_y)
        self.select_all_y_btn.setEnabled(False)
        self.select_none_y_btn.setEnabled(False)
        lc_y_buttons.addWidget(self.select_all_y_btn)
        lc_y_buttons.addWidget(self.select_none_y_btn)
        lc_y_buttons.addStretch()
        loadcases_y_layout.addLayout(lc_y_buttons)

        # Scroll area for checkboxes
        self.load_case_scroll_y = QScrollArea()
        self.load_case_scroll_y.setWidgetResizable(True)
        self.load_case_scroll_y.setStyleSheet(f"""
            QScrollArea {{
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                background-color: {COLORS['background']};
            }}
        """)

        self.load_case_container_y = QWidget()
        self.load_case_layout_y = QVBoxLayout(self.load_case_container_y)
        self.load_case_layout_y.setContentsMargins(0, 0, 0, 0)
        self.load_case_layout_y.setSpacing(0)

        self.load_case_placeholder_y = QLabel("Scanning...")
        self.load_case_placeholder_y.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.load_case_placeholder_y.setStyleSheet(f"color: {COLORS['muted']}; padding: 20px;")
        self.load_case_layout_y.addWidget(self.load_case_placeholder_y)
        self.load_case_layout_y.addStretch()

        self.load_case_scroll_y.setWidget(self.load_case_container_y)
        loadcases_y_layout.addWidget(self.load_case_scroll_y)

        data_row.addWidget(loadcases_y_group, stretch=30)

        # PROGRESS column
        progress_group = QGroupBox("Import Progress")
        progress_group.setStyleSheet(self._groupbox_style())
        progress_layout = QVBoxLayout(progress_group)
        progress_layout.setContentsMargins(8, 12, 8, 8)

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
        self.log_output.setStyleSheet(self._log_style())
        progress_layout.addWidget(self.log_output)

        data_row.addWidget(progress_group, stretch=40)

        main_layout.addLayout(data_row, stretch=1)

        # ============ BOTTOM ROW: Buttons ============
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(12)
        bottom_row.addStretch()

        self.import_btn = create_styled_button("Start Import", "primary")
        self.import_btn.clicked.connect(self.start_import)
        self.import_btn.setEnabled(False)
        bottom_row.addWidget(self.import_btn)

        cancel_btn = create_styled_button("Cancel", "ghost")
        cancel_btn.clicked.connect(self.reject)
        bottom_row.addWidget(cancel_btn)

        main_layout.addLayout(bottom_row)

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
        """

    @staticmethod
    def _entry_style() -> str:
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

    def _update_empty_state(self, line_edit: QLineEdit) -> None:
        """Update the 'empty' property based on whether the field has text."""
        is_empty = not line_edit.text().strip()
        line_edit.setProperty("empty", "true" if is_empty else "false")
        line_edit.style().unpolish(line_edit)
        line_edit.style().polish(line_edit)

    @staticmethod
    def _combo_style() -> str:
        """Style for combo box."""
        return f"""
            QComboBox {{
                background-color: {COLORS['card']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                padding: 8px;
                color: {COLORS['text']};
                font-size: 14px;
            }}
            QComboBox:hover {{
                border-color: {COLORS['accent']};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 6px solid {COLORS['text']};
                margin-right: 8px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {COLORS['card']};
                border: 1px solid {COLORS['border']};
                selection-background-color: {COLORS['accent']};
                selection-color: {COLORS['text']};
                outline: none;
            }}
        """

    def _load_existing_result_sets(self) -> bool:
        """Load existing pushover result sets.

        Returns:
            True if at least one pushover result set exists, False otherwise
        """
        from database.models import ResultSet

        result_sets = self.session.query(ResultSet).filter(
            ResultSet.project_id == self.project_id,
            ResultSet.analysis_type == "Pushover"
        ).all()

        self.existing_result_sets = [rs.name for rs in result_sets]

        return len(self.existing_result_sets) > 0

    # ------------------------------------------------------------------ #
    # Scanning
    # ------------------------------------------------------------------ #

    def start_scan(self):
        """Start background scan of folder."""
        self.scan_worker = PushoverScanWorker(self.folder_path)
        self.scan_worker.progress.connect(self.on_scan_progress)
        self.scan_worker.finished.connect(self.on_scan_finished)
        self.scan_worker.error.connect(self.on_scan_error)
        self.scan_worker.start()

    def on_scan_progress(self, message: str, current: int, total: int):
        """Handle scan progress updates."""
        self.progress_label.setText(message)
        if total > 0:
            self.progress_bar.setValue(int(100 * current / total))

    def on_scan_finished(self, results: dict):
        """Handle scan completion."""
        self.global_files = results['global_files']
        self.wall_files = results['wall_files']
        self.column_files = results.get('column_files', [])
        self.beam_files = results.get('beam_files', [])
        load_cases_x = results['load_cases_x']
        load_cases_y = results['load_cases_y']
        piers = results.get('piers', [])
        columns = results.get('columns', [])
        beams = results.get('beams', [])

        # Populate files list
        for file_path in self.global_files:
            self.files_list.addItem(f"📊 {file_path.name} (Global)")
        for file_path in self.wall_files:
            self.files_list.addItem(f"🏗️ {file_path.name} (Walls)")
        for file_path in self.column_files:
            self.files_list.addItem(f"🔧 {file_path.name} (Columns)")
        for file_path in self.beam_files:
            self.files_list.addItem(f"📏 {file_path.name} (Beams)")

        # Populate load case checkboxes
        if load_cases_x:
            self._populate_load_case_list(load_cases_x, 'X')
        if load_cases_y:
            self._populate_load_case_list(load_cases_y, 'Y')

        # Update status
        total_files = len(self.global_files) + len(self.wall_files) + len(self.column_files) + len(self.beam_files)
        self.progress_label.setText(
            f"Found {total_files} files "
            f"({len(self.global_files)} global, {len(self.wall_files)} walls, "
            f"{len(self.column_files)} columns, {len(self.beam_files)} beams)"
        )
        self.progress_bar.setValue(0)

        self.log(f"Scan complete: {len(self.global_files)} global, {len(self.wall_files)} walls, "
                 f"{len(self.column_files)} columns, {len(self.beam_files)} beams")
        self.log(f"  - {len(load_cases_x)} X load cases, {len(load_cases_y)} Y load cases")
        if piers:
            self.log(f"  - {len(piers)} piers: {', '.join(piers[:5])}{', ...' if len(piers) > 5 else ''}")
        if columns:
            self.log(f"  - {len(columns)} columns: {', '.join(columns[:5])}{', ...' if len(columns) > 5 else ''}")
        if beams:
            self.log(f"  - {len(beams)} beams: {', '.join(beams[:5])}{', ...' if len(beams) > 5 else ''}")

        # Enable import if we have data
        has_files = self.global_files or self.wall_files or self.column_files or self.beam_files
        has_load_cases = load_cases_x or load_cases_y
        if has_files and has_load_cases:
            self.import_btn.setEnabled(True)

    def on_scan_error(self, error: str):
        """Handle scan error."""
        self.progress_label.setText("Scan failed")
        self.progress_bar.setValue(0)
        self.log(f"ERROR: {error}", error=True)
        QMessageBox.warning(self, "Scan Failed", f"Failed to scan folder:\n\n{error}")

    def _populate_load_case_list(self, load_cases: List[str], direction: str):
        """Populate load case checkboxes for a direction."""
        if direction == 'X':
            layout = self.load_case_layout_x
            checkboxes_dict = self.load_case_checkboxes_x
            select_all_btn = self.select_all_x_btn
            select_none_btn = self.select_none_x_btn
        else:  # Y
            layout = self.load_case_layout_y
            checkboxes_dict = self.load_case_checkboxes_y
            select_all_btn = self.select_all_y_btn
            select_none_btn = self.select_none_y_btn

        # Clear placeholder
        while layout.count() > 0:
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Create checkmark image
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
        checkmark_path = os.path.join(temp_dir, f"rps_checkbox_check_{direction}.png")
        checkmark_pixmap.save(checkmark_path, "PNG")
        checkmark_url = checkmark_path.replace("\\", "/")

        # Add checkboxes
        for lc in load_cases:
            checkbox = QCheckBox(lc)
            checkbox.setChecked(True)  # All selected by default

            checkbox.setStyleSheet(f"""
                QCheckBox {{
                    color: {COLORS['text']};
                    font-size: 13px;
                    padding: 6px 8px;
                    spacing: 8px;
                }}
                QCheckBox::indicator {{
                    width: 18px;
                    height: 18px;
                    border: 2px solid {COLORS['border']};
                    border-radius: 3px;
                    background-color: {COLORS['background']};
                }}
                QCheckBox::indicator:hover {{
                    border-color: {COLORS['accent']};
                    background-color: {COLORS['card']};
                }}
                QCheckBox::indicator:checked {{
                    background-color: {COLORS['accent']};
                    border-color: {COLORS['accent']};
                    image: url({checkmark_url});
                }}
                QCheckBox::indicator:checked:hover {{
                    background-color: #5a99a8;
                    border-color: #5a99a8;
                    image: url({checkmark_url});
                }}
                QCheckBox:hover {{
                    background-color: rgba(255, 255, 255, 0.03);
                    border-radius: 4px;
                }}
            """)

            layout.addWidget(checkbox)
            checkboxes_dict[lc] = checkbox

        layout.addStretch()

        # Enable buttons
        select_all_btn.setEnabled(True)
        select_none_btn.setEnabled(True)

    def _select_all_x(self):
        """Select all X direction load cases."""
        for checkbox in self.load_case_checkboxes_x.values():
            checkbox.setChecked(True)

    def _select_none_x(self):
        """Deselect all X direction load cases."""
        for checkbox in self.load_case_checkboxes_x.values():
            checkbox.setChecked(False)

    def _select_all_y(self):
        """Select all Y direction load cases."""
        for checkbox in self.load_case_checkboxes_y.values():
            checkbox.setChecked(True)

    def _select_none_y(self):
        """Deselect all Y direction load cases."""
        for checkbox in self.load_case_checkboxes_y.values():
            checkbox.setChecked(False)

    def log(self, message: str, error: bool = False, warning: bool = False):
        """Add message to log."""
        if error:
            color = "#ef4444"
        elif warning:
            color = "#f59e0b"
        else:
            color = COLORS['muted']

        self.log_output.append(f'<span style="color: {color};">{message}</span>')

    # ------------------------------------------------------------------ #
    # Import
    # ------------------------------------------------------------------ #

    def start_import(self):
        """Start the import process."""
        result_set_name = self.result_set_combo.currentText()

        if not result_set_name:
            QMessageBox.warning(self, "Missing Information", "Please select a result set.")
            return

        # Get selected load cases
        selected_x = [lc for lc, cb in self.load_case_checkboxes_x.items() if cb.isChecked()]
        selected_y = [lc for lc, cb in self.load_case_checkboxes_y.items() if cb.isChecked()]

        if not selected_x and not selected_y:
            QMessageBox.warning(self, "No Load Cases Selected", "Please select at least one load case to import.")
            return

        # Disable UI during import
        self.import_btn.setEnabled(False)
        self.result_set_combo.setEnabled(False)

        # Disable all checkboxes
        for cb in self.load_case_checkboxes_x.values():
            cb.setEnabled(False)
        for cb in self.load_case_checkboxes_y.values():
            cb.setEnabled(False)

        self.log(f"Starting import: {result_set_name}")
        self.log(f"  - Files: {len(self.global_files)} global, {len(self.wall_files)} walls, "
                 f"{len(self.column_files)} columns, {len(self.beam_files)} beams")
        self.log(f"  - X direction: {len(selected_x)} load cases")
        self.log(f"  - Y direction: {len(selected_y)} load cases")

        # Start import worker
        self.import_worker = PushoverImportWorker(
            project_id=self.project_id,
            session=self.session,
            folder_path=self.folder_path,
            result_set_name=result_set_name,
            global_files=self.global_files,
            wall_files=self.wall_files,
            column_files=self.column_files,
            beam_files=self.beam_files,
            selected_load_cases_x=selected_x,
            selected_load_cases_y=selected_y,
        )

        self.import_worker.progress.connect(self.on_import_progress)
        self.import_worker.finished.connect(self.on_import_finished)
        self.import_worker.error.connect(self.on_import_error)
        self.import_worker.start()

    def on_import_progress(self, message: str, current: int, total: int):
        """Handle import progress updates."""
        self.progress_label.setText(message)
        if total > 0:
            self.progress_bar.setValue(int(100 * current / total))
        self.log(message)

    def on_import_finished(self, stats: dict):
        """Handle import completion."""
        self.progress_label.setText("Import complete!")
        self.progress_bar.setValue(100)

        # Log results
        self.log("=" * 50, warning=False)
        self.log(f"✓ Import complete!", warning=False)
        self.log(f"Files processed: {stats.get('files_processed', 0)}")

        # Global results
        if stats.get('x_drifts') or stats.get('y_drifts'):
            self.log(f"Global Results:")
            self.log(f"  X: {stats.get('x_drifts', 0)} drifts, {stats.get('x_displacements', 0)} displ, {stats.get('x_forces', 0)} forces")
            self.log(f"  Y: {stats.get('y_drifts', 0)} drifts, {stats.get('y_displacements', 0)} displ, {stats.get('y_forces', 0)} forces")

        # Wall results
        if stats.get('x_v2_shears') or stats.get('x_rotations'):
            self.log(f"Wall Results:")
            self.log(f"  X: {stats.get('x_v2_shears', 0)} V2 shears, {stats.get('x_v3_shears', 0)} V3 shears, {stats.get('x_rotations', 0)} rotations")
            self.log(f"  Y: {stats.get('y_v2_shears', 0)} V2 shears, {stats.get('y_v3_shears', 0)} V3 shears, {stats.get('y_rotations', 0)} rotations")

        # Column results
        if stats.get('x_r2_rotations') or stats.get('y_r2_rotations'):
            self.log(f"Column Results:")
            self.log(f"  X: {stats.get('x_r2_rotations', 0)} R2 rotations, {stats.get('x_r3_rotations', 0)} R3 rotations")
            self.log(f"  Y: {stats.get('y_r2_rotations', 0)} R2 rotations, {stats.get('y_r3_rotations', 0)} R3 rotations")

        # Beam results (beam stats use 'x_rotations' and 'y_rotations', but these may conflict with wall rotations)
        # Wall importer also uses x_rotations/y_rotations, so we check if it's beam-specific
        # For now, we'll include them in a separate section if files were processed
        if self.beam_files and (stats.get('x_rotations') or stats.get('y_rotations')):
            # Note: This may double-count if wall_files also present
            # Beam rotations are already counted in x_rotations from walls
            pass

        # Joint results
        if stats.get('x_ux_displacements') or stats.get('y_ux_displacements'):
            self.log(f"Joint Displacements:")
            self.log(f"  X: {stats.get('x_ux_displacements', 0)} Ux, {stats.get('x_uy_displacements', 0)} Uy, {stats.get('x_uz_displacements', 0)} Uz")
            self.log(f"  Y: {stats.get('y_ux_displacements', 0)} Ux, {stats.get('y_uy_displacements', 0)} Uy, {stats.get('y_uz_displacements', 0)} Uz")

        if stats.get('errors'):
            self.log(f"Errors: {len(stats['errors'])}", error=True)
            for error in stats['errors']:
                self.log(f"  - {error}", error=True)

        # Emit completion signal
        self.import_completed.emit(stats)

        # Show success message
        total_records = (
            stats.get('x_drifts', 0) + stats.get('y_drifts', 0) +
            stats.get('x_displacements', 0) + stats.get('y_displacements', 0) +
            stats.get('x_forces', 0) + stats.get('y_forces', 0) +
            stats.get('x_v2_shears', 0) + stats.get('y_v2_shears', 0) +
            stats.get('x_v3_shears', 0) + stats.get('y_v3_shears', 0) +
            stats.get('x_r2_rotations', 0) + stats.get('y_r2_rotations', 0) +
            stats.get('x_r3_rotations', 0) + stats.get('y_r3_rotations', 0)
        )

        QMessageBox.information(
            self,
            "Import Complete",
            f"Successfully imported pushover results!\n\n"
            f"Files: {stats.get('files_processed', 0)}\n"
            f"Total records: {total_records}"
        )

        self.accept()

    def on_import_error(self, error: str):
        """Handle import error."""
        self.progress_label.setText("Import failed")
        self.progress_bar.setValue(0)
        self.log(f"ERROR: {error}", error=True)

        # Re-enable UI
        self.import_btn.setEnabled(True)
        self.result_set_combo.setEnabled(True)
        for cb in self.load_case_checkboxes_x.values():
            cb.setEnabled(True)
        for cb in self.load_case_checkboxes_y.values():
            cb.setEnabled(True)

        QMessageBox.critical(
            self,
            "Import Failed",
            f"Failed to import pushover global results:\n\n{error}"
        )
