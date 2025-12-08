"""Result set repositories for ResultSet and ComparisonSet operations."""

from typing import List, Optional
from sqlalchemy import and_

from ..models import ResultSet, ComparisonSet
from ..base_repository import BaseRepository


class ResultSetRepository(BaseRepository[ResultSet]):
    """Repository for ResultSet operations."""

    model = ResultSet

    def create(
        self,
        project_id: int,
        name: str,
        description: Optional[str] = None,
        result_category: Optional[str] = None,
    ) -> ResultSet:
        result_set = super().create(
            project_id=project_id,
            name=name,
            description=description,
        )
        if result_category is not None:
            setattr(result_set, "result_category", result_category)
        return result_set

    def get_or_create(self, project_id: int, name: str) -> ResultSet:
        result_set = (
            self.session.query(ResultSet)
            .filter(and_(ResultSet.project_id == project_id, ResultSet.name == name))
            .first()
        )
        if not result_set:
            result_set = self.create(project_id, name)
        return result_set

    def check_duplicate(self, project_id: int, name: str) -> bool:
        return (
            self.session.query(ResultSet)
            .filter(and_(ResultSet.project_id == project_id, ResultSet.name == name))
            .first()
        ) is not None

    def get_by_project(self, project_id: int) -> List[ResultSet]:
        """Get all result sets for a project."""
        return (
            self.session.query(ResultSet)
            .filter(ResultSet.project_id == project_id)
            .order_by(ResultSet.name)
            .all()
        )


class ComparisonSetRepository(BaseRepository[ComparisonSet]):
    """Repository for ComparisonSet operations."""

    model = ComparisonSet

    def create(
        self,
        project_id: int,
        name: str,
        result_set_ids: List[int],
        result_types: List[str],
        description: Optional[str] = None,
    ) -> ComparisonSet:
        """Create a new comparison set."""
        comparison_set = super().create(
            project_id=project_id,
            name=name,
            result_set_ids=result_set_ids,
            result_types=result_types,
            description=description,
        )
        return comparison_set

    def get_by_project(self, project_id: int) -> List[ComparisonSet]:
        """Get all comparison sets for a project."""
        return (
            self.session.query(ComparisonSet)
            .filter(ComparisonSet.project_id == project_id)
            .order_by(ComparisonSet.name)
            .all()
        )

    def check_duplicate(self, project_id: int, name: str) -> bool:
        """Check if a comparison set with this name already exists."""
        return (
            self.session.query(ComparisonSet)
            .filter(and_(ComparisonSet.project_id == project_id, ComparisonSet.name == name))
            .first()
        ) is not None
