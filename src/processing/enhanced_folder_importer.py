"""Enhanced folder importer with load case selection and conflict resolution."""

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from PyQt6.QtWidgets import QWidget
from sqlalchemy.orm import Session

from database.repository import ProjectRepository, LoadCaseRepository, StoryRepository

from .excel_parser import ExcelParser
from .data_importer import DataImporter
from .selective_data_importer import SelectiveDataImporter
from .folder_importer import TARGET_SHEETS
from .base_importer import BaseFolderImporter

from gui.load_case_selection_dialog import LoadCaseSelectionDialog
from gui.load_case_conflict_dialog import LoadCaseConflictDialog


class EnhancedFolderImporter(BaseFolderImporter):
    """
    Enhanced folder importer with load case selection and conflict resolution.

    Workflow:
    1. Pre-scan all files to discover load cases
    2. Show selection dialog for user to choose which load cases to import
    3. Detect conflicts in selected load cases
    4. Show conflict resolution dialog if needed
    5. Import with user's selections and resolutions applied
    """

    def __init__(
        self,
        folder_path: str,
        project_name: str,
        result_set_name: str,
        result_types: Optional[List[str]] = None,
        session_factory: Optional[Callable[[], Session]] = None,
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
        parent_widget: Optional[QWidget] = None,
        selected_load_cases: Optional[Set[str]] = None,
        conflict_resolution: Optional[Dict[str, Dict[str, Optional[str]]]] = None,
    ):
        """
        Initialize enhanced folder importer.

        Args:
            folder_path: Path to folder containing Excel files
            project_name: Name of project to import into
            result_set_name: Name of result set
            result_types: Optional list of result type labels to filter
            session_factory: Factory function to create database sessions
            progress_callback: Optional callback for progress updates
            parent_widget: Parent widget for dialogs
            selected_load_cases: Pre-selected load cases (if None, all will be imported)
            conflict_resolution: Sheet-based conflict resolution {sheet: {load_case: file}}
        """
        super().__init__(
            folder_path=folder_path,
            result_types=result_types,
            session_factory=session_factory,
            progress_callback=progress_callback,
        )
        self.project_name = project_name
        self.result_set_name = result_set_name
        self.parent_widget = parent_widget
        self.selected_load_cases = selected_load_cases
        self.conflict_resolution = conflict_resolution or {}

    @staticmethod
    def prescan_folder_for_load_cases(
        folder_path: Path,
        result_types: Optional[Set[str]] = None,
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> Dict[str, Dict[str, List[str]]]:
        """
        Static method to pre-scan a folder for load cases.
        Can be called from main thread before creating worker.

        Args:
            folder_path: Path to folder
            result_types: Optional set of result types to filter
            progress_callback: Optional progress callback

        Returns:
            Dict of file → sheet → load_cases
        """
        files: List[Path] = []
        for pattern in ("*.xlsx", "*.xls"):
            files.extend(folder_path.glob(pattern))
        excel_files = sorted(f for f in files if not f.name.startswith("~$"))

        file_load_cases = {}

        for idx, file_path in enumerate(excel_files):
            if progress_callback:
                progress_callback(
                    f"Scanning {file_path.name}...",
                    idx,
                    len(excel_files)
                )

            try:
                parser = ExcelParser(str(file_path))
                load_cases_by_sheet = {}

                # Scan each result type
                sheets_found = []
                sheets_errored = []
                for sheet_name, result_labels in TARGET_SHEETS.items():
                    # Check if we should import this result type
                    if result_types is not None:
                        should_import_any = any(
                            label.strip().lower() in result_types for label in result_labels
                        )
                        if not should_import_any:
                            continue

                    if not parser.validate_sheet_exists(sheet_name):
                        continue

                    # Get load cases from this sheet
                    try:
                        load_cases = EnhancedFolderImporter._extract_load_cases_from_sheet_static(
                            parser, sheet_name
                        )
                        if load_cases:
                            load_cases_by_sheet[sheet_name] = load_cases
                            sheets_found.append(f"{sheet_name}({len(load_cases)})")
                    except Exception as e:
                        # Log error and skip problematic sheets
                        sheets_errored.append(f"{sheet_name}: {str(e)[:30]}")
                        continue

                # Log what was found/errored for this file
                if progress_callback and (sheets_found or sheets_errored):
                    if sheets_found:
                        progress_callback(
                            f"  ✓ {', '.join(sheets_found[:3])}{'...' if len(sheets_found) > 3 else ''}",
                            idx,
                            len(excel_files)
                        )
                    if sheets_errored:
                        progress_callback(
                            f"  ✗ {sheets_errored[0]}",
                            idx,
                            len(excel_files)
                        )

                if load_cases_by_sheet:
                    file_load_cases[file_path.name] = load_cases_by_sheet

            except Exception:
                # Skip problematic files
                continue

        return file_load_cases

    @staticmethod
    def _extract_load_cases_from_sheet_static(
        parser: ExcelParser, sheet_name: str
    ) -> List[str]:
        """Static version of _extract_load_cases_from_sheet."""
        if sheet_name == "Story Drifts":
            _, load_cases, _ = parser.get_story_drifts()
            return load_cases
        elif sheet_name == "Diaphragm Accelerations":
            _, load_cases, _ = parser.get_story_accelerations()
            return load_cases
        elif sheet_name == "Story Forces":
            _, load_cases, _ = parser.get_story_forces()
            return load_cases
        elif sheet_name == "Joint DisplacementsG":
            _, load_cases, _ = parser.get_joint_displacements()
            return load_cases
        elif sheet_name == "Pier Forces":
            _, load_cases, _, _ = parser.get_pier_forces()
            return load_cases
        elif sheet_name == "Element Forces - Columns":
            _, load_cases, _, _ = parser.get_column_forces()
            return load_cases
        elif sheet_name == "Fiber Hinge States":
            _, load_cases, _, _ = parser.get_fiber_hinge_states()
            return load_cases
        elif sheet_name == "Hinge States":
            _, load_cases, _, _ = parser.get_hinge_states()
            return load_cases
        elif sheet_name == "Quad Strain Gauge - Rotation":
            _, load_cases, _, _ = parser.get_quad_rotations()
            return load_cases
        else:
            return []

    def import_all(self) -> Dict[str, Any]:
        """
        Import with load case selection and conflict resolution.

        Returns:
            Dictionary with import statistics
        """
        if not self.excel_files:
            raise ValueError(f"No Excel files found in folder: {self.folder_path}")

        # Phase 1: Pre-scan all files for load cases
        self._report_progress("Scanning files for load cases...", 0, len(self.excel_files))
        file_load_cases = self._prescan_load_cases()

        if not file_load_cases:
            return {
                "project": None,
                "files_processed": 0,
                "files_total": len(self.excel_files),
                "load_cases": 0,
                "errors": ["No load cases found in any files"]
            }

        # Use pre-selected load cases if provided (from main thread)
        if self.selected_load_cases is None:
            # No pre-selection, import all
            selected_load_cases = set()
            for file_data in file_load_cases.values():
                for load_cases in file_data.values():
                    selected_load_cases.update(load_cases)
        else:
            selected_load_cases = self.selected_load_cases

        # Phase 5: Import with selections and resolutions
        return self._import_with_selection_and_resolution(
            file_load_cases, selected_load_cases, self.conflict_resolution
        )

    def _prescan_load_cases(self) -> Dict[str, Dict[str, List[str]]]:
        """
        Pre-scan all files to collect load cases.

        Returns:
            {
                "file1.xlsx": {
                    "Story Drifts": ["DES_X", "DES_Y", "MCE_X"],
                    "Story Forces": ["DES_X", "DES_Y", "MCE_X"],
                },
                "file2.xlsx": {
                    "Story Drifts": ["SLE_X", "SLE_Y"],
                }
            }
        """
        file_load_cases = {}

        for idx, file_path in enumerate(self.excel_files):
            self._report_progress(
                f"Scanning {file_path.name}...",
                idx,
                len(self.excel_files)
            )

            try:
                parser = ExcelParser(str(file_path))
                load_cases_by_sheet = {}

                # Scan each result type
                sheets_found = []
                sheets_errored = []
                for sheet_name, result_labels in TARGET_SHEETS.items():
                    # Check if we should import this result type
                    should_import_any = any(
                        self._should_import(label) for label in result_labels
                    )
                    if not should_import_any:
                        continue

                    if not parser.validate_sheet_exists(sheet_name):
                        continue

                    # Get load cases from this sheet
                    try:
                        load_cases = self._extract_load_cases_from_sheet(
                            parser, sheet_name
                        )
                        if load_cases:
                            load_cases_by_sheet[sheet_name] = load_cases
                            sheets_found.append(f"{sheet_name}({len(load_cases)})")
                    except Exception as e:
                        # Log error and skip problematic sheets
                        sheets_errored.append(f"{sheet_name}: {str(e)[:30]}")
                        continue

                # Log what was found/errored for this file
                if sheets_found:
                    self._report_progress(
                        f"  ✓ {', '.join(sheets_found[:3])}{'...' if len(sheets_found) > 3 else ''}",
                        idx,
                        len(self.excel_files)
                    )
                if sheets_errored:
                    self._report_progress(
                        f"  ✗ {sheets_errored[0]}",
                        idx,
                        len(self.excel_files)
                    )

                if load_cases_by_sheet:
                    file_load_cases[file_path.name] = load_cases_by_sheet

            except Exception:
                # Skip problematic files
                continue

        return file_load_cases

    def _extract_load_cases_from_sheet(
        self, parser: ExcelParser, sheet_name: str
    ) -> List[str]:
        """Extract load case names from a sheet (fast scan without full data)."""
        if sheet_name == "Story Drifts":
            _, load_cases, _ = parser.get_story_drifts()
            return load_cases
        elif sheet_name == "Diaphragm Accelerations":
            _, load_cases, _ = parser.get_story_accelerations()
            return load_cases
        elif sheet_name == "Story Forces":
            _, load_cases, _ = parser.get_story_forces()
            return load_cases
        elif sheet_name == "Joint DisplacementsG":
            _, load_cases, _ = parser.get_joint_displacements()
            return load_cases
        elif sheet_name == "Pier Forces":
            _, load_cases, _, _ = parser.get_pier_forces()
            return load_cases
        elif sheet_name == "Element Forces - Columns":
            _, load_cases, _, _ = parser.get_column_forces()
            return load_cases
        elif sheet_name == "Fiber Hinge States":
            _, load_cases, _, _ = parser.get_fiber_hinge_states()
            return load_cases
        elif sheet_name == "Hinge States":
            _, load_cases, _, _ = parser.get_hinge_states()
            return load_cases
        elif sheet_name == "Quad Strain Gauge - Rotation":
            _, load_cases, _, _ = parser.get_quad_rotations()
            return load_cases
        else:
            return []

    def _select_load_cases_interactive(
        self,
        file_load_cases: Dict[str, Dict[str, List[str]]]
    ) -> Optional[Set[str]]:
        """
        Show UI for user to select which load cases to import.

        Returns:
            Set of selected load case names, or None if cancelled
        """
        # Collect all unique load cases across all files
        all_load_cases = set()
        load_case_sources = {}  # load_case → [(file, sheet), ...]

        for file_name, sheets in file_load_cases.items():
            for sheet_name, load_cases in sheets.items():
                for lc in load_cases:
                    all_load_cases.add(lc)
                    if lc not in load_case_sources:
                        load_case_sources[lc] = []
                    load_case_sources[lc].append((file_name, sheet_name))

        # Show selection dialog
        dialog = LoadCaseSelectionDialog(
            all_load_cases,
            load_case_sources,
            self.result_set_name,
            self.parent_widget
        )

        if dialog.exec():
            return dialog.get_selected_load_cases()
        else:
            return None

    @staticmethod
    def detect_conflicts_in_selection(
        file_load_cases: Dict[str, Dict[str, List[str]]],
        selected_load_cases: Set[str]
    ) -> Dict[str, Dict[str, List[str]]]:
        """
        Detect conflicts only among selected load cases.
        Static method that can be called from main thread.

        Returns:
            {
                "DES_X": {
                    "Story Drifts": ["file1.xlsx", "file2.xlsx"],
                    "Story Forces": ["file1.xlsx", "file2.xlsx"]
                }
            }
        """
        conflicts = {}

        # Group by sheet type
        sheet_types = set()
        for file_data in file_load_cases.values():
            sheet_types.update(file_data.keys())

        for sheet_name in sheet_types:
            lc_files = {}  # load_case → list of files

            for file_name, sheets in file_load_cases.items():
                if sheet_name not in sheets:
                    continue

                for load_case in sheets[sheet_name]:
                    # Only check selected load cases
                    if load_case not in selected_load_cases:
                        continue

                    if load_case not in lc_files:
                        lc_files[load_case] = []
                    lc_files[load_case].append(file_name)

            # Find duplicates
            for load_case, files in lc_files.items():
                if len(files) > 1:
                    if load_case not in conflicts:
                        conflicts[load_case] = {}
                    conflicts[load_case][sheet_name] = files

        return conflicts

    def _detect_conflicts_in_selection(
        self,
        file_load_cases: Dict[str, Dict[str, List[str]]],
        selected_load_cases: Set[str]
    ) -> Dict[str, Dict[str, List[str]]]:
        """
        Detect conflicts only among selected load cases.

        Returns:
            {
                "DES_X": {
                    "Story Drifts": ["file1.xlsx", "file2.xlsx"],
                    "Story Forces": ["file1.xlsx", "file2.xlsx"]
                }
            }
        """
        return self.detect_conflicts_in_selection(file_load_cases, selected_load_cases)

    def _resolve_conflicts_interactive(
        self,
        conflicts: Dict[str, Dict[str, List[str]]]
    ) -> Optional[Dict[str, Optional[str]]]:
        """
        Show UI for user to resolve conflicts.

        Returns:
            Dict mapping load_case → chosen_file (or None to skip),
            or None if cancelled
        """
        dialog = LoadCaseConflictDialog(conflicts, self.parent_widget)

        if dialog.exec():
            return dialog.get_resolution()
        else:
            return None

    def _import_with_selection_and_resolution(
        self,
        file_load_cases: Dict[str, Dict[str, List[str]]],
        selected_load_cases: Set[str],
        resolution: Dict[str, Dict[str, Optional[str]]]
    ) -> Dict[str, Any]:
        """
        Import files with load case selection and conflict resolution applied (sheet-aware).
        """
        stats = {
            "project": None,
            "files_processed": 0,
            "files_total": len(self.excel_files),
            "load_cases": 0,
            "load_cases_skipped": 0,
            "stories": 0,
            "drifts": 0,
            "accelerations": 0,
            "forces": 0,
            "displacements": 0,
            "pier_forces": 0,
            "column_forces": 0,
            "errors": [],
        }

        # Track which load cases have been imported per sheet
        imported_load_cases_by_sheet = {}  # {sheet: {load_cases}}

        # Import each file
        for idx, file_path in enumerate(self.excel_files):
            file_name = file_path.name

            # Skip if file has no load cases in our scan
            if file_name not in file_load_cases:
                continue

            self._report_progress(
                f"Importing {file_name}...",
                idx,
                len(self.excel_files)
            )

            # Determine which load cases to import from this file
            allowed_load_cases = self._get_allowed_load_cases(
                file_name,
                file_load_cases[file_name],
                selected_load_cases,
                resolution,
                imported_load_cases_by_sheet
            )

            if not allowed_load_cases:
                # No load cases to import from this file
                self._report_progress(
                    f"  Skipping {file_name} (no allowed load cases)",
                    idx,
                    len(self.excel_files)
                )
                continue

            # Debug: Log what we're importing from this file
            self._report_progress(
                f"  Importing {len(allowed_load_cases)} load case(s): {', '.join(sorted(allowed_load_cases)[:3])}{'...' if len(allowed_load_cases) > 3 else ''}",
                idx,
                len(self.excel_files)
            )

            # Import file with load case filtering
            try:
                # Use SelectiveDataImporter to only import allowed load cases
                # Convert result_types set back to list for DataImporter
                result_types_list = list(self.result_types) if self.result_types else None

                importer = SelectiveDataImporter(
                    file_path=str(file_path),
                    project_name=self.project_name,
                    result_set_name=self.result_set_name,
                    allowed_load_cases=allowed_load_cases,
                    result_types=result_types_list,  # Pass result types filter
                    session_factory=self._session_factory,
                )
                file_stats = importer.import_all()

                # Aggregate stats
                stats["project"] = file_stats.get("project", stats["project"])
                stats["files_processed"] += 1
                stats["drifts"] += file_stats.get("drifts", 0)
                stats["accelerations"] += file_stats.get("accelerations", 0)
                stats["forces"] += file_stats.get("forces", 0)
                stats["displacements"] += file_stats.get("displacements", 0)
                stats["pier_forces"] += file_stats.get("pier_forces", 0)
                stats["column_forces"] += file_stats.get("column_forces", 0)

                # Track imported load cases per sheet
                for sheet_name in file_load_cases[file_name].keys():
                    if sheet_name not in imported_load_cases_by_sheet:
                        imported_load_cases_by_sheet[sheet_name] = set()
                    # Add load cases from this sheet that were allowed
                    sheet_load_cases = set(file_load_cases[file_name][sheet_name])
                    imported_load_cases_by_sheet[sheet_name].update(
                        allowed_load_cases & sheet_load_cases
                    )

            except Exception as e:
                stats["errors"].append(f"{file_name}: {str(e)}")

        # Get final load case and story counts
        if stats["project"]:
            session = self._session_factory()
            try:
                project_repo = ProjectRepository(session)
                project = project_repo.get_by_name(self.project_name)
                if project:
                    load_cases = LoadCaseRepository(session).get_by_project(project.id)
                    stories = StoryRepository(session).get_by_project(project.id)
                    stats["load_cases"] = len(load_cases)
                    stats["stories"] = len(stories)
            finally:
                session.close()

        self._report_progress("Import complete", len(self.excel_files), len(self.excel_files))
        return stats

    def _get_allowed_load_cases(
        self,
        file_name: str,
        file_sheets: Dict[str, List[str]],
        selected_load_cases: Set[str],
        resolution: Dict[str, Dict[str, Optional[str]]],
        already_imported: Dict[str, Set[str]]
    ) -> Set[str]:
        """
        Determine which load cases to import from this file (sheet-aware).

        Args:
            file_name: Name of current file
            file_sheets: Load cases in this file (by sheet)
            selected_load_cases: User-selected load cases
            resolution: Sheet-based conflict resolution {sheet: {load_case: file}}
            already_imported: Load cases already imported by sheet {sheet: {load_cases}}

        Returns:
            Set of load case names to import from this file
        """
        allowed = set()
        skipped_by_sheet = {}  # Track what was skipped for debugging

        # Process sheet by sheet to handle per-sheet conflicts
        for sheet_name, load_cases_in_sheet in file_sheets.items():
            for load_case in load_cases_in_sheet:
                # Skip if not selected by user
                if load_case not in selected_load_cases:
                    continue

                # Check if this sheet has conflict resolution for this load case
                if sheet_name in resolution and load_case in resolution[sheet_name]:
                    chosen_file = resolution[sheet_name][load_case]

                    if chosen_file is None:
                        # User chose to skip this load case for this sheet
                        if sheet_name not in skipped_by_sheet:
                            skipped_by_sheet[sheet_name] = []
                        skipped_by_sheet[sheet_name].append(f"{load_case} (user skipped)")
                        continue
                    elif chosen_file == file_name:
                        # User chose this file for this load case on this sheet
                        allowed.add(load_case)
                    else:
                        # User chose a different file
                        if sheet_name not in skipped_by_sheet:
                            skipped_by_sheet[sheet_name] = []
                        skipped_by_sheet[sheet_name].append(f"{load_case} (using {chosen_file})")

                else:
                    # No conflict for this sheet+load_case combo
                    # Check if already imported from another file FOR THIS SHEET
                    if sheet_name not in already_imported or load_case not in already_imported[sheet_name]:
                        # This load case hasn't been imported for this sheet yet
                        allowed.add(load_case)
                    else:
                        # Already imported from another file
                        if sheet_name not in skipped_by_sheet:
                            skipped_by_sheet[sheet_name] = []
                        skipped_by_sheet[sheet_name].append(f"{load_case} (already imported)")

        # Debug logging
        if skipped_by_sheet:
            for sheet, skipped in list(skipped_by_sheet.items())[:2]:  # Show first 2 sheets
                self._report_progress(
                    f"    [{sheet}] Skipped: {', '.join(skipped[:2])}{'...' if len(skipped) > 2 else ''}",
                    0, 1
                )

        return allowed
