"""Worker threads for folder import dialog."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Optional, Sequence, Set

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import QWidget

from processing.import_preparation import ImportPreparationService, PrescanResult
from services.project_service import ProjectContext
from processing.folder_importer import TARGET_SHEETS

logger = logging.getLogger(__name__)


class LoadCaseScanWorker(QThread):
    """Worker thread for scanning files for load cases."""

    progress = pyqtSignal(str, int, int)  # message, current, total
    finished = pyqtSignal(object)  # PrescanResult
    error = pyqtSignal(str)  # error message

    def __init__(
        self,
        folder_path: Path,
        result_types: Optional[Sequence[str]] = None,
    ) -> None:
        super().__init__()
        self.folder_path = folder_path
        self.result_types = result_types

    def run(self) -> None:  # pragma: no cover - executes in worker thread
        """Scan files for load cases in background thread."""
        try:
            result_types_set = None
            if self.result_types:
                result_types_set = {rt.strip().lower() for rt in self.result_types}

            service = ImportPreparationService(TARGET_SHEETS)
            prescan = service.prescan_folder(
                self.folder_path,
                result_types_set,
                self._on_progress,
            )
            logger.info(
                "Folder prescan finished",
                extra={
                    "event": "prescan.complete",
                    "folder": str(self.folder_path),
                    "files": prescan.files_scanned,
                    "errors": len(prescan.errors),
                },
            )
            self.finished.emit(prescan)
        except Exception as exc:  # pragma: no cover - UI feedback
            logger.exception(
                "Folder prescan failed",
                extra={
                    "event": "prescan.failure",
                    "folder": str(self.folder_path),
                },
            )
            self.error.emit(str(exc))

    def _on_progress(self, message: str, current: int, total: int) -> None:
        """Relay progress updates back to the dialog thread."""
        self.progress.emit(message, current, total)


class FolderImportWorker(QThread):
    """Worker thread for folder import to avoid blocking UI."""

    progress = pyqtSignal(str, int, int)  # message, current, total
    finished = pyqtSignal(dict)  # stats (will include result_set_id)
    error = pyqtSignal(str)  # error message

    def __init__(
        self,
        context: ProjectContext,
        folder_path: Path,
        result_set_name: str,
        result_types: Optional[Sequence[str]] = None,
        use_enhanced: bool = False,
        parent_widget: Optional[QWidget] = None,
        selected_load_cases: Optional[Set[str]] = None,
        conflict_resolution: Optional[Dict[str, Dict[str, Optional[str]]]] = None,
        prescan_result: Optional[PrescanResult] = None,
    ) -> None:
        super().__init__()
        self.context = context
        self.folder_path = folder_path
        self.result_set_name = result_set_name
        self.result_types = list(result_types) if result_types else None
        self.use_enhanced = use_enhanced
        self.parent_widget = parent_widget
        self.selected_load_cases = selected_load_cases
        self.conflict_resolution = conflict_resolution
        self.prescan_result = prescan_result
        self._session_factory = context.session_factory()
        self.result_set_id: Optional[int] = None

    def run(self) -> None:  # pragma: no cover - executes in worker thread
        """Run the import in background thread."""
        try:
            logger.info(
                "Folder import worker starting",
                extra={
                    "event": "import.folder.start",
                    "project": self.context.name,
                    "result_set": self.result_set_name,
                    "folder": str(self.folder_path),
                    "enhanced": self.use_enhanced,
                },
            )
            if self.use_enhanced:
                from processing.folder_importer import EnhancedFolderImporter

                importer = EnhancedFolderImporter(
                    folder_path=str(self.folder_path),
                    project_name=self.context.name,
                    result_set_name=self.result_set_name,
                    result_types=self.result_types,
                    session_factory=self._session_factory,
                    progress_callback=self._on_progress,
                    parent_widget=self.parent_widget,
                    selected_load_cases=self.selected_load_cases,
                    conflict_resolution=self.conflict_resolution,
                    prescan_result=self.prescan_result,
                )
                stats = importer.import_all()
                if hasattr(importer, "result_set_id"):
                    self.result_set_id = importer.result_set_id
                    stats["result_set_id"] = importer.result_set_id
                self.finished.emit(stats)
            else:
                from processing.folder_importer import FolderImporter

                importer = FolderImporter(
                    folder_path=str(self.folder_path),
                    project_name=self.context.name,
                    result_set_name=self.result_set_name,
                    result_types=self.result_types,
                    session_factory=self._session_factory,
                    progress_callback=self._on_progress,
                    file_summaries=self.prescan_result.file_summaries if self.prescan_result else None,
                )
                stats = importer.import_all()
                if hasattr(importer, "result_set_id"):
                    self.result_set_id = importer.result_set_id
                    stats["result_set_id"] = importer.result_set_id
                self.finished.emit(stats)
                logger.info(
                    "Folder import worker finished",
                    extra={
                        "event": "import.folder.complete",
                        "project": self.context.name,
                        "result_set": self.result_set_name,
                        "files_processed": stats.get("files_processed"),
                        "files_total": stats.get("files_total"),
                        "errors": len(stats.get("errors") or []),
                    },
                )
        except Exception as exc:  # pragma: no cover - UI feedback
            logger.exception(
                "Folder import worker failed",
                extra={
                    "event": "import.folder.failure",
                    "project": self.context.name,
                    "result_set": self.result_set_name,
                },
            )
            self.error.emit(str(exc))

    def _on_progress(self, message: str, current: int, total: int) -> None:
        """Relay progress updates back to the dialog thread."""
        self.progress.emit(message, current, total)
