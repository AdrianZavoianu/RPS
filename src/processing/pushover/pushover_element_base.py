"""
Base class for pushover element importers (beams, columns, walls).

Extends BasePushoverImporter with common patterns for element-based results:
- Entity creation (stories, elements)
- Row-by-row DataFrame processing
- ElementResultsCache building

Subclasses implement:
- _get_element_type(): Return element type ('Beam', 'Column', 'Wall')
- _get_parser(): Return parser instance
- _get_story_mapping_sheet(): Return sheet name for unique_name→story mapping
- _get_result_types(): Return list of result type configs
- _create_result_record(): Create ORM record for one result
"""

from abc import abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set, Any, Type
import logging

import pandas as pd
from sqlalchemy.orm import Session

from database.models import (
    ResultSet,
    Story,
    LoadCase,
    Element,
    ElementResultsCache,
)
from processing.pushover.pushover_base_importer import BasePushoverImporter

logger = logging.getLogger(__name__)


@dataclass
class ResultTypeConfig:
    """Configuration for one result type within an importer."""
    name: str  # e.g., 'R2', 'R3', 'V2', 'V3'
    attr_name: str  # Attribute name on parse result, e.g., 'rotations_r2'
    cache_suffix: str  # Suffix for ElementResultsCache.result_type, e.g., '_R2'
    model_field: str  # Field name on ORM model, e.g., 'rotation', 'r3_plastic'
    model_class: Type  # ORM model class, e.g., ColumnRotation, BeamRotation


