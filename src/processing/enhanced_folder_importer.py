"""Enhanced folder importer with load case selection and conflict resolution."""

import logging
from pathlib import Path
from time import perf_counter
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Type

from PyQt6.QtWidgets import QWidget
from sqlalchemy.orm import Session

from database.repository import ProjectRepository, LoadCaseRepository, StoryRepository
from services.import_preparation import (
    FilePrescanSummary,
    ImportPreparationService,
    PrescanResult,
    detect_conflicts,
    determine_allowed_load_cases,
)
from .data_importer import DataImporter
from .selective_data_importer import SelectiveDataImporter
from .folder_importer import TARGET_SHEETS
from .base_importer import BaseFolderImporter
from .import_stats import ImportStatsAggregator
from . import import_logging

logger = logging.getLogger(__name__)

# Lazy import to avoid circular dependency (processing -> gui)
# These are injected via parameters or imported only when needed
_LoadCaseSelectionDialog: Optional[Type] = None
_LoadCaseConflictDialog: Optional[Type] = None


def _get_selection_dialog():
    """Lazy import of LoadCaseSelectionDialog to avoid circular dependency."""
    global _LoadCaseSelectionDialog
    if _LoadCaseSelectionDialog is None:
        from gui.load_case_selection_dialog import LoadCaseSelectionDialog
        _LoadCaseSelectionDialog = LoadCaseSelectionDialog
    return _LoadCaseSelectionDialog


