"""Import normalized/cache data from JSON payload in IMPORT_DATA sheet."""

from __future__ import annotations

import logging
from typing import Callable, Optional

from services.import_models import ImportMappings
from services.project_service import ProjectContext
from database.models import (
    StoryDrift,
    StoryAcceleration,
    StoryForce,
    StoryDisplacement,
    AbsoluteMaxMinDrift,
    QuadRotation,
    WallShear,
    GlobalResultsCache,
    ElementResultsCache,
)

logger = logging.getLogger(__name__)


def import_database_from_json(
    context: ProjectContext,
    import_metadata: dict,
    mappings: ImportMappings,
    progress_callback: Optional[Callable] = None,
) -> None:
    """Import complete per-project database from JSON in IMPORT_DATA sheet."""
    normalized_data = import_metadata.get("normalized_data", {})
    cache_data = import_metadata.get("cache_data", {})

    with context.session() as session:
        story_mapping = mappings.story_mapping
        load_case_mapping = mappings.load_case_mapping
        result_set_mapping = mappings.result_set_mapping
        result_category_mapping = mappings.result_category_mapping
        element_mapping = mappings.element_mapping
        project_id = mappings.project_id

        # Import normalized tables
        if progress_callback:
            progress_callback("Importing story drifts...", 0, 9)

        drift_records = normalized_data.get("story_drifts", [])
        logger.debug("Found %s story_drifts records in JSON", len(drift_records))
        drift_count = 0

        for drift_data in drift_records:
            story_id = story_mapping.get(drift_data["story_name"])
            load_case_id = load_case_mapping.get(drift_data["load_case_name"])
            if story_id and load_case_id:
                entry = StoryDrift(
                    story_id=story_id,
                    load_case_id=load_case_id,
                    direction=drift_data["direction"],
                    drift=drift_data["drift"],
                    max_drift=drift_data.get("max_drift"),
                    min_drift=drift_data.get("min_drift"),
                    story_sort_order=drift_data.get("story_sort_order", 0),
                )
                session.add(entry)
                drift_count += 1

        logger.debug("Imported %s story_drifts records", drift_count)

        if progress_callback:
            progress_callback("Importing story accelerations...", 1, 9)

        accel_records = normalized_data.get("story_accelerations", [])
        logger.debug("Found %s story_accelerations records in JSON", len(accel_records))
        accel_count = 0

        for accel_data in accel_records:
            story_id = story_mapping.get(accel_data["story_name"])
            load_case_id = load_case_mapping.get(accel_data["load_case_name"])
            result_set_name = accel_data.get("result_set_name")
            result_category_name = accel_data.get("result_category_name")
            result_category_id = None
            if result_set_name and result_category_name:
                result_category_id = result_category_mapping.get(
                    (result_set_name, result_category_name)
                )

            if story_id and load_case_id:
                entry = StoryAcceleration(
                    story_id=story_id,
                    load_case_id=load_case_id,
                    result_category_id=result_category_id,
                    direction=accel_data["direction"],
                    acceleration=accel_data["acceleration"],
                    max_acceleration=accel_data.get("max_acceleration"),
                    min_acceleration=accel_data.get("min_acceleration"),
                    story_sort_order=accel_data.get("story_sort_order", 0),
                )
                session.add(entry)
                accel_count += 1
            else:
                if not story_id:
                    logger.warning("Missing story_id for %s", accel_data.get("story_name"))
                if not load_case_id:
                    logger.warning("Missing load_case_id for %s", accel_data.get("load_case_name"))

        logger.debug("Imported %s story_accelerations records", accel_count)

        if progress_callback:
            progress_callback("Importing story forces...", 2, 6)

        force_records = normalized_data.get("story_forces", [])
        logger.debug("Found %s story_forces records in JSON", len(force_records))
        force_count = 0

        for force_data in force_records:
            story_id = story_mapping.get(force_data["story_name"])
            load_case_id = load_case_mapping.get(force_data["load_case_name"])
            result_set_name = force_data.get("result_set_name")
            result_category_name = force_data.get("result_category_name")
            result_category_id = None
            if result_set_name and result_category_name:
                result_category_id = result_category_mapping.get(
                    (result_set_name, result_category_name)
                )

            if story_id and load_case_id:
                entry = StoryForce(
                    story_id=story_id,
                    load_case_id=load_case_id,
                    result_category_id=result_category_id,
                    direction=force_data["direction"],
                    location=force_data.get("location"),
                    force=force_data["force"],
                    max_force=force_data.get("max_force"),
                    min_force=force_data.get("min_force"),
                    story_sort_order=force_data.get("story_sort_order", 0),
                )
                session.add(entry)
                force_count += 1

        logger.debug("Imported %s story_forces records", force_count)

        if progress_callback:
            progress_callback("Importing story displacements...", 3, 6)

        disp_records = normalized_data.get("story_displacements", [])
        logger.debug("Found %s story_displacements records in JSON", len(disp_records))
        disp_count = 0

        for disp_data in disp_records:
            story_id = story_mapping.get(disp_data["story_name"])
            load_case_id = load_case_mapping.get(disp_data["load_case_name"])
            result_set_name = disp_data.get("result_set_name")
            result_category_name = disp_data.get("result_category_name")
            result_category_id = None
            if result_set_name and result_category_name:
                result_category_id = result_category_mapping.get(
                    (result_set_name, result_category_name)
                )

            if story_id and load_case_id:
                entry = StoryDisplacement(
                    story_id=story_id,
                    load_case_id=load_case_id,
                    result_category_id=result_category_id,
                    direction=disp_data["direction"],
                    displacement=disp_data["displacement"],
                    max_displacement=disp_data.get("max_displacement"),
                    min_displacement=disp_data.get("min_displacement"),
                    story_sort_order=disp_data.get("story_sort_order", 0),
                )
                session.add(entry)
                disp_count += 1

        logger.debug("Imported %s story_displacements records", disp_count)

        # Import absolute max/min drifts
        if progress_callback:
            progress_callback("Importing max/min drifts...", 4, 9)

        maxmin_records = normalized_data.get("absolute_maxmin_drifts", [])
        logger.debug("Found %s absolute_maxmin_drifts records in JSON", len(maxmin_records))
        imported_count = 0

        for maxmin_data in maxmin_records:
            result_set_id = result_set_mapping.get(maxmin_data["result_set_name"])
            story_id = story_mapping.get(maxmin_data["story_name"])
            load_case_id = load_case_mapping.get(maxmin_data["load_case_name"])
            if result_set_id and story_id and load_case_id:
                entry = AbsoluteMaxMinDrift(
                    project_id=project_id,
                    result_set_id=result_set_id,
                    story_id=story_id,
                    load_case_id=load_case_id,
                    direction=maxmin_data["direction"],
                    absolute_max_drift=maxmin_data["absolute_max_drift"],
                    sign=maxmin_data["sign"],
                    original_max=maxmin_data.get("original_max"),
                    original_min=maxmin_data.get("original_min"),
                )
                session.add(entry)
                imported_count += 1

        logger.debug("Imported %s absolute_maxmin_drifts records", imported_count)

        # Import quad rotations
        if progress_callback:
            progress_callback("Importing quad rotations...", 5, 9)

        quad_records = normalized_data.get("quad_rotations", [])
        logger.debug("Found %s quad_rotations records in JSON", len(quad_records))
        quad_count = 0

        for quad_data in quad_records:
            element_id = element_mapping.get(quad_data["element_name"])
            story_id = story_mapping.get(quad_data["story_name"])
            load_case_id = load_case_mapping.get(quad_data["load_case_name"])
            if element_id and story_id and load_case_id:
                entry = QuadRotation(
                    element_id=element_id,
                    story_id=story_id,
                    load_case_id=load_case_id,
                    rotation=quad_data["rotation"],
                    max_rotation=quad_data.get("max_rotation"),
                    min_rotation=quad_data.get("min_rotation"),
                    story_sort_order=quad_data.get("story_sort_order", 0),
                )
                session.add(entry)
                quad_count += 1

        logger.debug("Imported %s quad_rotations records", quad_count)

        # Import wall shears
        if progress_callback:
            progress_callback("Importing wall shears...", 6, 9)

        wall_records = normalized_data.get("wall_shears", [])
        logger.debug("Found %s wall_shears records in JSON", len(wall_records))
        wall_count = 0

        for wall_data in wall_records:
            element_id = element_mapping.get(wall_data["element_name"])
            story_id = story_mapping.get(wall_data["story_name"])
            load_case_id = load_case_mapping.get(wall_data["load_case_name"])
            if element_id and story_id and load_case_id:
                entry = WallShear(
                    element_id=element_id,
                    story_id=story_id,
                    load_case_id=load_case_id,
                    direction=wall_data["direction"],
                    location=wall_data.get("location"),
                    force=wall_data["force"],
                    max_force=wall_data.get("max_force"),
                    min_force=wall_data.get("min_force"),
                    story_sort_order=wall_data.get("story_sort_order", 0),
                )
                session.add(entry)
                wall_count += 1

        logger.debug("Imported %s wall_shears records", wall_count)

        # Import cache tables
        if progress_callback:
            progress_callback("Importing global cache...", 7, 9)

        global_cache_records = cache_data.get("global_results_cache", [])
        logger.debug(
            "Found %s global_results_cache records in JSON", len(global_cache_records)
        )
        global_cache_count = 0

        for cache_data_row in global_cache_records:
            result_set_id = result_set_mapping.get(cache_data_row["result_set_name"])
            story_id = story_mapping.get(cache_data_row["story_name"])
            if result_set_id and story_id:
                entry = GlobalResultsCache(
                    project_id=project_id,
                    result_set_id=result_set_id,
                    story_id=story_id,
                    result_type=cache_data_row["result_type"],
                    story_sort_order=cache_data_row.get("story_sort_order", 0),
                    results_matrix=cache_data_row["results_matrix"],
                )
                session.add(entry)
                global_cache_count += 1

        logger.debug("Imported %s global_results_cache records", global_cache_count)

        if progress_callback:
            progress_callback("Importing element cache...", 8, 9)

        element_cache_records = cache_data.get("element_results_cache", [])
        logger.debug(
            "Found %s element_results_cache records in JSON", len(element_cache_records)
        )
        element_cache_count = 0

        for cache_data_row in element_cache_records:
            result_set_id = result_set_mapping.get(cache_data_row["result_set_name"])
            element_id = element_mapping.get(cache_data_row["element_name"])
            story_id = story_mapping.get(cache_data_row["story_name"])
            if result_set_id and element_id and story_id:
                entry = ElementResultsCache(
                    project_id=project_id,
                    result_set_id=result_set_id,
                    element_id=element_id,
                    story_id=story_id,
                    result_type=cache_data_row["result_type"],
                    story_sort_order=cache_data_row.get("story_sort_order", 0),
                    results_matrix=cache_data_row["results_matrix"],
                )
                session.add(entry)
                element_cache_count += 1

        logger.debug("Imported %s element_results_cache records", element_cache_count)

        session.commit()
        logger.info("Database import complete")


__all__ = ["import_database_from_json"]
