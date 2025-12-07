"""Controller for ProjectDetailWindow state and context handling."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

from config.analysis_types import AnalysisType, normalize_analysis_type
from services.pushover_context import build_pushover_mapping, strip_direction_suffixes


@dataclass
class SelectionState:
    result_type: Optional[str] = None
    result_set_id: Optional[int] = None
    direction: str = "X"
    element_id: int = 0
    active_context: AnalysisType = AnalysisType.NLTHA


class ProjectDetailController:
    """Encapsulates selection and context state for ProjectDetailWindow."""

    def __init__(self, project_id: int, cache_repo) -> None:
        self.project_id = project_id
        self.cache_repo = cache_repo
        self.selection = SelectionState()
        # Cache for pushover load case mappings: result_set_id -> mapping
        self._pushover_mappings: Dict[int, Dict[str, str]] = {}

    # ---- Context helpers -------------------------------------------------

    def set_active_context(self, analysis_type: str | AnalysisType) -> None:
        self.selection.active_context = normalize_analysis_type(analysis_type)

    def get_active_context(self) -> AnalysisType:
        return self.selection.active_context

    # ---- Selection helpers ----------------------------------------------

    def update_selection(
        self,
        result_type: Optional[str] = None,
        result_set_id: Optional[int] = None,
        direction: Optional[str] = None,
        element_id: Optional[int] = None,
    ) -> None:
        if result_type is not None:
            self.selection.result_type = result_type
        if result_set_id is not None:
            self.selection.result_set_id = result_set_id
        if direction is not None:
            self.selection.direction = direction
        if element_id is not None:
            self.selection.element_id = element_id

    # ---- Pushover shorthand mappings ------------------------------------

    def get_pushover_mapping(self, result_set_id: int) -> Dict[str, str]:
        """Return (and build if needed) the pushover shorthand mapping for a result set."""
        if result_set_id in self._pushover_mappings:
            return dict(self._pushover_mappings[result_set_id])

        load_cases_with_suffix = self.cache_repo.get_distinct_load_cases(self.project_id, result_set_id)
        if not load_cases_with_suffix:
            self._pushover_mappings[result_set_id] = {}
            return {}

        base_cases = strip_direction_suffixes(load_cases_with_suffix)
        mapping = build_pushover_mapping(base_cases)
        self._pushover_mappings[result_set_id] = mapping
        return dict(mapping)

    def reset_pushover_mapping(self, result_set_id: Optional[int] = None) -> None:
        """Reset cached pushover mapping for a specific result set or all."""
        if result_set_id is None:
            self._pushover_mappings.clear()
        else:
            self._pushover_mappings.pop(result_set_id, None)
