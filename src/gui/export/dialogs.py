"""Export dialog compatibility shim."""

from services.export.discovery import ExportDiscoveryService

# Re-export for backward-compat tests that monkeypatch dialogs.ExportDiscoveryService
ExportDiscoveryService = ExportDiscoveryService

from .comprehensive_dialog import ComprehensiveExportDialog
from .simple_dialog import SimpleExportDialog
from .project_excel_dialog import ExportProjectExcelDialog

__all__ = [
    "ComprehensiveExportDialog",
    "SimpleExportDialog",
    "ExportProjectExcelDialog",
]
