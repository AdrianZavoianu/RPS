"""Metadata import helpers: project, result set, categories, and stats scaffold."""

from __future__ import annotations

from typing import Dict, Optional, Tuple

from sqlalchemy.orm import Session

from database.repositories import ProjectRepository, ResultSetRepository, ResultCategoryRepository


class MetadataImporter:
    """Creates/loads project + result set + global category and initializes stats."""

    def __init__(self, *, session: Session, project_name: str, result_set_name: str) -> None:
        self.session = session
        self.project_name = project_name
        self.result_set_name = result_set_name

    def ensure_project_and_result_set(self) -> Tuple[Dict[str, int], int, int]:
        """Ensure project/result set/global category exist and return stats/result ids."""
        project_repo = ProjectRepository(self.session)
        project = project_repo.get_by_name(self.project_name)
        if not project:
            project = project_repo.create(
                name=self.project_name,
                description=f"Imported from {self.result_set_name}",
            )

        result_set_repo = ResultSetRepository(self.session)
        result_set = result_set_repo.get_or_create(
            project_id=project.id,
            name=self.result_set_name,
        )

        category_repo = ResultCategoryRepository(self.session)
        result_category = category_repo.get_or_create(
            result_set_id=result_set.id,
            category_name="Envelopes",
            category_type="Global",
        )

        stats = self._initial_stats()
        stats["project"] = project.name
        stats["project_id"] = project.id
        stats["result_set_id"] = result_set.id

        return stats, project.id, result_category.id

    def _initial_stats(self) -> Dict[str, int]:
        """Return base stats structure for imports."""
        return {
            "project": None,
            "project_id": None,
            "result_set_id": None,
            "load_cases": 0,
            "stories": 0,
            "drifts": 0,
            "accelerations": 0,
            "forces": 0,
            "displacements": 0,
            "pier_forces": 0,
            "piers": 0,
            "column_forces": 0,
            "column_axials": 0,
            "column_rotations": 0,
            "columns": 0,
            "beam_rotations": 0,
            "beams": 0,
            "soil_pressures": 0,
            "errors": [],
        }
