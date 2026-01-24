"""Worker threads for pushover global results import."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable, List

from PyQt6.QtCore import QThread, pyqtSignal

logger = logging.getLogger(__name__)


class PushoverImportWorker(QThread):
    """Worker thread for importing pushover data (global + elements).

    Thread Safety: Creates its own session using the provided session_factory to ensure
    thread-safe database access. Never shares a session with the main UI thread.
    """

    progress = pyqtSignal(str, int, int)  # message, current, total
    finished = pyqtSignal(dict)  # stats
    error = pyqtSignal(str)  # error message

    def __init__(
        self,
        project_id: int,
        session_factory: Callable[[], object],
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
        self.session_factory = session_factory
        self.folder_path = folder_path
        self.result_set_name = result_set_name
        self.global_files = global_files
        self.wall_files = wall_files
        self.column_files = column_files
        self.beam_files = beam_files
        self.selected_load_cases_x = selected_load_cases_x
        self.selected_load_cases_y = selected_load_cases_y

    def run(self):
        """Run import in background thread with thread-safe session."""
        from processing.pushover_global_importer import (
            PushoverGlobalImporter,
            ensure_pushover_result_set,
        )
        from processing.pushover_wall_importer_v2 import PushoverWallImporter
        from processing.pushover_column_importer_v2 import PushoverColumnImporter
        from processing.pushover_column_shear_importer_v2 import PushoverColumnShearImporter
        from processing.pushover_beam_importer_v2 import PushoverBeamImporter

        try:
            session = self.session_factory()
            try:
                combined_stats = {}

                # Import global results if present
                if self.global_files:
                    self.progress.emit("Importing global results...", 10, 100)

                    global_importer = PushoverGlobalImporter(
                        project_id=self.project_id,
                        session=session,
                        folder_path=self.folder_path,
                        result_set_name=self.result_set_name,
                        valid_files=self.global_files,
                        selected_load_cases_x=self.selected_load_cases_x,
                        selected_load_cases_y=self.selected_load_cases_y,
                        progress_callback=lambda msg, curr, total: self._on_progress(
                            f"Global: {msg}",
                            curr // 2,
                            100,
                        ),
                    )

                    global_stats = global_importer.import_all()
                    combined_stats.update(global_stats)

                # Get the result set ID (created by global import or need to create)
                result_set = ensure_pushover_result_set(
                    session,
                    self.project_id,
                    self.result_set_name,
                )

                # Import wall results if present
                if self.wall_files:
                    self.progress.emit("Importing wall results...", 50, 100)

                    for wall_file in self.wall_files:
                        wall_importer = PushoverWallImporter(
                            project_id=self.project_id,
                            session=session,
                            result_set_id=result_set.id,
                            file_path=wall_file,
                            selected_load_cases_x=self.selected_load_cases_x,
                            selected_load_cases_y=self.selected_load_cases_y,
                            progress_callback=lambda msg, curr, total: self._on_progress(
                                f"Walls: {msg}",
                                50 + curr // 6,
                                100,
                            ),
                        )

                        wall_stats = wall_importer.import_all()
                        self._merge_stats(combined_stats, wall_stats)

                # Import column results if present
                if self.column_files:
                    self.progress.emit("Importing column rotations...", 70, 100)

                    for column_file in self.column_files:
                        column_importer = PushoverColumnImporter(
                            project_id=self.project_id,
                            session=session,
                            result_set_id=result_set.id,
                            file_path=column_file,
                            selected_load_cases_x=self.selected_load_cases_x,
                            selected_load_cases_y=self.selected_load_cases_y,
                            progress_callback=lambda msg, curr, total: self._on_progress(
                                f"Column Rotations: {msg}",
                                70 + curr // 8,
                                100,
                            ),
                        )

                        column_stats = column_importer.import_all()
                        self._merge_stats(combined_stats, column_stats)

                    # Also import column shears from the same files
                    self.progress.emit("Importing column shears...", 75, 100)

                    for column_file in self.column_files:
                        column_shear_importer = PushoverColumnShearImporter(
                            project_id=self.project_id,
                            session=session,
                            result_set_id=result_set.id,
                            file_path=column_file,
                            selected_load_cases_x=self.selected_load_cases_x,
                            selected_load_cases_y=self.selected_load_cases_y,
                            progress_callback=lambda msg, curr, total: self._on_progress(
                                f"Column Shears: {msg}",
                                75 + curr // 8,
                                100,
                            ),
                        )

                        shear_stats = column_shear_importer.import_all()
                        self._merge_stats(combined_stats, shear_stats)

                # Import beam results if present
                if self.beam_files:
                    self.progress.emit("Importing beam results...", 80, 100)

                    for beam_file in self.beam_files:
                        beam_importer = PushoverBeamImporter(
                            project_id=self.project_id,
                            session=session,
                            result_set_id=result_set.id,
                            file_path=beam_file,
                            selected_load_cases_x=self.selected_load_cases_x,
                            selected_load_cases_y=self.selected_load_cases_y,
                            progress_callback=lambda msg, curr, total: self._on_progress(
                                f"Beams: {msg}",
                                80 + curr // 8,
                                100,
                            ),
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
                            session=session,
                            result_set_id=result_set.id,
                            file_path=joint_file,
                            selected_load_cases_x=self.selected_load_cases_x,
                            selected_load_cases_y=self.selected_load_cases_y,
                            progress_callback=lambda msg, curr, total: self._on_progress(
                                f"Joints: {msg}",
                                85 + curr // 20,
                                100,
                            ),
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
                            session=session,
                            result_set_id=result_set.id,
                            file_path=soil_file,
                            selected_load_cases_x=self.selected_load_cases_x,
                            selected_load_cases_y=self.selected_load_cases_y,
                            progress_callback=lambda msg, curr, total: self._on_progress(
                                f"Soil Pressures: {msg}",
                                90 + curr // 20,
                                100,
                            ),
                        )

                        soil_stats = soil_importer.import_all()
                        self._merge_stats(combined_stats, soil_stats)

                # Import vertical displacements if present (from global results files)
                if self.global_files:
                    from processing.pushover_vert_displacement_importer import (
                        PushoverVertDisplacementImporter,
                    )

                    self.progress.emit("Importing vertical displacements...", 95, 100)

                    for vert_file in self.global_files:
                        vert_importer = PushoverVertDisplacementImporter(
                            project_id=self.project_id,
                            session=session,
                            result_set_id=result_set.id,
                            file_path=vert_file,
                            selected_load_cases_x=self.selected_load_cases_x,
                            selected_load_cases_y=self.selected_load_cases_y,
                            progress_callback=lambda msg, curr, total: self._on_progress(
                                f"Vert Displ: {msg}",
                                95 + curr // 20,
                                100,
                            ),
                        )

                        vert_stats = vert_importer.import_all()
                        self._merge_stats(combined_stats, vert_stats)

                session.commit()
            finally:
                session.close()

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
                        if "X" in directions:
                            cases_x = parser.get_output_cases("X")
                            all_load_cases_x.update(cases_x)

                        if "Y" in directions:
                            cases_y = parser.get_output_cases("Y")
                            all_load_cases_y.update(cases_y)

                except Exception:
                    logger.debug("Not a global results file: %s", file_path.name)

                # Try parsing as wall results
                try:
                    wall_parser = PushoverWallParser(file_path)
                    directions = wall_parser.get_available_directions()

                    if directions:
                        wall_files.append(file_path)

                        # Extract load cases for each direction
                        if "X" in directions:
                            cases_x = wall_parser.get_output_cases("X")
                            all_load_cases_x.update(cases_x)

                        if "Y" in directions:
                            cases_y = wall_parser.get_output_cases("Y")
                            all_load_cases_y.update(cases_y)

                        # Extract piers
                        piers = wall_parser.get_piers()
                        all_piers.update(piers)

                except Exception:
                    logger.debug("Not a wall results file: %s", file_path.name)

                # Try parsing as column results
                try:
                    column_parser = PushoverColumnParser(file_path)
                    directions = column_parser.get_available_directions()

                    if directions:
                        column_files.append(file_path)

                        # Extract load cases for each direction
                        if "X" in directions:
                            cases_x = column_parser.get_output_cases("X")
                            all_load_cases_x.update(cases_x)

                        if "Y" in directions:
                            cases_y = column_parser.get_output_cases("Y")
                            all_load_cases_y.update(cases_y)

                        # Extract columns
                        columns = column_parser.get_columns()
                        all_columns.update(columns)

                except Exception:
                    logger.debug("Not a column results file: %s", file_path.name)

                # Try parsing as beam results
                try:
                    beam_parser = PushoverBeamParser(file_path)
                    directions = beam_parser.get_available_directions()

                    if directions:
                        beam_files.append(file_path)

                        # Extract load cases for each direction
                        if "X" in directions:
                            cases_x = beam_parser.get_output_cases("X")
                            all_load_cases_x.update(cases_x)

                        if "Y" in directions:
                            cases_y = beam_parser.get_output_cases("Y")
                            all_load_cases_y.update(cases_y)

                        # Extract beams
                        beams = beam_parser.get_beams()
                        all_beams.update(beams)

                except Exception:
                    logger.debug("Not a beam results file: %s", file_path.name)

            if not global_files and not wall_files and not column_files and not beam_files:
                self.error.emit("No valid pushover results files found in folder")
                return

            # Return results
            results = {
                "global_files": global_files,
                "wall_files": wall_files,
                "column_files": column_files,
                "beam_files": beam_files,
                "load_cases_x": sorted(all_load_cases_x),
                "load_cases_y": sorted(all_load_cases_y),
                "piers": sorted(all_piers),
                "columns": sorted(all_columns),
                "beams": sorted(all_beams),
            }

            self.finished.emit(results)

        except Exception as e:
            self.error.emit(str(e))
