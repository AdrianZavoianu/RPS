"""
Base class for pushover result importers.

Provides common functionality for all pushover importers:
- Session management
- Progress reporting
- Entity caching (stories, load cases, elements)
- Import workflow template

Subclasses implement:
- _ensure_entities(): Create stories/elements from parsed data
- _import_direction(): Import data for one direction
- _build_cache(): Build result cache after import
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set, Any
import logging

from sqlalchemy.orm import Session

from database.models import Project, ResultSet, Story, LoadCase, Element

logger = logging.getLogger(__name__)


class BasePushoverImporter(ABC):
    """Abstract base class for all pushover result importers.

    Provides shared functionality:
    - Session and result set management
    - Entity caching (stories, load cases, elements)
    - Progress reporting
    - Import workflow template

    Subclasses implement parse/import logic for specific result types.
    """

    def __init__(
        self,
        project_id: int,
        session: Session,
        result_set_id: int,
        file_path: Path,
        selected_load_cases_x: List[str],
        selected_load_cases_y: List[str],
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
    ):
        """Initialize importer.

        Args:
            project_id: ID of the project
            session: Database session
            result_set_id: ID of the result set to add results to
            file_path: Path to Excel file containing results
            selected_load_cases_x: List of selected load cases for X direction
            selected_load_cases_y: List of selected load cases for Y direction
            progress_callback: Optional callback for progress updates
        """
        self.project_id = project_id
        self.session = session
        self.result_set_id = result_set_id
        self.file_path = file_path
        self.selected_load_cases_x = set(selected_load_cases_x)
        self.selected_load_cases_y = set(selected_load_cases_y)
        self.progress_callback = progress_callback

        # Entity caches
        self.result_set: Optional[ResultSet] = None
        self.stories_cache: Dict[str, Story] = {}
        self.load_cases_cache: Dict[str, LoadCase] = {}
        self.elements_cache: Dict[str, Element] = {}

        # Story ordering
        self.story_order: Dict[tuple, int] = {}

    def import_all(self) -> Dict[str, Any]:
        """Import all pushover results using template method pattern.

        Returns:
            Dict with import statistics

        Raises:
            ValueError: If result set not found
            Exception: On import failure (rolls back transaction)
        """
        try:
            self._log_progress("Loading result set...", 0, 100)

            # Get existing result set
            self.result_set = self.session.query(ResultSet).get(self.result_set_id)
            if not self.result_set:
                raise ValueError(f"Result set ID {self.result_set_id} not found")

            # Step 1: Ensure entities exist (stories, elements)
            self._log_progress("Preparing entities...", 10, 100)
            self._ensure_entities()

            # Step 2: Import data
            stats = self._create_stats_dict()

            # Import X direction
            if self.selected_load_cases_x:
                self._log_progress("Importing X direction...", 30, 100)
                x_stats = self._import_direction('X', self.selected_load_cases_x)
                self._merge_stats(stats, x_stats, 'x')

            # Import Y direction
            if self.selected_load_cases_y:
                self._log_progress("Importing Y direction...", 60, 100)
                y_stats = self._import_direction('Y', self.selected_load_cases_y)
                self._merge_stats(stats, y_stats, 'y')

            # Step 3: Flush all records
            self._log_progress("Flushing data...", 85, 100)
            self.session.flush()
            logger.info(f"Flushed all records to database")

            # Step 4: Build cache
            self._log_progress("Building cache...", 90, 100)
            self._build_cache()

            # Step 5: Commit
            self._log_progress("Import complete!", 100, 100)
            self.session.commit()

            return stats

        except Exception as e:
            self.session.rollback()
            logger.exception(f"{self.__class__.__name__} import failed")
            raise

    def _create_stats_dict(self) -> Dict[str, Any]:
        """Create initial statistics dictionary.

        Subclasses can override to add result-type-specific stats.

        Returns:
            Dict with stat keys initialized to 0
        """
        return {'errors': []}

    def _merge_stats(self, stats: Dict, direction_stats: Dict, prefix: str):
        """Merge direction-specific stats into main stats.

        Args:
            stats: Main statistics dict
            direction_stats: Stats from one direction
            prefix: Prefix for direction ('x' or 'y')
        """
        for key, value in direction_stats.items():
            if key == 'errors':
                stats['errors'].extend(value if isinstance(value, list) else [value])
            else:
                stat_key = f"{prefix}_{key}"
                stats[stat_key] = stats.get(stat_key, 0) + value

    def _log_progress(self, message: str, current: int, total: int):
        """Log progress message and call callback if set.

        Args:
            message: Progress message
            current: Current progress value
            total: Total progress value
        """
        if self.progress_callback:
            self.progress_callback(message, current, total)
        logger.info(f"{message} ({current}/{total})")

    # ===== Entity Management =====

    def _get_or_create_story(self, story_name: str, sort_order: int = 0) -> Story:
        """Get or create a story entity.

        Args:
            story_name: Name of the story
            sort_order: Sort order (default 0)

        Returns:
            Story entity
        """
        if story_name in self.stories_cache:
            return self.stories_cache[story_name]

        story = self.session.query(Story).filter(
            Story.project_id == self.project_id,
            Story.name == story_name
        ).first()

        if not story:
            story = Story(
                project_id=self.project_id,
                name=story_name,
                sort_order=sort_order
            )
            self.session.add(story)
            self.session.flush()

        self.stories_cache[story_name] = story
        return story

    def _get_or_create_load_case(self, load_case_name: str) -> LoadCase:
        """Get or create a load case entity.

        Args:
            load_case_name: Name of the load case

        Returns:
            LoadCase entity
        """
        if load_case_name in self.load_cases_cache:
            return self.load_cases_cache[load_case_name]

        load_case = self.session.query(LoadCase).filter(
            LoadCase.project_id == self.project_id,
            LoadCase.name == load_case_name
        ).first()

        if not load_case:
            load_case = LoadCase(
                project_id=self.project_id,
                name=load_case_name,
                case_type="Pushover"
            )
            self.session.add(load_case)
            self.session.flush()

        self.load_cases_cache[load_case_name] = load_case
        return load_case

    def _get_or_create_element(
        self,
        element_name: str,
        element_type: str
    ) -> Element:
        """Get or create an element entity.

        Args:
            element_name: Name of the element
            element_type: Type of element ('Wall', 'Column', 'Beam', 'Quad')

        Returns:
            Element entity
        """
        cache_key = f"{element_type}:{element_name}"
        if cache_key in self.elements_cache:
            return self.elements_cache[cache_key]

        element = self.session.query(Element).filter(
            Element.project_id == self.project_id,
            Element.name == element_name,
            Element.element_type == element_type
        ).first()

        if not element:
            element = Element(
                project_id=self.project_id,
                name=element_name,
                element_type=element_type
            )
            self.session.add(element)
            self.session.flush()

        self.elements_cache[cache_key] = element
        return element

    def _get_load_case_ids(self) -> List[int]:
        """Get list of load case IDs from cache.

        Returns:
            List of load case IDs
        """
        return [lc.id for lc in self.load_cases_cache.values()]

    # ===== Abstract Methods =====

    @abstractmethod
    def _ensure_entities(self):
        """Ensure all required entities (stories, elements) exist.

        Reads data from parser to determine what entities are needed,
        then creates/caches them.
        """
        pass

    @abstractmethod
    def _import_direction(self, direction: str, selected_load_cases: Set[str]) -> Dict:
        """Import data for one direction.

        Args:
            direction: 'X' or 'Y'
            selected_load_cases: Set of load cases to import

        Returns:
            Dict with counts of imported records
        """
        pass

    @abstractmethod
    def _build_cache(self):
        """Build result cache after all data is imported.

        Queries imported records and creates cache entries for fast retrieval.
        """
        pass
