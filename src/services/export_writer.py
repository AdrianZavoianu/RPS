"""Excel/CSV writing helpers for export flows."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

import pandas as pd


class ExportWriter:
    """Handles writing datasets to Excel/CSV with simple progress callbacks."""

    def __init__(self, progress_callback: Optional[Callable[[str, int, int], None]] = None):
        self.progress_callback = progress_callback or (lambda msg, curr, total: None)

    def write_dataset(self, df: pd.DataFrame, output_path: Path, format: str) -> None:
        total_steps = 1
        self.progress_callback("Writing file...", 1, total_steps)

        if format == "excel":
            df.to_excel(output_path, index=False, engine="openpyxl")
        else:
            df.to_csv(output_path, index=False)

        self.progress_callback("Export complete!", total_steps, total_steps)
