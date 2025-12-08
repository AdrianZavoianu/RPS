"""Load case repository for LoadCase operations."""

from typing import List, Optional
from sqlalchemy import and_

from ..models import LoadCase
from ..base_repository import BaseRepository


class LoadCaseRepository(BaseRepository[LoadCase]):
    """Repository for LoadCase operations."""

    model = LoadCase

    def create(
        self,
        project_id: int,
        name: str,
        case_type: Optional[str] = None,
        description: Optional[str] = None,
    ) -> LoadCase:
        return super().create(
            project_id=project_id,
            name=name,
            case_type=case_type,
            description=description,
        )

    def get_or_create(
        self, project_id: int, name: str, case_type: Optional[str] = None
    ) -> LoadCase:
        """Get existing load case or create new one."""
        load_case = (
            self.session.query(LoadCase)
            .filter(and_(LoadCase.project_id == project_id, LoadCase.name == name))
            .first()
        )
        if not load_case:
            load_case = self.create(project_id, name, case_type)
        return load_case

    def get_by_project(self, project_id: int) -> List[LoadCase]:
        return (
            self.session.query(LoadCase)
            .filter(LoadCase.project_id == project_id)
            .order_by(LoadCase.name)
            .all()
        )
