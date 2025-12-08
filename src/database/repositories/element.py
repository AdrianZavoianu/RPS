"""Element repository for Element operations."""

from typing import List, Optional
from sqlalchemy import and_

from ..models import Element
from ..base_repository import BaseRepository


class ElementRepository(BaseRepository[Element]):
    """Repository for Element operations."""

    model = Element

    def create(
        self,
        project_id: int,
        element_type: str,
        name: str,
        unique_name: Optional[str] = None,
        story_id: Optional[int] = None,
    ) -> Element:
        """Create a new element."""
        return super().create(
            project_id=project_id,
            element_type=element_type,
            name=name,
            unique_name=unique_name,
            story_id=story_id,
        )

    def get_or_create(
        self,
        project_id: int,
        element_type: str,
        unique_name: str,
        name: Optional[str] = None,
        story_id: Optional[int] = None,
    ) -> Element:
        """Get existing element or create new one."""
        element = (
            self.session.query(Element)
            .filter(
                and_(
                    Element.project_id == project_id,
                    Element.element_type == element_type,
                    Element.unique_name == unique_name,
                )
            )
            .first()
        )
        if not element:
            element = self.create(
                project_id=project_id,
                element_type=element_type,
                name=name or unique_name,
                unique_name=unique_name,
                story_id=story_id,
            )
        return element

    def get_by_project(self, project_id: int, element_type: Optional[str] = None) -> List[Element]:
        """Get all elements for a project, optionally filtered by type."""
        query = self.session.query(Element).filter(Element.project_id == project_id)
        if element_type:
            query = query.filter(Element.element_type == element_type)
        return query.order_by(Element.name.asc()).all()

    def get_by_id(self, element_id: int) -> Optional[Element]:
        """Get element by ID."""
        return super().get_by_id(element_id)
