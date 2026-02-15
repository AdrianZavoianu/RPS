"""Excel export helpers."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable, Optional, TYPE_CHECKING

import pandas as pd

from utils.timing import PhaseTimer
from .metadata import ExportMetadataBuilder
from .excel_sections import write_readme_sheet, write_metadata_sheets
from .discovery import ExportDiscovery
from .import_data import ImportDataBuilder
from .formatting import apply_excel_formatting

if TYPE_CHECKING:
    from .service import ProjectExportExcelOptions

logger = logging.getLogger(__name__)


class ExcelDatasetWriter:
    """Writes datasets to Excel with progress callbacks."""

    def __init__(self, progress_callback: Optional[Callable[[str, int, int], None]] = None):
        self.progress_callback = progress_callback or (lambda msg, curr, total: None)

    def write(self, df: pd.DataFrame, output_path: Path) -> None:
        total_steps = 1
        self.progress_callback("Writing file...", 1, total_steps)
        df.to_excel(output_path, index=False, engine="openpyxl")
        self.progress_callback("Export complete!", total_steps, total_steps)


class ProjectExcelExporter:
    """Exports an entire project to a multi-sheet Excel workbook."""

    def __init__(self, context, result_service, app_version: str):
        self.context = context
        self.result_service = result_service
        self.app_version = app_version

    def export_project_excel(
        self,
        options: "ProjectExportExcelOptions",
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
    ) -> None:
        timer = PhaseTimer({"project": self.context.slug})
        total_steps = 10

        if progress_callback:
            progress_callback("Gathering project metadata...", 1, total_steps)

        with timer.measure("metadata"):
            metadata = ExportMetadataBuilder(self.context, self.result_service).build_metadata()

        if progress_callback:
            progress_callback("Creating Excel workbook...", 2, total_steps)

        with pd.ExcelWriter(options.output_path, engine="openpyxl") as writer:
            if progress_callback:
                progress_callback("Writing README sheet...", 3, total_steps)
            with timer.measure("readme"):
                write_readme_sheet(writer, metadata, self.app_version)

            if progress_callback:
                progress_callback("Writing metadata sheets...", 4, total_steps)
            with timer.measure("metadata_sheets"):
                write_metadata_sheets(writer, metadata)

            if progress_callback:
                progress_callback("Writing result data sheets...", 5, total_steps)

            with timer.measure("result_sheets"):
                result_sheets = self._write_result_data_sheets(
                    writer,
                    metadata,
                    options,
                    (lambda msg, curr, tot: progress_callback(msg, 5 + curr, total_steps))
                    if progress_callback
                    else None,
                )

            if progress_callback:
                progress_callback("Writing import metadata...", 9, total_steps)
            with timer.measure("import_data"):
                ImportDataBuilder(self.context, self.app_version).write_import_data_sheet(
                    writer,
                    metadata,
                    result_sheets,
                )

        if progress_callback:
            progress_callback("Applying formatting...", 10, total_steps)
        with timer.measure("formatting"):
            apply_excel_formatting(options.output_path)

        if progress_callback:
            progress_callback("Export complete!", total_steps, total_steps)

        logger.info(
            "export_project_excel.complete",
            extra={
                "output_path": str(options.output_path),
                "timings": timer.as_list(),
            },
        )

    def _write_result_data_sheets(
        self,
        writer,
        metadata: dict,
        options: "ProjectExportExcelOptions",
        progress_callback: Optional[Callable] = None,
    ) -> dict:
        if options.result_set_ids:
            result_sets = [rs for rs in metadata["result_sets"] if rs.id in options.result_set_ids]
        else:
            result_sets = metadata["result_sets"]

        if not result_sets:
            return {"global": [], "element": []}

        result_set = result_sets[0]
        discovery = ExportDiscovery(self.context.session, self.context)
        return discovery.discover_and_write(writer, result_set.id, result_sets, progress_callback)
