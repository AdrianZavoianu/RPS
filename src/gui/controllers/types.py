"""Typed interfaces for controller dependencies to enforce layering."""

from __future__ import annotations

from typing import Protocol, Any, List


class CacheRepositoryProtocol(Protocol):
    """Minimal interface for cache repository access used by controllers."""

    def get_distinct_load_cases(self, project_id: int, result_set_id: int) -> List[str]:
        ...


class ResultServiceProtocol(Protocol):
    """Methods consumed by result view controller."""

    def get_standard_dataset(self, result_type: str, direction: str, result_set_id: int, is_pushover: bool = False) -> Any:
        ...

    def get_element_dataset(self, element_id: int, result_type: str, direction: str, result_set_id: int, is_pushover: bool = False) -> Any:
        ...

    def get_joint_dataset(self, result_type: str, result_set_id: int, is_pushover: bool = False) -> Any:
        ...
