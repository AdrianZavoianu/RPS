"""Import service for RPS projects."""

import json
import logging
from pathlib import Path
from typing import Callable, Optional

import pandas as pd

from services.import_models import ImportPreview, ImportProjectExcelOptions
from services.import_database_json import (
    import_database_from_json as import_database_from_json_payload,
)
from services.import_metadata import import_metadata as import_metadata_tables
from services.import_preview import preview_import as build_import_preview
from services.import_results import (
    create_normalized_result as create_normalized_result_helper,
    import_element_result as import_element_result_helper,
    import_global_result as import_global_result_helper,
    import_result_data as import_result_data_sheets,
)
from services.project_service import ProjectContext, ensure_project_context
from utils.error_handling import timed


logger = logging.getLogger(__name__)


class ImportService:
    """Service for importing Excel project files."""

    @timed
    def preview_import(self, excel_path: Path) -> ImportPreview:
        """Preview Excel file before importing."""
        return build_import_preview(excel_path)

    @timed
    def import_project_excel(
        self,
        options: ImportProjectExcelOptions,
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> ProjectContext:
        """Import project from Excel workbook.

        Args:
            options: Import options
            progress_callback: Optional callback(message, current, total)

        Returns:
            ProjectContext for newly imported project

        Raises:
            ValueError: If Excel file is invalid
            IOError: If file cannot be read
        """
        total_steps = 8

        # Step 1: Read import metadata
        if progress_callback:
            progress_callback("Reading import metadata...", 1, total_steps)

        import_data_df = pd.read_excel(options.excel_path, sheet_name="IMPORT_DATA")

        # Concatenate all rows to reassemble the JSON (may be chunked)
        json_chunks = import_data_df['import_metadata'].tolist()
        json_str = ''.join(str(chunk) for chunk in json_chunks if pd.notna(chunk))

        import_metadata = json.loads(json_str)

        project_info = import_metadata.get('project', {})
        project_name = options.new_project_name or project_info.get('name')

        # Step 2: Create project
        if progress_callback:
            progress_callback("Creating project...", 2, total_steps)

        # Create project context (name is already validated by UI)
        context = ensure_project_context(
            name=project_name,
            description=project_info.get('description', '')
        )

        # Step 3: Import metadata (result sets, load cases, stories, elements)
        if progress_callback:
            progress_callback("Importing metadata...", 3, total_steps)

        self._import_metadata(context, import_metadata)

        # Step 4-7: Import complete database from IMPORT_DATA
        if progress_callback:
            progress_callback("Importing database...", 4, total_steps)

        self._import_database_from_json(
            context, import_metadata,
            lambda msg, curr, tot: progress_callback(msg, 4 + curr, total_steps) if progress_callback else None
        )

        # Step 8: Complete
        if progress_callback:
            progress_callback("Import complete!", total_steps, total_steps)

        return context

    def _import_metadata(self, context: ProjectContext, import_metadata: dict) -> None:
        """Import metadata tables (result sets, load cases, stories, elements)."""
        self._import_context = import_metadata_tables(context, import_metadata)

    def _import_database_from_json(
        self,
        context: ProjectContext,
        import_metadata: dict,
        progress_callback: Optional[Callable] = None
    ) -> None:
        """Import complete per-project database from JSON in IMPORT_DATA sheet."""
        import_database_from_json_payload(
            context,
            import_metadata,
            self._import_context,
            progress_callback,
        )

    def _import_result_data(
        self,
        context: ProjectContext,
        excel_path: Path,
        import_metadata: dict,
        progress_callback: Optional[Callable] = None
    ) -> None:
        """Import result data from Excel sheets into cache tables."""
        import_result_data_sheets(
            context,
            excel_path,
            import_metadata,
            self._import_context,
            progress_callback,
        )

    def _import_global_result(self, session, cache_repo, result_type: str, df: pd.DataFrame) -> None:
        """Import global result data into GlobalResultsCache."""
        import_global_result_helper(
            session,
            cache_repo,
            result_type,
            df,
            self._import_context,
        )

    def _create_normalized_result(
        self,
        session,
        result_type: str,
        direction: str,
        project_id: int,
        result_set_id: int,
        story_id: int,
        load_case_id: int,
        value: float,
        story_sort_order: int = 0,
    ) -> None:
        """Create normalized result entry in the appropriate table."""
        create_normalized_result_helper(
            session,
            result_type,
            direction,
            project_id,
            result_set_id,
            story_id,
            load_case_id,
            value,
            story_sort_order=story_sort_order,
        )

    def _import_element_result(self, session, element_cache_repo, result_type: str, df: pd.DataFrame) -> None:
        """Import element result data into ElementResultsCache."""
        import_element_result_helper(
            session,
            element_cache_repo,
            result_type,
            df,
            self._import_context,
        )
