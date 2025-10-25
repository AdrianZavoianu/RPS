"""Repository pattern for database access - provides clean interface to database operations."""

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from .models import (
    Project,
    LoadCase,
    Story,
    StoryDrift,
    StoryAcceleration,
    StoryForce,
    StoryDisplacement,
    Element,
    TimeHistoryData,
    ResultSet,
    ResultCategory,
    GlobalResultsCache,
    AbsoluteMaxMinDrift,
)


class ProjectRepository:
    """Repository for Project operations."""

    def __init__(self, session: Session):
        self.session = session

    def create(self, name: str, description: Optional[str] = None) -> Project:
        """Create a new project."""
        project = Project(name=name, description=description)
        self.session.add(project)
        self.session.commit()
        self.session.refresh(project)
        return project

    def get_by_id(self, project_id: int) -> Optional[Project]:
        """Get project by ID."""
        return self.session.query(Project).filter(Project.id == project_id).first()

    def get_by_name(self, name: str) -> Optional[Project]:
        """Get project by name."""
        return self.session.query(Project).filter(Project.name == name).first()

    def get_all(self) -> List[Project]:
        """Get all projects."""
        return self.session.query(Project).order_by(Project.created_at.desc()).all()

    def update(self, project: Project) -> Project:
        """Update project."""
        self.session.commit()
        self.session.refresh(project)
        return project

    def delete(self, project_id: int) -> bool:
        """Delete project and all related data."""
        project = self.get_by_id(project_id)
        if project:
            self.session.delete(project)
            self.session.commit()
            return True
        return False


class LoadCaseRepository:
    """Repository for LoadCase operations."""

    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        project_id: int,
        name: str,
        case_type: Optional[str] = None,
        description: Optional[str] = None,
    ) -> LoadCase:
        """Create a new load case."""
        load_case = LoadCase(
            project_id=project_id,
            name=name,
            case_type=case_type,
            description=description,
        )
        self.session.add(load_case)
        self.session.commit()
        self.session.refresh(load_case)
        return load_case

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
        """Get all load cases for a project."""
        return (
            self.session.query(LoadCase)
            .filter(LoadCase.project_id == project_id)
            .order_by(LoadCase.name)
            .all()
        )

    def get_by_id(self, load_case_id: int) -> Optional[LoadCase]:
        """Get a load case by ID."""
        return self.session.query(LoadCase).filter(LoadCase.id == load_case_id).first()


class StoryRepository:
    """Repository for Story operations."""

    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        project_id: int,
        name: str,
        elevation: Optional[float] = None,
        sort_order: Optional[int] = None,
    ) -> Story:
        """Create a new story."""
        story = Story(
            project_id=project_id,
            name=name,
            elevation=elevation,
            sort_order=sort_order,
        )
        self.session.add(story)
        self.session.commit()
        self.session.refresh(story)
        return story

    def get_or_create(
        self, project_id: int, name: str, sort_order: Optional[int] = None
    ) -> Story:
        """Get existing story or create new one."""
        story = (
            self.session.query(Story)
            .filter(and_(Story.project_id == project_id, Story.name == name))
            .first()
        )
        if not story:
            story = self.create(project_id, name, sort_order=sort_order)
        elif sort_order is not None and story.sort_order != sort_order:
            # Keep database ordering in sync with the source Excel order
            story.sort_order = sort_order
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


class ResultRepository:
    """Repository for result data (drifts, accelerations, forces, displacements)."""

    def __init__(self, session: Session):
        self.session = session

    def create_story_drift(
        self,
        story_id: int,
        load_case_id: int,
        direction: str,
        drift: float,
        max_drift: Optional[float] = None,
        min_drift: Optional[float] = None,
    ) -> StoryDrift:
        """Create story drift record."""
        story_drift = StoryDrift(
            story_id=story_id,
            load_case_id=load_case_id,
            direction=direction,
            drift=drift,
            max_drift=max_drift,
            min_drift=min_drift,
        )
        self.session.add(story_drift)
        self.session.commit()
        self.session.refresh(story_drift)
        return story_drift

    def create_story_acceleration(
        self,
        story_id: int,
        load_case_id: int,
        direction: str,
        acceleration: float,
        max_acceleration: Optional[float] = None,
        min_acceleration: Optional[float] = None,
    ) -> StoryAcceleration:
        """Create story acceleration record."""
        story_accel = StoryAcceleration(
            story_id=story_id,
            load_case_id=load_case_id,
            direction=direction,
            acceleration=acceleration,
            max_acceleration=max_acceleration,
            min_acceleration=min_acceleration,
        )
        self.session.add(story_accel)
        self.session.commit()
        self.session.refresh(story_accel)
        return story_accel

    def create_story_force(
        self,
        story_id: int,
        load_case_id: int,
        direction: str,
        force: float,
        location: Optional[str] = None,
        max_force: Optional[float] = None,
        min_force: Optional[float] = None,
    ) -> StoryForce:
        """Create story force record."""
        story_force = StoryForce(
            story_id=story_id,
            load_case_id=load_case_id,
            direction=direction,
            location=location,
            force=force,
            max_force=max_force,
            min_force=min_force,
        )
        self.session.add(story_force)
        self.session.commit()
        self.session.refresh(story_force)
        return story_force

    def create_story_displacement(
        self,
        story_id: int,
        load_case_id: int,
        direction: str,
        displacement: float,
        max_displacement: Optional[float] = None,
        min_displacement: Optional[float] = None,
    ) -> StoryDisplacement:
        """Create story displacement record."""
        record = StoryDisplacement(
            story_id=story_id,
            load_case_id=load_case_id,
            direction=direction,
            displacement=displacement,
            max_displacement=max_displacement,
            min_displacement=min_displacement,
        )
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return record

    def bulk_create_displacements(self, displacements: List[StoryDisplacement]):
        """Bulk insert displacement records."""
        if not displacements:
            return
        self.session.bulk_save_objects(displacements)
        self.session.commit()

    def get_drifts_by_project(self, project_id: int) -> List[StoryDrift]:
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

    def bulk_create_drifts(self, drifts: List[StoryDrift]):
        """Bulk insert drift records for better performance."""
        self.session.bulk_save_objects(drifts)
        self.session.commit()

    def bulk_create_accelerations(self, accelerations: List[StoryAcceleration]):
        """Bulk insert acceleration records."""
        self.session.bulk_save_objects(accelerations)
        self.session.commit()

    def bulk_create_forces(self, forces: List[StoryForce]):
        """Bulk insert force records."""
        self.session.bulk_save_objects(forces)
        self.session.commit()


