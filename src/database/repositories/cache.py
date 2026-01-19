"""Cache repositories for GlobalResultsCache, ElementResultsCache, JointResultsCache operations."""

from typing import List, Optional
from sqlalchemy import and_

from ..models import (
    GlobalResultsCache,
    ElementResultsCache,
    JointResultsCache,
    AbsoluteMaxMinDrift,
    ResultCategory,
    Story,
)
from ..base_repository import BaseRepository


class CacheRepository(BaseRepository[GlobalResultsCache]):
    """Repository for GlobalResultsCache operations - optimized for tabular display."""

    model = GlobalResultsCache

    def get_distinct_load_cases(self, project_id: int, result_set_id: int) -> list:
        """
        Get all distinct load case names for a result set.

        Extracts load case names from the results_matrix JSON keys.
        """
        # Query a single cache entry to get load case names
        entry = (
            self.session.query(GlobalResultsCache)
            .filter(
                and_(
                    GlobalResultsCache.project_id == project_id,
                    GlobalResultsCache.result_set_id == result_set_id
                )
            )
            .first()
        )

        if entry and entry.results_matrix:
            # Return the keys (load case names) from the JSON results_matrix
            return list(entry.results_matrix.keys())

        return []

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

    def replace_cache_entries(
        self,
        project_id: int,
        result_set_id: Optional[int],
        result_type: str,
        entries: List[dict],
    ) -> int:
        """Replace all cache entries for a result type in a result set."""
        self.session.query(GlobalResultsCache).filter(
            and_(
                GlobalResultsCache.project_id == project_id,
                GlobalResultsCache.result_set_id == result_set_id,
                GlobalResultsCache.result_type == result_type,
            )
        ).delete(synchronize_session=False)

        if entries:
            self.session.bulk_insert_mappings(GlobalResultsCache, entries)
        self.session.commit()
        return len(entries)

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

    def replace_cache_entries(
        self,
        project_id: int,
        result_set_id: Optional[int],
        result_type: str,
        entries: List[dict],
    ) -> int:
        """Replace all element cache entries for a result type in a result set."""
        self.session.query(ElementResultsCache).filter(
            and_(
                ElementResultsCache.project_id == project_id,
                ElementResultsCache.result_set_id == result_set_id,
                ElementResultsCache.result_type == result_type,
            )
        ).delete(synchronize_session=False)

        if entries:
            self.session.bulk_insert_mappings(ElementResultsCache, entries)
        self.session.commit()
        return len(entries)

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


class JointCacheRepository(BaseRepository[JointResultsCache]):
    """Repository for joint-level results cache operations."""

    model = JointResultsCache

    def get_cache_entry(
        self,
        project_id: int,
        result_set_id: int,
        result_type: str,
        unique_name: str,
    ) -> Optional[JointResultsCache]:
        """Get cache entry for a specific foundation element."""
        return (
            self.session.query(JointResultsCache)
            .filter(
                and_(
                    JointResultsCache.project_id == project_id,
                    JointResultsCache.result_set_id == result_set_id,
                    JointResultsCache.result_type == result_type,
                    JointResultsCache.unique_name == unique_name,
                )
            )
            .first()
        )

    def get_all_for_type(
        self,
        project_id: int,
        result_set_id: int,
        result_type: str,
    ) -> List[JointResultsCache]:
        """Get all cache entries for a specific result type."""
        return (
            self.session.query(JointResultsCache)
            .filter(
                and_(
                    JointResultsCache.project_id == project_id,
                    JointResultsCache.result_set_id == result_set_id,
                    JointResultsCache.result_type == result_type,
                )
            )
            .all()
        )

    def upsert_cache_entry(
        self,
        project_id: int,
        result_set_id: int,
        result_type: str,
        shell_object: str,
        unique_name: str,
        results_matrix: dict,
    ) -> JointResultsCache:
        """Insert or update a cache entry."""
        entry = self.get_cache_entry(project_id, result_set_id, result_type, unique_name)

        if entry:
            entry.results_matrix = results_matrix
            entry.shell_object = shell_object
            self.session.commit()
        else:
            entry = JointResultsCache(
                project_id=project_id,
                result_set_id=result_set_id,
                result_type=result_type,
                shell_object=shell_object,
                unique_name=unique_name,
                results_matrix=results_matrix,
            )
            self.session.add(entry)
        self.session.commit()

        return entry

    def replace_cache_entries(
        self,
        project_id: int,
        result_set_id: int,
        result_type: str,
        entries: List[dict],
    ) -> int:
        """Replace all joint cache entries for a result type in a result set."""
        self.session.query(JointResultsCache).filter(
            and_(
                JointResultsCache.project_id == project_id,
                JointResultsCache.result_set_id == result_set_id,
                JointResultsCache.result_type == result_type,
            )
        ).delete(synchronize_session=False)

        if entries:
            self.session.bulk_insert_mappings(JointResultsCache, entries)
        self.session.commit()
        return len(entries)


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
