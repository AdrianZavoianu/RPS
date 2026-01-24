"""Worker threads for time history import."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set

from PyQt6.QtCore import QThread, pyqtSignal

from processing.time_history_parser import prescan_time_history_file
from processing.time_history_importer import TimeHistoryImporter
from utils.error_handling import handle_worker_error

logger = logging.getLogger(__name__)

EXCEL_PATTERNS = ("*.xlsx", "*.xls")


class TimeHistoryPrescanWorker(QThread):
    """Worker thread for scanning folder for time history load cases."""

    progress = pyqtSignal(str, int, int)  # message, current, total
    finished = pyqtSignal(dict)  # {file_path: load_case_name, ...}
    error = pyqtSignal(str)

    def __init__(self, folder_path: Path):
        super().__init__()
        self.folder_path = folder_path

    def run(self):
        """Scan folder for time history files and extract load case names."""
        try:
            files = []
            for pattern in EXCEL_PATTERNS:
                files.extend(sorted(self.folder_path.glob(pattern)))

            # Filter out temp files
            files = [f for f in files if not f.name.startswith("~$")]

            if not files:
                self.finished.emit({})
                return

            result: Dict[str, str] = {}  # file_path -> load_case_name
            for idx, file_path in enumerate(files):
                self.progress.emit(f"Scanning {file_path.name}", idx + 1, len(files))
                try:
                    info = prescan_time_history_file(file_path)
                    load_case = info.get("load_case_name", "Unknown")
                    if load_case and load_case != "Unknown":
                        result[str(file_path)] = load_case
                except Exception as e:
                    logger.warning("Failed to prescan %s: %s", file_path.name, e)

            self.finished.emit(result)

        except Exception as e:
            error_msg = handle_worker_error(e, "Prescan failed", str(self.folder_path))
            self.error.emit(error_msg)


class TimeHistoryImportWorker(QThread):
    """Worker thread for time history import (non-blocking UI).

    Thread Safety: Creates its own session using the provided session_factory to ensure
    thread-safe database access. Never shares a session with the main UI thread.
    """

    progress = pyqtSignal(str, int, int)  # message, current, total
    finished = pyqtSignal(int, int)  # Number of records imported, result_set_id
    error = pyqtSignal(str)  # Error message

    def __init__(
        self,
        session_factory: Callable[[], object],
        file_paths: List[Path],
        project_id: int,
        result_set_id: int,
        selected_load_cases: Set[str],
        conflict_resolution: Optional[Dict[str, str]] = None,
    ):
        super().__init__()
        self.session_factory = session_factory
        self.file_paths = file_paths
        self.project_id = project_id
        self.result_set_id = result_set_id
        self.selected_load_cases = selected_load_cases
        self.conflict_resolution = conflict_resolution or {}

    def run(self):
        """Execute import in background thread with thread-safe session."""
        try:
            self.progress.emit("Initializing import...", 5, 100)

            session = self.session_factory()
            try:
                importer = TimeHistoryImporter(
                    session,
                    self.project_id,
                    self.result_set_id,
                    progress_callback=self._on_progress,
                )

                total_count = 0
                num_files = len(self.file_paths)

                for idx, file_path in enumerate(self.file_paths):
                    base_progress = int((idx / num_files) * 90) + 5
                    self.progress.emit(f"Processing {file_path.name}...", base_progress, 100)

                    # Check if this file's load case should be imported
                    # based on conflict resolution
                    try:
                        info = prescan_time_history_file(file_path)
                        load_case = info.get("load_case_name", "Unknown")
                    except Exception:
                        continue

                    # Skip if load case not selected
                    if load_case not in self.selected_load_cases:
                        continue

                    # Skip if conflict resolution says use different file
                    if load_case in self.conflict_resolution:
                        preferred_file = self.conflict_resolution[load_case]
                        if preferred_file and str(file_path) != preferred_file:
                            self.progress.emit(
                                f"Skipping {file_path.name} (using {Path(preferred_file).name} for {load_case})",
                                base_progress,
                                100,
                            )
                            continue

                    # Import this file
                    count = importer.import_file(file_path, self.selected_load_cases)
                    total_count += count

                self.progress.emit("Committing to database...", 95, 100)
                session.commit()
            finally:
                session.close()

            self.finished.emit(total_count, self.result_set_id)

        except Exception as e:
            error_msg = handle_worker_error(e, "Import failed")
            self.error.emit(error_msg)

    def _on_progress(self, percent: int, message: str):
        """Forward progress to signal.

        The importer calls this with (percent, message) format.
        We convert to (message, current, total) for the signal.
        """
        self.progress.emit(message, percent, 100)
