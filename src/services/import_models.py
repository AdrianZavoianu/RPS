"""Shared models for Excel import workflow."""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple


@dataclass
class ImportProjectExcelOptions:
    """Options for importing Excel project."""

    excel_path: Path
    new_project_name: Optional[str] = None  # If None, use name from Excel
    overwrite_existing: bool = False


@dataclass
class ImportPreview:
    """Preview of project to be imported."""

    project_name: str
    description: str
    created_at: str
    exported_at: str
    result_sets_count: int
    load_cases_count: int
    stories_count: int
    elements_count: int
    result_types: list
    warnings: list
    can_import: bool


@dataclass
class ImportMappings:
    """ID mappings built during import metadata creation."""

    project_id: int
    result_set_mapping: Dict[str, int]
    result_category_mapping: Dict[Tuple[str, str], int]
    load_case_mapping: Dict[str, int]
    story_mapping: Dict[str, int]
    element_mapping: Dict[str, int]


__all__ = [
    "ImportProjectExcelOptions",
    "ImportPreview",
    "ImportMappings",
]
