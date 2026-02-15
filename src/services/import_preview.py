"""Preview helpers for Excel import workflow."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pandas as pd

from services.import_models import ImportPreview

logger = logging.getLogger(__name__)


def preview_import(excel_path: Path) -> ImportPreview:
    """Preview Excel file before importing.

    Validates file structure and returns summary without creating project.
    """
    warnings = []
    can_import = True

    try:
        # Read IMPORT_DATA sheet (may be split across multiple rows)
        import_data_df = pd.read_excel(excel_path, sheet_name="IMPORT_DATA")

        # Concatenate all rows to reassemble the JSON
        json_chunks = import_data_df["import_metadata"].tolist()
        json_str = "".join(str(chunk) for chunk in json_chunks if pd.notna(chunk))

        import_metadata = json.loads(json_str)

        project_info = import_metadata.get("project", {})
        result_sheets = import_metadata.get("result_sheet_mapping", {})

        logger.debug("Preview result_sheet_mapping: %s", result_sheets)

        # Validate required sheets exist
        xl_file = pd.ExcelFile(excel_path)
        logger.debug("Preview Excel sheets: %s", xl_file.sheet_names)
        required_sheets = ["README", "Result Sets", "Load Cases", "Stories", "IMPORT_DATA"]
        missing_sheets = [s for s in required_sheets if s not in xl_file.sheet_names]

        if missing_sheets:
            warnings.append(f"Missing required sheets: {', '.join(missing_sheets)}")
            can_import = False

        # Validate result data sheets exist
        all_result_types = result_sheets.get("global", []) + result_sheets.get("element", [])
        missing_data = [rt for rt in all_result_types if rt[:31] not in xl_file.sheet_names]

        if missing_data:
            warnings.append(f"Missing result data sheets: {', '.join(missing_data)}")

        return ImportPreview(
            project_name=project_info.get("name", "Unknown"),
            description=project_info.get("description", ""),
            created_at=project_info.get("created_at", ""),
            exported_at=import_metadata.get("export_timestamp", ""),
            result_sets_count=len(import_metadata.get("result_sets", [])),
            load_cases_count=len(import_metadata.get("load_cases", [])),
            stories_count=len(import_metadata.get("stories", [])),
            elements_count=len(import_metadata.get("elements", [])),
            result_types=all_result_types,
            warnings=warnings,
            can_import=can_import,
        )

    except Exception as exc:
        logger.exception("Failed to preview import for %s", excel_path)
        return ImportPreview(
            project_name="Error",
            description="",
            created_at="",
            exported_at="",
            result_sets_count=0,
            load_cases_count=0,
            stories_count=0,
            elements_count=0,
            result_types=[],
            warnings=[f"Failed to read Excel file: {str(exc)}"],
            can_import=False,
        )


__all__ = ["preview_import"]
