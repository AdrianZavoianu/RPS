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
    Element,
    TimeHistoryData,
    ResultSet,
    GlobalResultsCache,
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
        return story

    def get_by_project(self, project_id: int) -> List[Story]:
        """Get all stories for a project, ordered by sort_order."""
        return (
            self.session.query(Story)
            .filter(Story.project_id == project_id)
            .order_by(Story.sort_order.desc())
            .all()
        )


class ResultRepository:
    """Repository for result data (drifts, accelerations, forces)."""

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
        result_category: Optional[str] = None,
        description: Optional[str] = None,
    ) -> ResultSet:
        """Create a new result set."""
        result_set = ResultSet(
            project_id=project_id,
            name=name,
            result_category=result_category,
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
        result_category: Optional[str] = None,
    ) -> ResultSet:
        """Get existing result set or create new one."""
        result_set = (
            self.session.query(ResultSet)
            .filter(and_(ResultSet.project_id == project_id, ResultSet.name == name))
            .first()
        )
        if not result_set:
            result_set = self.create(project_id, name, result_category)
        return result_set

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
    ) -> List[GlobalResultsCache]:
        """Get all cache entries for a result type, ordered by story sort_order."""
        query = (
            self.session.query(GlobalResultsCache)
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

        return query.order_by(Story.sort_order.desc()).all()

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
