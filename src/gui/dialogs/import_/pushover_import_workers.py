"""Worker threads for pushover curve import."""

from __future__ import annotations

from typing import Callable

from PyQt6.QtCore import QThread, pyqtSignal

from processing.pushover.pushover_curve_importer import PushoverImporter


class PushoverCurveImportWorker(QThread):
    """Worker thread for pushover curve import (non-blocking UI)."""

    progress = pyqtSignal(str)  # Status message
    finished = pyqtSignal(dict)  # Import statistics
    error = pyqtSignal(str)  # Error message

    def __init__(
        self,
        session_factory: Callable[[], object],
        file_path,
        project_id: int,
        result_set_name: str,
        base_story: str,
        direction: str,
        overwrite: bool,
    ):
        super().__init__()
        self.session_factory = session_factory
        self.file_path = file_path
        self.project_id = project_id
        self.result_set_name = result_set_name
        self.base_story = base_story
        self.direction = direction
        self.overwrite = overwrite

    def run(self):
        """Execute import in background thread with thread-safe session."""
        try:
            self.progress.emit("Initializing importer...")

            session = self.session_factory()
            try:
                importer = PushoverImporter(session)

                if self.direction:
                    self.progress.emit(f"Parsing Excel file (direction: {self.direction})...")
                else:
                    self.progress.emit("Parsing Excel file (both X and Y directions)...")

                stats = importer.import_pushover_file(
                    file_path=self.file_path,
                    project_id=self.project_id,
                    result_set_name=self.result_set_name,
                    base_story=self.base_story,
                    direction=self.direction,
                    overwrite=self.overwrite,
                )
                session.commit()
            finally:
                session.close()

            self.finished.emit(stats)

        except Exception as e:
            self.error.emit(str(e))
