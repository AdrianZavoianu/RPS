"""Export worker for single result type."""

import logging
from PyQt6.QtCore import QThread, pyqtSignal

from services.export.service import ExportService, ExportOptions
from utils.error_handling import handle_worker_error, log_exception

logger = logging.getLogger(__name__)


class ExportWorker(QThread):
    """Background worker for executing simple export operations.

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


