"""
Pushover Column Shear Importer (v2 - using Template Method pattern)

Imports pushover column shear forces into the database.
This version extends BasePushoverImporter for reduced code duplication.
"""

import logging
from typing import Dict, List, Set, Any

import pandas as pd

from database.models import Element, Story, LoadCase, ColumnShear, ElementResultsCache
from processing.pushover.pushover_base_importer import BasePushoverImporter
from processing.pushover.pushover_column_shear_parser import PushoverColumnShearParser

logger = logging.getLogger(__name__)


class PushoverColumnShearImporterV2(BasePushoverImporter):
    """Importer for pushover column shear forces.

    Imports column shear values (V2 and V3) from Excel files
    for both X and Y directions.

    This is a refactored version using the Template Method pattern,
    reducing ~390 lines to ~150 lines.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._parser = None

    def _get_parser(self) -> PushoverColumnShearParser:
        """Get or create parser instance (cached)."""
        if self._parser is None:
            self._parser = PushoverColumnShearParser(self.file_path)
        return self._parser

    def _create_stats_dict(self) -> Dict[str, Any]:
        """Create statistics dictionary for column shears."""
        return {
            'x_v2_shears': 0,
            'x_v3_shears': 0,
            'y_v2_shears': 0,
            'y_v3_shears': 0,
            'errors': [],
            'result_set_id': self.result_set_id,
        }

    def _ensure_entities(self):
        """Ensure all stories and column elements from data exist in database."""
        parser = self._get_parser()

        # Get columns and stories from first available direction
        if self.selected_load_cases_x:
            results = parser.parse('X')
        elif self.selected_load_cases_y:
            results = parser.parse('Y')
        else:
            return

        if results.shears_v2 is None:
            return

        df = results.shears_v2

        # Extract and create column elements (first column)
        column_names = df.iloc[:, 0].unique().tolist()
        for column_name in column_names:
            column_name_str = str(column_name)
            self._get_or_create_element(column_name_str, 'Column')

        # Extract and create stories (second column)
        story_names = df.iloc[:, 1].unique().tolist()
        for story_name in story_names:
            story_name_str = str(story_name)
            self._get_or_create_story(story_name_str)

    def _import_direction(self, direction: str, selected_load_cases: Set[str]) -> Dict:
        """Import data for one direction."""
        stats = {'v2_shears': 0, 'v3_shears': 0, 'errors': []}
        parser = self._get_parser()
        results = parser.parse(direction)

        # Import V2 shears
        if results.shears_v2 is not None:
            stats['v2_shears'] = self._import_shears(
                results.shears_v2, 'V2', selected_load_cases
            )

        # Import V3 shears
        if results.shears_v3 is not None:
            stats['v3_shears'] = self._import_shears(
                results.shears_v3, 'V3', selected_load_cases
            )

        return stats

    def _import_shears(
        self,
        df: pd.DataFrame,
        direction: str,
        selected_load_cases: Set[str]
    ) -> int:
        """Import column shears from DataFrame.

        Args:
            df: DataFrame with columns: Column, Story, [Load Cases...]
            direction: 'V2' or 'V3'
            selected_load_cases: Set of load cases to import

        Returns:
            Count of imported records
        """
        count = 0
        column_col = df.columns[0]  # 'Column'
        story_col = df.columns[1]  # 'Story'

        for _, row in df.iterrows():
            column_name = str(row[column_col])
            story_name = str(row[story_col])

            # Look up element and story from cache
            element = self.elements_cache.get(f"Column:{column_name}")
            story = self.stories_cache.get(story_name)

            if not element or not story:
                continue

            # Import each load case column
            for load_case_name in df.columns[2:]:
                if load_case_name not in selected_load_cases:
                    continue

                value = row[load_case_name]
                if pd.isna(value):
                    continue

                load_case = self._get_or_create_load_case(load_case_name)

                shear = ColumnShear(
                    element_id=element.id,
                    story_id=story.id,
                    load_case_id=load_case.id,
                    direction=direction,
                    force=float(value),
                    story_sort_order=story.sort_order,
                )
                self.session.add(shear)
                count += 1

        return count

    def _build_cache(self):
        """Build element results cache for column shears."""
        # Delete existing cache entries
        self.session.query(ElementResultsCache).filter(
            ElementResultsCache.result_set_id == self.result_set_id,
            ElementResultsCache.result_type.in_(['ColumnShears_V2', 'ColumnShears_V3'])
        ).delete(synchronize_session=False)

        # Build cache for V2 and V3
        self._cache_direction('V2')
        self._cache_direction('V3')

        logger.info("Built element cache for column shears")

    def _cache_direction(self, direction: str):
        """Build cache for one shear direction (V2 or V3)."""
        load_case_ids = self._get_load_case_ids()
        if not load_case_ids:
            logger.warning(f"No load cases in cache for {direction}")
            return

        # Query all column shears for this direction
        records = self.session.query(
            ColumnShear,
            LoadCase.name,
            ColumnShear.element_id,
            ColumnShear.story_id,
            ColumnShear.story_sort_order
        ).join(
            LoadCase, ColumnShear.load_case_id == LoadCase.id
        ).filter(
            ColumnShear.load_case_id.in_(load_case_ids),
            ColumnShear.direction == direction
        ).all()

        logger.info(f"Query returned {len(records)} column shear records for {direction}")

        if not records:
            return

        # Group by element and story
        element_story_data = {}
        for shear, load_case_name, element_id, story_id, story_sort_order in records:
            key = (element_id, story_id)
            if key not in element_story_data:
                element_story_data[key] = {
                    'results_matrix': {},
                    'story_sort_order': story_sort_order
                }
            element_story_data[key]['results_matrix'][load_case_name] = shear.force

        # Create cache entries
        result_type = f"ColumnShears_{direction}"
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


# Alias for backward compatibility
PushoverColumnShearImporter = PushoverColumnShearImporterV2
