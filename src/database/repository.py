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
    ElementResultsCache,
    WallShear,
)
from .base_repository import BaseRepository


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


class CacheRepository(BaseRepository[GlobalResultsCache]):
    """Repository for GlobalResultsCache operations - optimized for tabular display."""

    model = GlobalResultsCache

    def upsert_cache_entry(
        self,
        project_id: int,
        story_id: int,
        result_type: str,
        results_matrix: dict,
        result_set_id: Optional[int] = None,
        story_sort_order: Optional[int] = None,
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
            if story_sort_order is not None:
                cache_entry.story_sort_order = story_sort_order
        else:
            cache_entry = GlobalResultsCache(
                project_id=project_id,
                result_set_id=result_set_id,
                result_type=result_type,
                story_id=story_id,
                results_matrix=results_matrix,
                story_sort_order=story_sort_order,
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
        """Get all cache entries for a result type, ordered by story_sort_order from cache (bottom to top).

        Returns list of cache entries ordered by story_sort_order from the cache entry.
        Each result type preserves its own sheet-specific story ordering.
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

        records = query.order_by(
            GlobalResultsCache.story_sort_order.desc(), Story.name.desc()
        ).all()
        return [cache for cache, _ in records]

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


class ResultCategoryRepository(BaseRepository[ResultCategory]):
    """Repository for ResultCategory operations."""

    model = ResultCategory

    def create(
        self,
        result_set_id: int,
        category_name: str,
        category_type: str,
    ) -> ResultCategory:
        """Create a new result category."""
        return super().create(
            result_set_id=result_set_id,
            category_name=category_name,
            category_type=category_type,
        )

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


class AbsoluteMaxMinDriftRepository(BaseRepository[AbsoluteMaxMinDrift]):
    """Repository for AbsoluteMaxMinDrift operations."""

    model = AbsoluteMaxMinDrift

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


class ElementCacheRepository(BaseRepository[ElementResultsCache]):
    """Repository for ElementResultsCache operations - optimized for element-level tabular display."""

    model = ElementResultsCache

    def upsert_cache_entry(
        self,
        project_id: int,
        element_id: int,
        story_id: int,
        result_type: str,
        results_matrix: dict,
        result_set_id: Optional[int] = None,
        story_sort_order: Optional[int] = None,
    ) -> ElementResultsCache:
        """Create or update cache entry for an element's results at a specific story."""
        cache_entry = (
            self.session.query(ElementResultsCache)
            .filter(
                and_(
                    ElementResultsCache.project_id == project_id,
                    ElementResultsCache.element_id == element_id,
                    ElementResultsCache.story_id == story_id,
                    ElementResultsCache.result_type == result_type,
                    ElementResultsCache.result_set_id == result_set_id,
                )
            )
            .first()
        )

        if cache_entry:
            cache_entry.results_matrix = results_matrix
            if story_sort_order is not None:
                cache_entry.story_sort_order = story_sort_order
        else:
            cache_entry = ElementResultsCache(
                project_id=project_id,
                result_set_id=result_set_id,
                result_type=result_type,
                element_id=element_id,
                story_id=story_id,
                results_matrix=results_matrix,
                story_sort_order=story_sort_order,
            )
            self.session.add(cache_entry)

        self.session.commit()
        self.session.refresh(cache_entry)
        return cache_entry

    def get_cache_for_display(
        self,
        project_id: int,
        element_id: int,
        result_type: str,
        result_set_id: Optional[int] = None,
    ) -> List[ElementResultsCache]:
        """Get all cache entries for a specific element and result type.

        Args:
            project_id: Project ID
            element_id: Specific element (pier/wall) ID
            result_type: Result type (e.g., 'WallShears_V22')
            result_set_id: Optional result set ID filter
        """
        query = (
            self.session.query(ElementResultsCache, Story)
            .join(Story, ElementResultsCache.story_id == Story.id)
            .filter(
                and_(
                    ElementResultsCache.project_id == project_id,
                    ElementResultsCache.element_id == element_id,
                    ElementResultsCache.result_type == result_type,
                )
            )
        )

        if result_set_id is not None:
            query = query.filter(ElementResultsCache.result_set_id == result_set_id)

        records = query.order_by(
            ElementResultsCache.story_sort_order.desc(), Story.name.desc()
        ).all()
        return [cache for cache, _ in records]

    def clear_cache_for_project(self, project_id: int, result_type: Optional[str] = None):
        """Clear cache entries for a project, optionally filtered by result type."""
        query = self.session.query(ElementResultsCache).filter(
            ElementResultsCache.project_id == project_id
        )
        if result_type:
            query = query.filter(ElementResultsCache.result_type == result_type)

        query.delete()
        self.session.commit()

    def bulk_upsert_cache(self, cache_entries: List[dict]):
        """Bulk upsert cache entries for better performance."""
        for entry_data in cache_entries:
            self.upsert_cache_entry(**entry_data)


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
