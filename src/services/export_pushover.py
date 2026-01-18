"""Pushover curve export helper."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

import pandas as pd


class PushoverExporter:
    """Exports pushover curves to Excel (one sheet per case)."""

    def __init__(self, context, repo_factory=None):
        self.context = context
        self._repo_factory = repo_factory

    def export_curves(
        self,
        result_set_id: int,
        output_path: Path,
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
    ) -> None:
        from database.repository import PushoverCaseRepository

        repo_factory = self._repo_factory or (lambda session: PushoverCaseRepository(session))

        with self.context.session() as session:
            pushover_repo = repo_factory(session)
            cases = pushover_repo.get_by_result_set(result_set_id)

            if not cases:
                raise ValueError(f"No pushover cases found for result set ID {result_set_id}")

            curves_to_export = []
            total_steps = len(cases)

            for idx, case in enumerate(cases):
                if progress_callback:
                    progress_callback(f"Loading {case.name}...", idx + 1, total_steps)

                curve_points = pushover_repo.get_curve_data(case.id)
                curves_to_export.append((case.name, curve_points))

        # Write outside session
        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            for idx, (case_name, curve_points) in enumerate(curves_to_export):
                df = pd.DataFrame(
                    [
                        {
                            "Step": pt.step_number,
                            "Base Shear (kN)": pt.base_shear,
                            "Displacement (mm)": pt.displacement,
                        }
                        for pt in curve_points
                    ]
                )
                df.to_excel(writer, sheet_name=case_name[:31], index=False)

                if progress_callback:
                    progress_callback(f"Exported {case_name}", len(curves_to_export), len(curves_to_export))
