"""Metadata assembly helpers for project export."""

from __future__ import annotations

from typing import Dict, List

from database.catalog_base import get_catalog_session
from database.catalog_repository import CatalogProjectRepository
from services.project_service import get_project_summary
from database.models import ResultSet, ResultCategory, LoadCase, Story, Element


class ExportMetadataBuilder:
    """Builds project metadata structure for export."""

    def __init__(self, context, result_service) -> None:
        self.context = context
        self.result_service = result_service

    def build_metadata(self) -> dict:
        """Gather project metadata for export."""
        catalog_project = self._get_catalog_project()
        summary = get_project_summary(self.context)

        with self.context.session() as session:
            result_sets = session.query(ResultSet).filter(
                ResultSet.project_id == self.result_service.project_id
            ).all()
            result_set_ids = [rs.id for rs in result_sets]
            result_categories = session.query(ResultCategory).filter(
                ResultCategory.result_set_id.in_(result_set_ids)
            ).all() if result_set_ids else []
            load_cases = session.query(LoadCase).filter(
                LoadCase.project_id == self.result_service.project_id
            ).all()
            stories = session.query(Story).filter(
                Story.project_id == self.result_service.project_id
            ).order_by(Story.sort_order).all()
            elements = session.query(Element).filter(
                Element.project_id == self.result_service.project_id
            ).all()

        return {
            "project": {
                "name": catalog_project.name,
                "slug": catalog_project.slug,
                "description": catalog_project.description,
                "db_path": str(self.context.db_path),
                "summary": summary,
            },
            "result_sets": result_sets,
            "result_categories": result_categories,
            "load_cases": load_cases,
            "stories": stories,
            "elements": elements,
        }

    def _get_catalog_project(self):
        catalog_session = get_catalog_session()
        try:
            catalog_repo = CatalogProjectRepository(catalog_session)
            catalog_project = catalog_repo.get_by_slug(self.context.slug)
            if not catalog_project:
                raise ValueError(f"Project '{self.context.slug}' not found in catalog")
            return catalog_project
        finally:
            catalog_session.close()
