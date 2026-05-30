"""Backward-compatible import preparation shim."""

from processing.import_preparation import (
    FilePrescanSummary,
    ImportPreparationService,
    PrescanResult,
    detect_conflicts,
    determine_allowed_load_cases,
    get_existing_load_cases_by_task_for_result_set,
    get_existing_load_cases_for_result_set,
)

__all__ = [
    "FilePrescanSummary",
    "ImportPreparationService",
    "PrescanResult",
    "detect_conflicts",
    "determine_allowed_load_cases",
    "get_existing_load_cases_by_task_for_result_set",
    "get_existing_load_cases_for_result_set",
]
