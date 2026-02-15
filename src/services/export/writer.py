"""Excel/CSV writing helpers for export flows."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

import pandas as pd

from .excel_writer import ExcelDatasetWriter
from .csv_writer import CsvDatasetWriter


class ExportWriter:
    """Handles writing datasets to Excel/CSV with simple progress callbacks."""

    def __init__(self, progress_callback: Optional[Callable[[str, int, int], None]] = None):
        self.progress_callback = progress_callback or (lambda msg, curr, total: None)

    def write_dataset(self, df: pd.DataFrame, output_path: Path, format: str) -> None:
        if format == "excel":
            ExcelDatasetWriter(self.progress_callback).write(df, output_path)
        else:
            CsvDatasetWriter(self.progress_callback).write(df, output_path)
