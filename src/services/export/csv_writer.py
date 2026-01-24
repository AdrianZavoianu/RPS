"""CSV export helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

import pandas as pd


class CsvDatasetWriter:
    """Writes datasets to CSV with progress callbacks."""

    def __init__(self, progress_callback: Optional[Callable[[str, int, int], None]] = None):
        self.progress_callback = progress_callback or (lambda msg, curr, total: None)

    def write(self, df: pd.DataFrame, output_path: Path) -> None:
        total_steps = 1
        self.progress_callback("Writing file...", 1, total_steps)
        df.to_csv(output_path, index=False)
        self.progress_callback("Export complete!", total_steps, total_steps)
