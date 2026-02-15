"""Export worker for project Excel output."""

import logging
from PyQt6.QtCore import QThread, pyqtSignal

from services.export.service import ExportService
from utils.error_handling import handle_worker_error, log_exception

logger = logging.getLogger(__name__)


class ExportProjectExcelWorker(QThread):
    """Background worker for Excel project export."""

    progress = pyqtSignal(str, int, int)
    finished = pyqtSignal(bool, str, str)

    def __init__(self, context, result_service, options):
        super().__init__()
        self.context = context
        self.result_service = result_service
        self.options = options

    def run(self):
        try:
            from services.export.service import ExportService

            export_service = ExportService(self.context, self.result_service)

            export_service.export_project_excel(
                self.options,
                progress_callback=self._emit_progress
            )

            self.finished.emit(
                True,
                "Project exported successfully to Excel!",
                str(self.options.output_path)
            )
        except Exception as e:
            error_msg = handle_worker_error(e, "Export failed")
            self.finished.emit(False, error_msg, "")

    def _emit_progress(self, message: str, current: int, total: int):
        self.progress.emit(message, current, total)
