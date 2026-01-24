"""Pushover curve export helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from services.export_pushover import PushoverExporter


class CurveExporter:
    """Exports pushover curves for a result set."""

    def __init__(self, context):
        self.context = context

    def export_pushover_curves(
        self,
        result_set_id: int,
        output_path: Path,
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
    ) -> None:
        PushoverExporter(self.context).export_curves(result_set_id, output_path, progress_callback)
