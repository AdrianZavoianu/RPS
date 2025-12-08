"""Project repository for Project operations."""

from typing import List, Optional

from ..models import Project
from ..base_repository import BaseRepository


class ProjectRepository(BaseRepository[Project]):
    """Repository for Project operations."""

    model = Project

    def create(self, name: str, description: Optional[str] = None) -> Project:
        return super().create(name=name, description=description)

    def get_by_name(self, name: str) -> Optional[Project]:
        return self.session.query(Project).filter(Project.name == name).first()

    def get_all(self) -> List[Project]:
        return self.session.query(Project).order_by(Project.created_at.desc()).all()

    def delete(self, project_id: int) -> bool:
        project = self.get_by_id(project_id)
        if project:
            super().delete(project)
            return True
        return False