class ResultSetRepository:
    """Repository for ResultSet operations."""

    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        project_id: int,
        name: str,
        description: Optional[str] = None,
    ) -> ResultSet:
        """Create a new result set."""
        result_set = ResultSet(
            project_id=project_id,
            name=name,
            description=description,
        )
        self.session.add(result_set)
        self.session.commit()
        self.session.refresh(result_set)
        return result_set

    def get_or_create(
        self,
        project_id: int,
        name: str,
    ) -> ResultSet:
        """Get existing result set or create new one."""
        result_set = (
            self.session.query(ResultSet)
            .filter(and_(ResultSet.project_id == project_id, ResultSet.name == name))
            .first()
        )
        if not result_set:
            result_set = self.create(project_id, name)
        return result_set

    def check_duplicate(self, project_id: int, name: str) -> bool:
        """Check if result set name already exists for this project."""
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


class CacheRepository:
    """Repository for GlobalResultsCache operations - optimized for tabular display."""

    def __init__(self, session: Session):
        self.session = session

    def upsert_cache_entry(
        self,
        project_id: int,
        story_id: int,
        result_type: str,
        results_matrix: dict,
        result_set_id: Optional[int] = None,
    ) -> GlobalResultsCache:
        """Create or update cache entry for a story's results."""
        cache_entry = (
            self.session.query(GlobalResultsCache)
            .filter(
                and_(
                    GlobalResultsCache.project_id == project_id,
                    GlobalResultsCache.story_id == story_id,
                    GlobalResultsCache.result_type == result_type,
                    GlobalResultsCache.result_set_id == result_set_id,
                )
            )
            .first()
        )

        if cache_entry:
            cache_entry.results_matrix = results_matrix
        else:
            cache_entry = GlobalResultsCache(
                project_id=project_id,
                result_set_id=result_set_id,
                result_type=result_type,
                story_id=story_id,
                results_matrix=results_matrix,
            )
            self.session.add(cache_entry)

        self.session.commit()
        self.session.refresh(cache_entry)
        return cache_entry

    def get_cache_for_display(
        self,
        project_id: int,
        result_type: str,
        result_set_id: Optional[int] = None,
    ) -> List[tuple]:
        """Get all cache entries for a result type, ordered by story sort_order (bottom to top).

        Returns list of tuples: (GlobalResultsCache, Story) in ascending sort_order to match Excel source order.
        """
        query = (
            self.session.query(GlobalResultsCache, Story)
            .join(Story, GlobalResultsCache.story_id == Story.id)
            .filter(
                and_(
                    GlobalResultsCache.project_id == project_id,
                    GlobalResultsCache.result_type == result_type,
                )
            )
        )

        if result_set_id is not None:
            query = query.filter(GlobalResultsCache.result_set_id == result_set_id)

        return query.order_by(Story.sort_order.asc()).all()

    def clear_cache_for_project(self, project_id: int, result_type: Optional[str] = None):
        """Clear cache entries for a project, optionally filtered by result type."""
        query = self.session.query(GlobalResultsCache).filter(
            GlobalResultsCache.project_id == project_id
        )
        if result_type:
            query = query.filter(GlobalResultsCache.result_type == result_type)

        query.delete()
        self.session.commit()

    def bulk_upsert_cache(self, cache_entries: List[dict]):
        """Bulk upsert cache entries for better performance.

        Args:
            cache_entries: List of dicts with keys: project_id, story_id, result_type,
                          results_matrix, result_set_id (optional)
        """
        for entry_data in cache_entries:
            self.upsert_cache_entry(
                project_id=entry_data['project_id'],
                story_id=entry_data['story_id'],
                result_type=entry_data['result_type'],
                results_matrix=entry_data['results_matrix'],
                result_set_id=entry_data.get('result_set_id'),
            )


