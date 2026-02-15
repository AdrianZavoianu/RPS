"""Metadata import helpers for Excel project import."""

from __future__ import annotations

import logging

from services.import_models import ImportMappings
from services.project_service import ProjectContext
from database.repositories import (
    ElementRepository,
    LoadCaseRepository,
    ProjectRepository,
    ResultSetRepository,
    StoryRepository,
    ResultCategoryRepository,
)

logger = logging.getLogger(__name__)


def import_metadata(context: ProjectContext, import_metadata: dict) -> ImportMappings:
    """Import metadata tables (result sets, load cases, stories, elements)."""
    with context.session() as session:
        project_repo = ProjectRepository(session)
        project = project_repo.get_by_name(context.name)

        if not project:
            raise ValueError(f"Project '{context.name}' not found in database")

        # Import result sets
        result_set_repo = ResultSetRepository(session)
        result_set_mapping: dict[str, int] = {}
        logger.debug("Importing %s result sets", len(import_metadata.get("result_sets", [])))
        for rs_data in import_metadata.get("result_sets", []):
            logger.debug("Creating result set: %s", rs_data["name"])
            rs = result_set_repo.create(
                project_id=project.id,
                name=rs_data["name"],
                description=rs_data.get("description", ""),
            )
            result_set_mapping[rs_data["name"]] = rs.id

        # Import result categories
        result_category_repo = ResultCategoryRepository(session)
        result_category_mapping: dict[tuple[str, str], int] = {}
        for rc_data in import_metadata.get("result_categories", []):
            result_set_id = result_set_mapping.get(rc_data.get("result_set_name"))
            if result_set_id:
                rc = result_category_repo.create(
                    result_set_id=result_set_id,
                    category_name=rc_data["category_name"],
                    category_type=rc_data.get("category_type", "Global"),
                )
                # Use composite key: (result_set_name, category_name) -> category_id
                key = (rc_data.get("result_set_name"), rc_data["category_name"])
                result_category_mapping[key] = rc.id

        # Import load cases
        load_case_repo = LoadCaseRepository(session)
        load_case_mapping: dict[str, int] = {}
        for lc_data in import_metadata.get("load_cases", []):
            lc = load_case_repo.create(
                project_id=project.id,
                name=lc_data["name"],
                description=lc_data.get("description", ""),
            )
            load_case_mapping[lc_data["name"]] = lc.id

        # Import stories
        story_repo = StoryRepository(session)
        story_mapping: dict[str, int] = {}
        for s_data in import_metadata.get("stories", []):
            s = story_repo.create(
                project_id=project.id,
                name=s_data["name"],
                sort_order=s_data.get("sort_order", 0),
                elevation=s_data.get("elevation", 0.0),
            )
            story_mapping[s_data["name"]] = s.id

        # Import elements
        element_repo = ElementRepository(session)
        element_mapping: dict[str, int] = {}
        for e_data in import_metadata.get("elements", []):
            e = element_repo.create(
                project_id=project.id,
                name=e_data["name"],
                element_type=e_data.get("element_type", "Wall"),
                unique_name=e_data.get("unique_name", ""),
            )
            element_mapping[e_data["name"]] = e.id

        session.commit()

        return ImportMappings(
            project_id=project.id,
            result_set_mapping=result_set_mapping,
            result_category_mapping=result_category_mapping,
            load_case_mapping=load_case_mapping,
            story_mapping=story_mapping,
            element_mapping=element_mapping,
        )


__all__ = ["import_metadata"]
