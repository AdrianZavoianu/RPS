"""Export service package."""

__all__ = [
    "ExportService",
    "ExportOptions",
    "ProjectExportExcelOptions",
    "ProjectExcelExporter",
    "ExcelDatasetWriter",
    "CsvDatasetWriter",
    "CurveExporter",
]


def __getattr__(name: str):
    if name in {"ExportService", "ExportOptions", "ProjectExportExcelOptions"}:
        from .service import ExportService, ExportOptions, ProjectExportExcelOptions
        return {
            "ExportService": ExportService,
            "ExportOptions": ExportOptions,
            "ProjectExportExcelOptions": ProjectExportExcelOptions,
        }[name]

    if name in {"ProjectExcelExporter", "ExcelDatasetWriter"}:
        from .excel_writer import ProjectExcelExporter, ExcelDatasetWriter
        return {
            "ProjectExcelExporter": ProjectExcelExporter,
            "ExcelDatasetWriter": ExcelDatasetWriter,
        }[name]

    if name == "CsvDatasetWriter":
        from .csv_writer import CsvDatasetWriter
        return CsvDatasetWriter

    if name == "CurveExporter":
        from .curve_exporter import CurveExporter
        return CurveExporter

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
