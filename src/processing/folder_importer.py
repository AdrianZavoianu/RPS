"""Folder-based batch importer for processing multiple Excel files."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy.orm import Session

from database.repository import ProjectRepository, LoadCaseRepository, StoryRepository

from .excel_parser import ExcelParser
from .data_importer import DataImporter

TARGET_SHEETS: Dict[str, List[str]] = {
    "Story Drifts": ["Story Drifts"],
    "Diaphragm Accelerations": ["Story Accelerations"],  # Using Diaphragm Accelerations sheet (newer ETABS format)
    "Story Forces": ["Story Forces"],
    "Joint DisplacementsG": ["Floors Displacements"],
    "Pier Forces": ["Pier Forces"],
    # Columns sheet supplies both shears and axial compression envelopes.
    "Element Forces - Columns": ["Column Forces", "Column Axials"],
    # Fiber Hinge States sheet supplies column rotations (R2, R3).
    "Fiber Hinge States": ["Column Rotations"],
    # Hinge States sheet supplies beam rotations (R3 Plastic).
    "Hinge States": ["Beam Rotations"],
    "Quad Strain Gauge - Rotation": ["Quad Rotations"],
}


class FolderImporter:
    """Import structural analysis results from a folder containing multiple Excel files."""

    def __init__(
        self,
        folder_path: str,
        project_name: str,
        result_set_name: str,
        result_types: Optional[List[str]] = None,
        session_factory: Optional[Callable[[], Session]] = None,
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
    ):
        self.folder_path = Path(folder_path)
        if not self.folder_path.exists() or not self.folder_path.is_dir():
            raise ValueError(f"Invalid folder path: {folder_path}")

        self.project_name = project_name
        self.result_set_name = result_set_name
        self.result_types = {rt.strip().lower() for rt in result_types} if result_types else None
        self.progress_callback = progress_callback
        self.excel_files = self._find_excel_files()
        if session_factory is None:
            raise ValueError("FolderImporter requires a session_factory")
        self._session_factory = session_factory

    def _find_excel_files(self) -> List[Path]:
        files: List[Path] = []
        for pattern in ("*.xlsx", "*.xls"):
            files.extend(self.folder_path.glob(pattern))
        return sorted(f for f in files if not f.name.startswith("~$"))

    def _report_progress(self, message: str, current: int, total: int) -> None:
        if self.progress_callback:
            self.progress_callback(message, current, total)

    def _should_import(self, label: str) -> bool:
        if not self.result_types:
            return True
        return label.strip().lower() in self.result_types

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
            "drifts": 0,
            "accelerations": 0,
            "forces": 0,
            "displacements": 0,
            "errors": [],
        }

        self._report_progress("Processing files...", 0, len(self.excel_files))

        for idx, excel_file in enumerate(self.excel_files, 1):
            try:
                self._report_progress(
                    f"Scanning {excel_file.name} ({idx}/{len(self.excel_files)})",
                    idx - 1,
                    len(self.excel_files),
                )

                parser = ExcelParser(str(excel_file))
                available = set(parser.get_available_sheets())

                matched_labels = []
                for sheet, labels in TARGET_SHEETS.items():
                    if sheet not in available:
                        continue
                    for label in labels:
                        if self._should_import(label) and label not in matched_labels:
                            matched_labels.append(label)

                if not matched_labels:
                    continue

                importer = DataImporter(
                    file_path=str(excel_file),
                    project_name=self.project_name,
                    result_set_name=self.result_set_name,
                    result_types=matched_labels,
                    session_factory=self._session_factory,
                )
                file_stats = importer.import_all()

                stats["project"] = file_stats.get("project", stats["project"])
                stats["files_processed"] += 1
                for key in ("drifts", "accelerations", "forces", "displacements"):
                    stats[key] += file_stats.get(key, 0)

            except Exception as exc:  # collect error and continue
                stats["errors"].append(f"{excel_file.name}: {exc}")

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

    def get_file_list(self) -> List[str]:
        """Return the list of Excel file names that will be processed."""
        return [f.name for f in self.excel_files]

    def get_file_count(self) -> int:
        """Return the number of Excel files detected in the folder."""
        return len(self.excel_files)
