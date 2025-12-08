"""Story repositories for Story and story-level result operations."""

from typing import List, Optional
from sqlalchemy import and_
from sqlalchemy.orm import Session

from ..models import Story, StoryDrift, StoryAcceleration, StoryForce, StoryDisplacement
from ..base_repository import BaseRepository


class StoryRepository(BaseRepository[Story]):
    """Repository for Story operations."""

    model = Story

    def create(
        self,
        project_id: int,
        name: str,
        elevation: Optional[float] = None,
        sort_order: Optional[int] = None,
    ) -> Story:
        return super().create(
            project_id=project_id,
            name=name,
            elevation=elevation,
            sort_order=sort_order,
        )

    def get_or_create(
        self, project_id: int, name: str, sort_order: Optional[int] = None
    ) -> Story:
        """Get existing story or create new one.

        Note: sort_order is only set during initial creation. Once a story exists,
        its sort_order is preserved to maintain canonical ordering from the first sheet.
        This prevents later imports (e.g., Quad Rotations) from changing the display
        order of all result types.
        """
        story = (
            self.session.query(Story)
            .filter(and_(Story.project_id == project_id, Story.name == name))
            .first()
        )
        if not story:
            story = self.create(project_id, name, sort_order=sort_order)
        # Do NOT update sort_order if story already exists - preserve canonical order
        return story

    def get_by_project(self, project_id: int) -> List[Story]:
        """Get all stories for a project, ordered by sort_order (bottom to top).

        Returns stories in ascending sort_order (0=ground, increasing with height).
        This matches Excel source order where stories are listed bottom-to-top.
        """
        return (
            self.session.query(Story)
            .filter(Story.project_id == project_id)
            .order_by(Story.sort_order.asc())
            .all()
        )


class StoryDriftDataRepository(BaseRepository[StoryDrift]):
    model = StoryDrift

    def create_drift(
        self,
        story_id: int,
        load_case_id: int,
        direction: str,
        drift: float,
        max_drift: Optional[float] = None,
        min_drift: Optional[float] = None,
    ) -> StoryDrift:
        return super().create(
            story_id=story_id,
            load_case_id=load_case_id,
            direction=direction,
            drift=drift,
            max_drift=max_drift,
            min_drift=min_drift,
        )

    def get_by_project(self, project_id: int) -> List[StoryDrift]:
        """Get all drifts for a project."""
        return (
            self.session.query(StoryDrift)
            .join(Story)
            .filter(Story.project_id == project_id)
            .all()
        )

    def get_drifts_by_case(
        self, load_case_id: int, direction: Optional[str] = None
    ) -> List[StoryDrift]:
        """Get drifts for a specific load case, optionally filtered by direction."""
        query = self.session.query(StoryDrift).filter(
            StoryDrift.load_case_id == load_case_id
        )
        if direction:
            query = query.filter(StoryDrift.direction == direction)
        return query.all()

    def bulk_create(self, drifts: List[StoryDrift]):
        """Bulk insert drift records for better performance."""
        if not drifts:
            return
        self.session.bulk_save_objects(drifts)
        self.session.commit()


class StoryAccelerationDataRepository(BaseRepository[StoryAcceleration]):
    model = StoryAcceleration

    def create_acceleration(
        self,
        story_id: int,
        load_case_id: int,
        direction: str,
        acceleration: float,
        max_acceleration: Optional[float] = None,
        min_acceleration: Optional[float] = None,
    ) -> StoryAcceleration:
        return super().create(
            story_id=story_id,
            load_case_id=load_case_id,
            direction=direction,
            acceleration=acceleration,
            max_acceleration=max_acceleration,
            min_acceleration=min_acceleration,
        )

    def bulk_create(self, accelerations: List[StoryAcceleration]):
        """Bulk insert acceleration records."""
        if not accelerations:
            return
        self.session.bulk_save_objects(accelerations)
        self.session.commit()


class StoryForceDataRepository(BaseRepository[StoryForce]):
    model = StoryForce

    def create_force(
        self,
        story_id: int,
        load_case_id: int,
        direction: str,
        force: float,
        location: Optional[str] = None,
        max_force: Optional[float] = None,
        min_force: Optional[float] = None,
    ) -> StoryForce:
        return super().create(
            story_id=story_id,
            load_case_id=load_case_id,
            direction=direction,
            location=location,
            force=force,
            max_force=max_force,
            min_force=min_force,
        )

    def bulk_create(self, forces: List[StoryForce]):
        """Bulk insert force records."""
        if not forces:
            return
        self.session.bulk_save_objects(forces)
        self.session.commit()


class StoryDisplacementDataRepository(BaseRepository[StoryDisplacement]):
    model = StoryDisplacement

    def create_displacement(
        self,
        story_id: int,
        load_case_id: int,
        direction: str,
        displacement: float,
        max_displacement: Optional[float] = None,
        min_displacement: Optional[float] = None,
    ) -> StoryDisplacement:
        return super().create(
            story_id=story_id,
            load_case_id=load_case_id,
            direction=direction,
            displacement=displacement,
            max_displacement=max_displacement,
            min_displacement=min_displacement,
        )

    def bulk_create(self, displacements: List[StoryDisplacement]):
        """Bulk insert displacement records."""
        if not displacements:
            return
        self.session.bulk_save_objects(displacements)
        self.session.commit()


class ResultRepository:
    """Facade over story-level result repositories."""

    def __init__(self, session: Session):
        self.drifts = StoryDriftDataRepository(session)
        self.accelerations = StoryAccelerationDataRepository(session)
        self.forces = StoryForceDataRepository(session)
        self.displacements = StoryDisplacementDataRepository(session)

    def create_story_drift(self, *args, **kwargs) -> StoryDrift:
        return self.drifts.create_drift(*args, **kwargs)

    def create_story_acceleration(self, *args, **kwargs) -> StoryAcceleration:
        return self.accelerations.create_acceleration(*args, **kwargs)

    def create_story_force(self, *args, **kwargs) -> StoryForce:
        return self.forces.create_force(*args, **kwargs)

    def create_story_displacement(self, *args, **kwargs) -> StoryDisplacement:
        return self.displacements.create_displacement(*args, **kwargs)

    def bulk_create_drifts(self, drifts: List[StoryDrift]) -> None:
        self.drifts.bulk_create(drifts)

    def bulk_create_accelerations(self, accelerations: List[StoryAcceleration]) -> None:
        self.accelerations.bulk_create(accelerations)

    def bulk_create_forces(self, forces: List[StoryForce]) -> None:
        self.forces.bulk_create(forces)

    def bulk_create_displacements(self, displacements: List[StoryDisplacement]) -> None:
        self.displacements.bulk_create(displacements)

    def get_drifts_by_project(self, project_id: int) -> List[StoryDrift]:
        return self.drifts.get_by_project(project_id)

    def get_drifts_by_case(
        self, load_case_id: int, direction: Optional[str] = None
    ) -> List[StoryDrift]:
        return self.drifts.get_drifts_by_case(load_case_id, direction)