class ResultCategoryRepository:
    """Repository for ResultCategory operations."""

    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        result_set_id: int,
        category_name: str,
        category_type: str,
    ) -> ResultCategory:
        """Create a new result category."""
        category = ResultCategory(
            result_set_id=result_set_id,
            category_name=category_name,
            category_type=category_type,
        )
        self.session.add(category)
        self.session.commit()
        self.session.refresh(category)
        return category

    def get_or_create(
        self,
        result_set_id: int,
        category_name: str,
        category_type: str,
    ) -> ResultCategory:
        """Get existing category or create new one."""
        category = (
            self.session.query(ResultCategory)
            .filter(
                and_(
                    ResultCategory.result_set_id == result_set_id,
                    ResultCategory.category_name == category_name,
                    ResultCategory.category_type == category_type,
                )
            )
            .first()
        )
        if not category:
            category = self.create(result_set_id, category_name, category_type)
        return category

    def get_by_result_set(self, result_set_id: int) -> List[ResultCategory]:
        """Get all categories for a result set."""
        return (
            self.session.query(ResultCategory)
            .filter(ResultCategory.result_set_id == result_set_id)
            .order_by(ResultCategory.category_name, ResultCategory.category_type)
            .all()
        )

    def get_by_result_set_and_category(
        self, result_set_id: int, category_name: str, category_type: str
    ) -> Optional[ResultCategory]:
        """Get specific category by result set, name, and type."""
        return (
            self.session.query(ResultCategory)
            .filter(
                and_(
                    ResultCategory.result_set_id == result_set_id,
                    ResultCategory.category_name == category_name,
                    ResultCategory.category_type == category_type,
                )
            )
            .first()
        )


class AbsoluteMaxMinDriftRepository:
    """Repository for AbsoluteMaxMinDrift operations."""

    def __init__(self, session: Session):
        self.session = session

    def bulk_create(self, drift_records: List[dict]) -> int:
        """Bulk create absolute max/min drift records.

        Args:
            drift_records: List of dictionaries with keys:
                - project_id
                - result_set_id
                - story_id
                - load_case_id
                - direction
                - absolute_max_drift
                - sign
                - original_max
                - original_min

        Returns:
            Number of records created
        """
        # Clear existing records for this result set if any
        if drift_records:
            result_set_id = drift_records[0].get('result_set_id')
            project_id = drift_records[0].get('project_id')

            if result_set_id and project_id:
                self.session.query(AbsoluteMaxMinDrift).filter(
                    and_(
                        AbsoluteMaxMinDrift.project_id == project_id,
                        AbsoluteMaxMinDrift.result_set_id == result_set_id
                    )
                ).delete()
                self.session.commit()  # Commit the deletion before inserting

        # Create new records
        records = [AbsoluteMaxMinDrift(**record) for record in drift_records]
        self.session.bulk_save_objects(records)
        self.session.commit()

        return len(records)

    def get_by_result_set(
        self, project_id: int, result_set_id: int
    ) -> List[AbsoluteMaxMinDrift]:
        """Get all absolute max/min drifts for a result set.

        Args:
            project_id: Project ID
            result_set_id: Result set ID

        Returns:
            List of AbsoluteMaxMinDrift objects
        """
        return (
            self.session.query(AbsoluteMaxMinDrift)
            .filter(
                and_(
                    AbsoluteMaxMinDrift.project_id == project_id,
                    AbsoluteMaxMinDrift.result_set_id == result_set_id
                )
            )
            .order_by(AbsoluteMaxMinDrift.story_id, AbsoluteMaxMinDrift.load_case_id)
            .all()
        )

    def get_by_result_set_and_direction(
        self, project_id: int, result_set_id: int, direction: str
    ) -> List[AbsoluteMaxMinDrift]:
        """Get absolute max/min drifts for a specific direction.

        Args:
            project_id: Project ID
            result_set_id: Result set ID
            direction: 'X' or 'Y'

        Returns:
            List of AbsoluteMaxMinDrift objects
        """
        return (
            self.session.query(AbsoluteMaxMinDrift)
            .filter(
                and_(
                    AbsoluteMaxMinDrift.project_id == project_id,
                    AbsoluteMaxMinDrift.result_set_id == result_set_id,
                    AbsoluteMaxMinDrift.direction == direction
                )
            )
            .order_by(AbsoluteMaxMinDrift.story_id, AbsoluteMaxMinDrift.load_case_id)
            .all()
        )

    def delete_by_result_set(self, project_id: int, result_set_id: int) -> int:
        """Delete all absolute max/min drifts for a result set.

        Args:
            project_id: Project ID
            result_set_id: Result set ID

        Returns:
            Number of records deleted
        """
        count = (
            self.session.query(AbsoluteMaxMinDrift)
            .filter(
                and_(
                    AbsoluteMaxMinDrift.project_id == project_id,
                    AbsoluteMaxMinDrift.result_set_id == result_set_id
                )
            )
            .delete()
        )
        self.session.commit()
        return count