class PushoverElementBaseImporter(BasePushoverImporter):
    """Base class for pushover element importers.

    Handles the common workflow for importing element-based results
    (beams, columns, walls) that follow the pattern:
    1. Create stories and elements from DataFrame
    2. Import rows with load case filtering
    3. Build ElementResultsCache

    Subclasses configure the import via abstract methods rather than
    overriding the full workflow.
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
        super().__init__(
            project_id=project_id,
            session=session,
            result_set_id=result_set_id,
            file_path=file_path,
            selected_load_cases_x=selected_load_cases_x,
            selected_load_cases_y=selected_load_cases_y,
            progress_callback=progress_callback,
        )
        # Additional caches for element importers
        self.unique_name_story_map: Dict[str, str] = {}  # unique_name → story_name
        self._parser = None

    def _get_parser(self):
        """Get or create parser instance (cached)."""
        if self._parser is None:
            self._parser = self._create_parser()
        return self._parser

    # ===== Abstract Configuration Methods =====

    @abstractmethod
    def _get_element_type(self) -> str:
        """Return element type: 'Beam', 'Column', 'Wall', 'Quad'.

        Returns:
            Element type string used in Element.element_type
        """
        pass

    @abstractmethod
    def _create_parser(self):
        """Create and return parser instance.

        Returns:
            Parser instance for parsing Excel file
        """
        pass

    @abstractmethod
    def _get_story_mapping_sheet(self) -> str:
        """Return sheet name for building unique_name→story mapping.

        Returns:
            Sheet name, e.g., 'Hinge States', 'Fiber Hinge States'
        """
        pass

    @abstractmethod
    def _get_result_types(self) -> List[ResultTypeConfig]:
        """Return configuration for result types to import.

        Returns:
            List of ResultTypeConfig objects
        """
        pass

    @abstractmethod
    def _create_result_record(
        self,
        config: ResultTypeConfig,
        element: Element,
        story: Story,
        load_case: LoadCase,
        value: float,
        story_sort_order: int,
    ) -> Any:
        """Create ORM record for one result.

        Args:
            config: Result type configuration
            element: Element entity
            story: Story entity
            load_case: LoadCase entity
            value: Result value
            story_sort_order: Sort order for story

        Returns:
            ORM record instance (not yet added to session)
        """
        pass

    # ===== Implemented Template Methods =====

    def _create_stats_dict(self) -> Dict[str, Any]:
        """Create statistics dictionary based on result types."""
        stats = {'errors': [], 'result_set_id': self.result_set_id}
        for config in self._get_result_types():
            stats[f'x_{config.name.lower()}'] = 0
            stats[f'y_{config.name.lower()}'] = 0
        return stats

    def _ensure_entities(self):
        """Ensure all stories and elements exist in database."""
        parser = self._get_parser()

        # Get data from first available direction
        if self.selected_load_cases_x:
            results = parser.parse('X')
        elif self.selected_load_cases_y:
            results = parser.parse('Y')
        else:
            return

        # Use first result type to extract elements
        result_types = self._get_result_types()
        if not result_types:
            return

        first_config = result_types[0]
        df = getattr(results, first_config.attr_name, None)
        if df is None:
            return

        # Extract and create elements
        element_type = self._get_element_type()
        element_names = df.iloc[:, 0].unique().tolist()

        for element_name in element_names:
            element_name_str = str(element_name)
            element = self._get_or_create_element(element_name_str, element_type)
            # Also store in local cache keyed by name only
            self.elements_cache[element_name_str] = element

        # Build unique_name → story mapping from raw sheet
        sheet_name = self._get_story_mapping_sheet()
        if sheet_name:
            raw_df = parser._read_sheet(sheet_name)
            for _, row in raw_df.iterrows():
                unique_name = str(int(float(row['Unique Name'])))
                story_name = str(row['Story'])
                self.unique_name_story_map[unique_name] = story_name

            # Create stories
            for story_name in set(self.unique_name_story_map.values()):
                self._get_or_create_story(story_name)

    def _import_direction(self, direction: str, selected_load_cases: Set[str]) -> Dict:
        """Import data for one direction."""
        stats = {'errors': []}
        parser = self._get_parser()
        results = parser.parse(direction)

        for config in self._get_result_types():
            df = getattr(results, config.attr_name, None)
            if df is not None:
                count = self._import_result_type(df, config, selected_load_cases)
                stats[config.name.lower()] = count

        return stats

    def _import_result_type(
        self,
        df: pd.DataFrame,
        config: ResultTypeConfig,
        selected_load_cases: Set[str]
    ) -> int:
        """Import one result type from DataFrame.

        Args:
            df: DataFrame with columns: Element, Unique Name, [Load Cases...]
            config: Result type configuration
            selected_load_cases: Set of load cases to import

        Returns:
            Count of imported records
        """
        count = 0

        # First two columns are element and unique name
        element_col = df.columns[0]
        unique_name_col = df.columns[1]

        for _, row in df.iterrows():
            element_name = str(row[element_col])
            unique_name = str(int(float(row[unique_name_col])))

            # Look up element and story
            element = self.elements_cache.get(element_name)
            story_name = self.unique_name_story_map.get(unique_name)
            story = self.stories_cache.get(story_name) if story_name else None

            if not element or not story:
                continue

            # Import each load case
            for load_case_name in df.columns[2:]:
                if load_case_name not in selected_load_cases:
                    continue

                value = row[load_case_name]
                if pd.isna(value):
                    continue

                load_case = self._get_or_create_load_case(load_case_name)
                story_sort_order = story.sort_order

                record = self._create_result_record(
                    config=config,
                    element=element,
                    story=story,
                    load_case=load_case,
                    value=float(value),
                    story_sort_order=story_sort_order,
                )
                self.session.add(record)
                count += 1

        return count

    def _build_cache(self):
        """Build element results cache for all result types."""
        # Delete existing cache entries for this result set
        result_type_names = [
            f"{self._get_cache_base_name()}{config.cache_suffix}"
            for config in self._get_result_types()
        ]

        self.session.query(ElementResultsCache).filter(
            ElementResultsCache.result_set_id == self.result_set_id,
            ElementResultsCache.result_type.in_(result_type_names)
        ).delete(synchronize_session=False)

        # Build cache for each result type
        for config in self._get_result_types():
            self._build_cache_for_type(config)

    def _get_cache_base_name(self) -> str:
        """Return base name for cache entries.

        Default implementation uses element type + 'Rotations' or 'Shears'.
        Override if different naming is needed.

        Returns:
            Base name like 'BeamRotations', 'ColumnRotations'
        """
        element_type = self._get_element_type()
        return f"{element_type}Rotations"

    def _build_cache_for_type(self, config: ResultTypeConfig):
        """Build cache entries for one result type.

        Args:
            config: Result type configuration
        """
        load_case_ids = self._get_load_case_ids()
        if not load_case_ids:
            logger.warning(f"No load cases in cache for {config.name}")
            return

        # Query all records for this result type
        model_class = config.model_class
        records = self.session.query(
            model_class,
            LoadCase.name,
            model_class.element_id,
            model_class.story_id,
            model_class.story_sort_order
        ).join(
            LoadCase, model_class.load_case_id == LoadCase.id
        ).filter(
            model_class.load_case_id.in_(load_case_ids),
            *self._get_cache_query_filters(config, model_class)
        ).all()

        logger.info(f"Query returned {len(records)} records for {config.name}")

        if not records:
            return

        # Group by element and story
        element_story_data = {}
        for record, load_case_name, element_id, story_id, story_sort_order in records:
            key = (element_id, story_id)
            if key not in element_story_data:
                element_story_data[key] = {
                    'results_matrix': {},
                    'story_sort_order': story_sort_order
                }
            # Get value from record using model_field
            value = getattr(record, config.model_field)
            element_story_data[key]['results_matrix'][load_case_name] = value

        # Create cache entries
        result_type = f"{self._get_cache_base_name()}{config.cache_suffix}"
        for (element_id, story_id), data in element_story_data.items():
            cache_entry = ElementResultsCache(
                project_id=self.project_id,
                result_set_id=self.result_set_id,
                element_id=element_id,
                story_id=story_id,
                result_type=result_type,
                story_sort_order=data['story_sort_order'],
                results_matrix=data['results_matrix']
            )
            self.session.add(cache_entry)

        logger.info(f"Created {len(element_story_data)} cache entries for {result_type}")

    def _get_cache_query_filters(self, config: ResultTypeConfig, model_class) -> list:
        """Return additional filters for cache query.

        Override to add filters like direction='R2'.

        Args:
            config: Result type configuration
            model_class: ORM model class

        Returns:
            List of SQLAlchemy filter conditions
        """
        return []
