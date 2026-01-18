"""Controller to manage result view loading for ProjectDetailWindow."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List, Tuple, Any

from config.analysis_types import AnalysisType
from .types import CacheRepositoryProtocol, ResultServiceProtocol


@dataclass
class LoadedDataset:
    data: Any
    mapping: Optional[dict]


class ResultViewController:
    """Lightweight helper to prepare view data and mappings."""

    def __init__(self, project_id: int, cache_repo: CacheRepositoryProtocol, controller) -> None:
        self.project_id = project_id
        self.cache_repo = cache_repo
        self.controller = controller

    def get_pushover_mapping(self, result_set_id: int) -> Optional[dict]:
        """Proxy to controller mapping with fallback build."""
        return self.controller.get_pushover_mapping(result_set_id)

    def should_apply_pushover_mapping(self) -> bool:
        return self.controller.get_active_context() == AnalysisType.PUSHOVER

    def apply_mapping_to_headers(self, column_names: List[str], result_set_id: int) -> List[str]:
        """Return mapped headers for UI display; exports should continue using full names."""
        if not self.should_apply_pushover_mapping():
            return column_names
        mapping = self.get_pushover_mapping(result_set_id)
        if not mapping:
            return column_names
        return [mapping.get(name, name) for name in column_names]

    def get_standard_view(
        self, result_service: ResultServiceProtocol, result_type: str, direction: str, result_set_id: int
    ) -> Tuple[Any, Optional[dict]]:
        """Fetch standard dataset and optional mapping."""
        is_pushover = self.should_apply_pushover_mapping()
        dataset = result_service.get_standard_dataset(result_type, direction, result_set_id, is_pushover=is_pushover)
        mapping = self.get_pushover_mapping(result_set_id) if is_pushover else None
        return dataset, mapping

    def get_element_view(
        self, result_service: ResultServiceProtocol, element_id: int, result_type: str, direction: str, result_set_id: int
    ) -> Tuple[Any, Optional[dict]]:
        """Fetch element dataset and optional mapping."""
        is_pushover = self.should_apply_pushover_mapping()
        dataset = result_service.get_element_dataset(element_id, result_type, direction, result_set_id, is_pushover=is_pushover)
        mapping = self.get_pushover_mapping(result_set_id) if is_pushover else None
        return dataset, mapping

    def get_joint_view(
        self, result_service: ResultServiceProtocol, result_type: str, result_set_id: int
    ) -> Tuple[Any, Optional[dict]]:
        """Fetch joint dataset and optional mapping."""
        is_pushover = self.should_apply_pushover_mapping()
        dataset = result_service.get_joint_dataset(result_type, result_set_id, is_pushover=is_pushover)
        mapping = self.get_pushover_mapping(result_set_id) if is_pushover else None
        return dataset, mapping
