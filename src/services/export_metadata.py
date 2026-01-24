"""Metadata assembly helpers for project export."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Dict, List

from database.session import get_catalog_session
from database.catalog_repository import CatalogProjectRepository
from services.project_service import get_project_summary
from database.models import ResultSet, ResultCategory, LoadCase, Story, Element


class ExportMetadataBuilder:
    """Builds project metadata structure for export."""

    def __init__(self, context, result_service) -> None:
        self.context = context
        self.result_service = result_service

    def build_metadata(self) -> dict:
        """Gather project metadata for export.

        Returns plain objects (SimpleNamespace) instead of ORM objects to avoid
        detached instance errors when the session closes.
        """
        catalog_project = self._get_catalog_project()
        summary = get_project_summary(self.context)

        session = self.context.session()
        try:
            result_sets_orm = session.query(ResultSet).filter(
                ResultSet.project_id == self.result_service.project_id
            ).all()
            result_set_ids = [rs.id for rs in result_sets_orm]
            result_categories_orm = session.query(ResultCategory).filter(
                ResultCategory.result_set_id.in_(result_set_ids)
            ).all() if result_set_ids else []
            load_cases_orm = session.query(LoadCase).filter(
                LoadCase.project_id == self.result_service.project_id
            ).all()
            stories_orm = session.query(Story).filter(
                Story.project_id == self.result_service.project_id
            ).order_by(Story.sort_order).all()
            elements_orm = session.query(Element).filter(
                Element.project_id == self.result_service.project_id
            ).all()

            # Convert ORM objects to plain objects to avoid detached instance errors
            result_sets = [
                SimpleNamespace(
                    id=rs.id, name=rs.name, description=rs.description,
                    created_at=rs.created_at, analysis_type=rs.analysis_type
                )
                for rs in result_sets_orm
            ]
            result_categories = [
                SimpleNamespace(
                    id=rc.id, category_name=rc.category_name,
                    result_set_id=rc.result_set_id, category_type=rc.category_type
                )
                for rc in result_categories_orm
            ]
            load_cases = [
                SimpleNamespace(id=lc.id, name=lc.name, description=lc.description)
                for lc in load_cases_orm
            ]
            stories = [
                SimpleNamespace(
                    id=s.id, name=s.name, sort_order=s.sort_order, elevation=s.elevation
                )
                for s in stories_orm
            ]
            elements = [
                SimpleNamespace(
                    id=e.id, name=e.name, unique_name=e.unique_name, element_type=e.element_type
                )
                for e in elements_orm
            ]
        finally:
            session.close()

        return {
            "catalog_project": catalog_project,
            "summary": summary,
            "project": {
                "name": catalog_project.name,
                "slug": catalog_project.slug,
                "description": catalog_project.description,
                "db_path": str(self.context.db_path),
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
            # Convert to SimpleNamespace to avoid detached instance errors
            return SimpleNamespace(
                name=catalog_project.name,
                slug=catalog_project.slug,
                description=catalog_project.description,
                created_at=catalog_project.created_at,
            )
        finally:
            catalog_session.close()