def _get_conflict_dialog():
    """Lazy import of LoadCaseConflictDialog to avoid circular dependency."""
    global _LoadCaseConflictDialog
    if _LoadCaseConflictDialog is None:
        from gui.load_case_conflict_dialog import LoadCaseConflictDialog
        _LoadCaseConflictDialog = LoadCaseConflictDialog
    return _LoadCaseConflictDialog


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
        preparation_service: Optional[ImportPreparationService] = None,
        prescan_result: Optional[PrescanResult] = None,
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
        self.foundation_joints = []  # Will be populated during pre-scan
        self.preparation_service = preparation_service or ImportPreparationService(TARGET_SHEETS)
        self.prescan_result = prescan_result
        self._file_summaries: Dict[str, FilePrescanSummary] = (
            prescan_result.file_summaries if prescan_result else {}
        )
        self._cache_builder: Optional[SelectiveDataImporter] = None

    @staticmethod
    def prescan_folder_for_load_cases(
        folder_path: Path,
        result_types: Optional[Set[str]] = None,
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> Tuple[Dict[str, Dict[str, List[str]]], List[str]]:
        """
        Static method to pre-scan a folder for load cases.
        Can be called from main thread before creating worker.

        Args:
            folder_path: Path to folder
            result_types: Optional set of result types to filter
            progress_callback: Optional progress callback

        Returns:
            Tuple of (file_load_cases, foundation_joints)
            - file_load_cases: Dict of file → sheet → load_cases
            - foundation_joints: List of unique joint names from all Fou sheets
        """
        service = ImportPreparationService(TARGET_SHEETS)
        result = service.prescan_folder(folder_path, result_types, progress_callback)
        return result.file_load_cases, result.foundation_joints


    def import_all(self) -> Dict[str, Any]:
        """
        Import with load case selection and conflict resolution.

        Returns:
            Dictionary with import statistics
        """
        if not self.excel_files:
            raise ValueError(f"No Excel files found in folder: {self.folder_path}")

        import_logging.log_import_start(
            logger=logger,
            project_name=self.project_name,
            result_set_name=self.result_set_name,
            file_name=f"{self.folder_path}/*",
            result_types=self.result_types,
        )

        # Phase 1: Pre-scan all files for load cases and foundation joints
        self._report_progress("Scanning files for load cases...", 0, len(self.excel_files))
        if self.prescan_result:
            file_load_cases = self.prescan_result.file_load_cases
            self.foundation_joints = list(self.prescan_result.foundation_joints)
            self._file_summaries = self.prescan_result.file_summaries
        else:
            file_load_cases, self.foundation_joints = self._prescan_load_cases()

        if not file_load_cases:
            stats = {
                "project": None,
                "files_processed": 0,
                "files_total": len(self.excel_files),
                "load_cases": 0,
                "errors": ["No load cases found in any files"],
                "phase_timings": [],
            }
            import_logging.log_phase_timings(
                logger=logger,
                project_name=self.project_name,
                result_set_name=self.result_set_name,
                file_name=f"{self.folder_path}/*",
                phase_timings=stats["phase_timings"],
            )
            import_logging.log_import_complete(
                logger=logger,
                project_name=self.project_name,
                result_set_name=self.result_set_name,
                file_name=f"{self.folder_path}/*",
                stats=stats,
            )
            return stats

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
        stats = self._import_with_selection_and_resolution(
            file_load_cases, selected_load_cases, self.conflict_resolution
        )
        import_logging.log_phase_timings(
            logger=logger,
            project_name=self.project_name,
            result_set_name=self.result_set_name,
            file_name=f"{self.folder_path}/*",
            phase_timings=stats.get("phase_timings", []),
        )
        import_logging.log_import_complete(
            logger=logger,
            project_name=self.project_name,
            result_set_name=self.result_set_name,
            file_name=f"{self.folder_path}/*",
            stats=stats,
        )
        return stats

    def _prescan_load_cases(self) -> Tuple[Dict[str, Dict[str, List[str]]], List[str]]:
        """
        Pre-scan all files to collect load cases and foundation joints.

        Returns:
            Tuple of (file_load_cases, foundation_joints)
            file_load_cases = {
                "file1.xlsx": {
                    "Story Drifts": ["DES_X", "DES_Y", "MCE_X"],
                    "Story Forces": ["DES_X", "DES_Y", "MCE_X"],
                },
                "file2.xlsx": {
                    "Story Drifts": ["SLE_X", "SLE_Y"],
                }
            }
            foundation_joints = ["J1", "J2", ...] from Fou sheet
        """
        result = self.preparation_service.prescan_files(
            self.excel_files,
            self.result_types,
            self._report_progress,
        )
        self._file_summaries = result.file_summaries
        return result.file_load_cases, result.foundation_joints

    def _finalize_cache_generation(self, stats: Dict[str, Any]) -> None:
        """Run a single cache build after all selective imports finish."""
        if not self._cache_builder:
            return

        self._report_progress("Building result caches...", len(self.excel_files), len(self.excel_files))
        start = perf_counter()
        self._cache_builder.generate_cache_if_needed()
        duration = perf_counter() - start
        stats["phase_timings"].append(
            {
                "phase": "cache_generation",
                "file": "ALL_FILES",
                "duration": duration,
                "source": "finalize",
            }
        )


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

        # Show selection dialog (lazy import to avoid circular dependency)
        SelectionDialog = _get_selection_dialog()
        dialog = SelectionDialog(
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
        return detect_conflicts(file_load_cases, selected_load_cases)

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
        # Lazy import to avoid circular dependency
        ConflictDialog = _get_conflict_dialog()
        dialog = ConflictDialog(conflicts, self.parent_widget)

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
            "errors": [],
            "phase_timings": [],
        }
        aggregator = ImportStatsAggregator()
        result_set_id: Optional[int] = None

        # Track which load cases have been imported per sheet
        imported_load_cases_by_sheet = {}  # {sheet: {load_cases}}

        for idx, file_path in enumerate(self.excel_files):
            file_name = file_path.name
            if file_name not in file_load_cases:
                continue

            self._report_progress(
                f"Importing {file_name}...",
                idx,
                len(self.excel_files)
            )

            allowed_load_cases = self._get_allowed_load_cases(
                file_name,
                file_load_cases[file_name],
                selected_load_cases,
                resolution,
                imported_load_cases_by_sheet
            )

            if not allowed_load_cases:
                self._report_progress(
                    f"  Skipping {file_name} (no allowed load cases)",
                    idx,
                    len(self.excel_files)
                )
                continue

            self._report_progress(
                f"  Importing {len(allowed_load_cases)} load case(s): {', '.join(sorted(allowed_load_cases)[:3])}{'...' if len(allowed_load_cases) > 3 else ''}",
                idx,
                len(self.excel_files)
            )

            try:
                result_types_list = list(self.result_types) if self.result_types else None
                importer = SelectiveDataImporter(
                    file_path=str(file_path),
                    project_name=self.project_name,
                    result_set_name=self.result_set_name,
                    allowed_load_cases=allowed_load_cases,
                    result_types=result_types_list,
                    session_factory=self._session_factory,
                    foundation_joints=self.foundation_joints,
                    file_summary=self._file_summaries.get(file_name),
                    generate_cache=False,
                )
                if self._cache_builder is None:
                    self._cache_builder = importer
                file_stats = importer.import_all()
                if result_set_id is None and getattr(importer, "result_set_id", None):
                    result_set_id = importer.result_set_id

                stats["project"] = file_stats.get("project", stats["project"])
                stats["files_processed"] += 1
                aggregator.merge(file_stats)
                aggregator.extend_errors(file_stats.get("errors") or [])
                stats["phase_timings"].extend(file_stats.get("phase_timings") or [])

                for sheet_name in file_load_cases[file_name].keys():
                    imported_load_cases_by_sheet.setdefault(sheet_name, set())
                    sheet_load_cases = set(file_load_cases[file_name][sheet_name])
                    imported_load_cases_by_sheet[sheet_name].update(
                        allowed_load_cases & sheet_load_cases
                    )

            except Exception as e:
                stats["errors"].append(f"{file_name}: {str(e)}")
                import_logging.log_import_failure(
                    logger=logger,
                    project_name=self.project_name,
                    result_set_name=self.result_set_name,
                    file_name=file_name,
                    error=e,
                )

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

        agg_data = aggregator.as_dict()
        agg_errors = agg_data.pop("errors", [])
        stats.update(agg_data)
        if result_set_id is not None:
            stats["result_set_id"] = result_set_id
        if agg_errors:
            stats["errors"].extend(agg_errors)

        self._finalize_cache_generation(stats)
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
        allowed, skipped_by_sheet = determine_allowed_load_cases(
            file_name=file_name,
            file_sheets=file_sheets,
            selected_load_cases=selected_load_cases,
            resolution=resolution,
            already_imported=already_imported,
        )

        if skipped_by_sheet:
            for sheet, skipped in list(skipped_by_sheet.items())[:2]:
                self._report_progress(
                    f"    [{sheet}] Skipped: {', '.join(skipped[:2])}"
                    f"{'...' if len(skipped) > 2 else ''}",
                    0,
                    1,
                )

        return allowed
