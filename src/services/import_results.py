"""Result sheet import helpers for Excel project import."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable, Optional

import pandas as pd

from services.import_models import ImportMappings
from services.project_service import ProjectContext
from database.repositories import CacheRepository, ElementCacheRepository

logger = logging.getLogger(__name__)


def import_result_data(
    context: ProjectContext,
    excel_path: Path,
    import_metadata: dict,
    mappings: ImportMappings,
    progress_callback: Optional[Callable] = None,
) -> None:
    """Import result data from Excel sheets into cache tables."""
    result_sheets = import_metadata.get("result_sheet_mapping", {})
    global_types = result_sheets.get("global", [])
    element_types = result_sheets.get("element", [])

    logger.debug("Importing result data")
    logger.debug("Global types: %s", global_types)
    logger.debug("Element types: %s", element_types)

    total = len(global_types) + len(element_types)
    current = 0

    with context.session() as session:
        cache_repo = CacheRepository(session)
        element_cache_repo = ElementCacheRepository(session)

        # Import global results
        for result_type in global_types:
            if progress_callback:
                progress_callback(f"Importing {result_type}...", current, total)

            sheet_name = result_type[:31]
            logger.debug("Reading sheet '%s' for %s", sheet_name, result_type)
            df = pd.read_excel(excel_path, sheet_name=sheet_name)
            logger.debug("Sheet has %s rows, %s columns", len(df), len(df.columns))

            import_global_result(session, cache_repo, result_type, df, mappings)
            current += 1

        # Import element results
        for result_type in element_types:
            if progress_callback:
                progress_callback(f"Importing {result_type}...", current, total)

            sheet_name = result_type[:31]
            logger.debug("Reading sheet '%s' for %s", sheet_name, result_type)
            df = pd.read_excel(excel_path, sheet_name=sheet_name)
            logger.debug("Sheet has %s rows, %s columns", len(df), len(df.columns))

            import_element_result(session, element_cache_repo, result_type, df, mappings)
            current += 1

        logger.debug("Committing session...")
        session.commit()
        logger.info("Result data import complete")


def import_global_result(
    session,
    cache_repo,
    result_type: str,
    df: pd.DataFrame,
    mappings: ImportMappings,
) -> None:
    """Import global result data into GlobalResultsCache."""
    from database.models import GlobalResultsCache
    from config.result_config import RESULT_CONFIGS

    result_set_id = list(mappings.result_set_mapping.values())[0]
    story_mapping = mappings.story_mapping
    project_id = mappings.project_id

    config = RESULT_CONFIGS.get(result_type)
    if not config:
        logger.warning("Unknown result type %s, skipping", result_type)
        return

    base_type = result_type.split("_")[0] if "_" in result_type else result_type
    direction = result_type.split("_")[1] if "_" in result_type else None

    logger.debug("Importing %s -> base_type: %s, direction: %s", result_type, base_type, direction)
    logger.debug("Story mapping has %s stories", len(story_mapping))

    load_case_mapping = mappings.load_case_mapping

    entries_added = 0
    normalized_total = 0
    for idx, row in df.iterrows():
        story_name = row["Story"]
        story_id = story_mapping.get(story_name)

        if not story_id:
            logger.warning("Story '%s' not found in mapping, skipping", story_name)
            continue

        results_matrix = {}
        for col in df.columns:
            if col != "Story":
                results_matrix[col] = float(row[col]) if pd.notna(row[col]) else None

        cache_entry = GlobalResultsCache(
            project_id=project_id,
            result_set_id=result_set_id,
            story_id=story_id,
            result_type=base_type,
            story_sort_order=idx,
            results_matrix=results_matrix,
        )
        session.add(cache_entry)
        entries_added += 1

        for load_case_name, value in results_matrix.items():
            load_case_id = load_case_mapping.get(load_case_name)
            if not load_case_id or value is None:
                continue

            try:
                create_normalized_result(
                    session,
                    base_type,
                    direction,
                    project_id,
                    result_set_id,
                    story_id,
                    load_case_id,
                    value,
                    story_sort_order=idx,
                )
                normalized_total += 1
            except Exception:
                logger.exception("Error creating normalized result for %s", result_type)

    logger.debug(
        "Added %s cache entries and %s normalized entries for %s",
        entries_added,
        normalized_total,
        result_type,
    )


def create_normalized_result(
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
    from database.models import StoryDrift, StoryAcceleration, StoryForce, StoryDisplacement

    if not direction:
        logger.warning("No direction provided for %s, skipping normalized table creation", result_type)
        return

    if result_type == "Drifts":
        entry = StoryDrift(
            story_id=story_id,
            load_case_id=load_case_id,
            direction=direction,
            drift=value,
            story_sort_order=story_sort_order,
        )
        session.add(entry)
    elif result_type == "Accelerations":
        entry = StoryAcceleration(
            story_id=story_id,
            load_case_id=load_case_id,
            direction=direction,
            acceleration=value,
            story_sort_order=story_sort_order,
        )
        session.add(entry)
    elif result_type == "Forces":
        entry = StoryForce(
            story_id=story_id,
            load_case_id=load_case_id,
            direction=direction,
            force=value,
            story_sort_order=story_sort_order,
        )
        session.add(entry)
    elif result_type == "Displacements":
        entry = StoryDisplacement(
            story_id=story_id,
            load_case_id=load_case_id,
            direction=direction,
            displacement=value,
            story_sort_order=story_sort_order,
        )
        session.add(entry)


def import_element_result(
    session,
    element_cache_repo,
    result_type: str,
    df: pd.DataFrame,
    mappings: ImportMappings,
) -> None:
    """Import element result data into ElementResultsCache."""
    from database.models import ElementResultsCache

    result_set_id = list(mappings.result_set_mapping.values())[0]
    story_mapping = mappings.story_mapping
    element_mapping = mappings.element_mapping
    project_id = mappings.project_id

    for idx, row in df.iterrows():
        element_name = row["Element"]
        story_name = row["Story"]

        element_id = element_mapping.get(element_name)
        story_id = story_mapping.get(story_name)

        if not element_id or not story_id:
            continue

        results_matrix = {}
        for col in df.columns:
            if col not in ["Element", "Story"]:
                results_matrix[col] = float(row[col]) if pd.notna(row[col]) else None

        cache_entry = ElementResultsCache(
            project_id=project_id,
            result_set_id=result_set_id,
            element_id=element_id,
            story_id=story_id,
            result_type=result_type,
            story_sort_order=idx,
            results_matrix=results_matrix,
        )
        session.add(cache_entry)


__all__ = [
    "import_result_data",
    "import_global_result",
    "create_normalized_result",
    "import_element_result",
]
