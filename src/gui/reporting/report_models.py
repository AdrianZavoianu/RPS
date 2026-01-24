"""Report view models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class ReportSection:
    """Data container for a report section."""

    title: str              # "Story Drifts - X Direction"
    result_type: str        # "Drifts"
    direction: str          # "X"
    result_set_id: int
    category: str = "Global"  # "Global", "Element", "Joint"
    element_id: Optional[int] = None
    analysis_context: str = "NLTHA"  # "NLTHA" or "Pushover"
    dataset: Optional[object] = None
    element_data: Optional[object] = None
    joint_data: Optional[object] = None
