"""Folder-based batch importer for processing multiple Excel files."""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy.orm import Session

from database.repository import ProjectRepository, LoadCaseRepository, StoryRepository

from services.import_preparation import FilePrescanSummary
from .excel_parser import ExcelParser
from .data_importer import DataImporter
from .base_importer import BaseFolderImporter
from .import_stats import ImportStatsAggregator
from . import import_logging

logger = logging.getLogger(__name__)

TARGET_SHEETS: Dict[str, List[str]] = {
    "Story Drifts": ["Story Drifts"],
    "Diaphragm Accelerations": ["Story Accelerations"],  # Using Diaphragm Accelerations sheet (newer ETABS format)
    "Story Forces": ["Story Forces"],
    "Joint Displacements": ["Floors Displacements"],  # Floor displacements from Joint Displacements sheet
    "Pier Forces": ["Pier Forces"],
    # Columns sheet supplies both shears and axial compression envelopes.
    "Element Forces - Columns": ["Column Forces", "Column Axials"],
    # Fiber Hinge States sheet supplies column rotations (R2, R3).
    "Fiber Hinge States": ["Column Rotations"],
    # Hinge States sheet supplies beam rotations (R3 Plastic).
    "Hinge States": ["Beam Rotations"],
    "Quad Strain Gauge - Rotation": ["Quad Rotations"],
    "Soil Pressures": ["Soil Pressures"],  # Foundation soil pressures
}


class FolderImporter(BaseFolderImporter):
    """Import structural analysis results from a folder containing multiple Excel files."""

    def __init__(
        self,
        folder_path: str,
        project_name: str,
        result_set_name: str,
        result_types: Optional[List[str]] = None,
        session_factory: Optional[Callable[[], Session]] = None,
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
        file_summaries: Optional[Dict[str, FilePrescanSummary]] = None,
    ):
        super().__init__(
            folder_path=folder_path,
            result_types=result_types,
            session_factory=session_factory,
            progress_callback=progress_callback,
        )
        self.project_name = project_name
        self.result_set_name = result_set_name
        self._session_factory = session_factory
        self._file_summaries = file_summaries or {}

    def import_all(self) -> Dict[str, Any]:
        """Import data from all Excel files in the folder."""
        if not self.excel_files:
            raise ValueError(f"No Excel files found in folder: {self.folder_path}")

        stats: Dict[str, Any] = {
            "project": None,
            "files_processed": 0,
            "files_total": len(self.excel_files),
            "load_cases": 0,
            "stories": 0,
            "errors": [],
        }
        aggregator = ImportStatsAggregator()
        result_set_id: Optional[int] = None

        self._report_progress("Processing files...", 0, len(self.excel_files))

        import_logging.log_import_start(
            logger=logger,
            project_name=self.project_name,
            result_set_name=self.result_set_name,
            file_name=f"{self.folder_path}/*",
            result_types=self.result_types,
        )

        for idx, excel_file in enumerate(self.excel_files, 1):
            try:
                self._report_progress(
                    f"Scanning {excel_file.name} ({idx}/{len(self.excel_files)})",
                    idx - 1,
                    len(self.excel_files),
                )

                parser = ExcelParser(str(excel_file))
                summary = self._file_summaries.get(excel_file.name)
                if summary:
                    available = summary.available_sheets
                else:
                    available = set(parser.get_available_sheets())

                matched_labels = []
                for sheet, labels in TARGET_SHEETS.items():
                    if sheet not in available:
                        continue
                    for label in labels:
                        if self._should_import(label) and label not in matched_labels:
                            matched_labels.append(label)

                # Special case: If both Joint Displacements and Fou sheets exist, also enable Vertical Displacements
                # This is separate from Floor Displacements which also uses Joint Displacements
                if ("Joint Displacements" in available and "Fou" in available):
                    if "Vertical Displacements" not in matched_labels:
                        matched_labels.append("Vertical Displacements")

                if not matched_labels:
                    continue

                importer = DataImporter(
                    file_path=str(excel_file),
                    project_name=self.project_name,
                    result_set_name=self.result_set_name,
                    result_types=matched_labels,
                    session_factory=self._session_factory,
                    file_summary=summary,
                )
                file_stats = importer.import_all()
                if result_set_id is None and getattr(importer, "result_set_id", None):
                    result_set_id = importer.result_set_id

                stats["project"] = file_stats.get("project", stats["project"])
                stats["files_processed"] += 1
                aggregator.merge(file_stats)
                aggregator.extend_errors(file_stats.get("errors") or [])

            except Exception as exc:  # collect error and continue
                stats["errors"].append(f"{excel_file.name}: {exc}")
                import_logging.log_import_failure(
                    logger=logger,
                    project_name=self.project_name,
                    result_set_name=self.result_set_name,
                    file_name=excel_file.name,
                    error=exc,
                )

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
        stats.setdefault("errors", [])
        if agg_errors:
            stats["errors"].extend(agg_errors)

        stats["phase_timings"] = []  # Folder imports aggregate per-file timings elsewhere if needed
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

        self._report_progress("Import complete", len(self.excel_files), len(self.excel_files))
        return stats

    def get_file_list(self) -> List[str]:
        """Return the list of Excel file names that will be processed."""
        return [f.name for f in self.excel_files]

    def get_file_count(self) -> int:
        """Return the number of Excel files detected in the folder."""
        return len(self.excel_files)
