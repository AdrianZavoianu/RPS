"""Catalog repository helpers."""

from datetime import datetime
from pathlib import Path
from typing import Optional, List

from sqlalchemy.orm import Session

from .catalog_models import CatalogProject


class CatalogProjectRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_all(self) -> List[CatalogProject]:
        return (
            self.session.query(CatalogProject)
            .order_by(CatalogProject.created_at.desc())
            .all()
        )

    def get_by_name(self, name: str) -> Optional[CatalogProject]:
        return (
            self.session.query(CatalogProject)
            .filter(CatalogProject.name == name)
            .first()
        )

    def get_by_slug(self, slug: str) -> Optional[CatalogProject]:
        return (
            self.session.query(CatalogProject)
            .filter(CatalogProject.slug == slug)
            .first()
        )

    def create(self, name: str, slug: str, db_path: Path, description: Optional[str] = None) -> CatalogProject:
        project = CatalogProject(
            name=name,
            slug=slug,
            db_path=str(db_path),
            description=description,
        )
        self.session.add(project)
        self.session.commit()
        self.session.refresh(project)
        return project

    def update_last_opened(self, project: CatalogProject) -> CatalogProject:
        project.last_opened = datetime.utcnow()
        self.session.commit()
        self.session.refresh(project)
        return project

    def delete(self, project: CatalogProject) -> None:
        self.session.delete(project)
        self.session.commit()
