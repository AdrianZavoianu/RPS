"""
Pushover Wall Results Importer (v2 - using Template Method pattern)

Imports pushover wall (pier) shear forces and quad rotations into the database.
This version extends BasePushoverImporter for reduced code duplication.

Note: This importer handles two element types:
- Wall (Pier) for shear forces (V2/V3)
- Quad for rotations
"""

import logging
from typing import Dict, List, Set, Any

import pandas as pd

from database.models import (
    Element,
    Story,
    LoadCase,
    WallShear,
    QuadRotation,
    ElementResultsCache,
)
from processing.pushover.pushover_base_importer import BasePushoverImporter
from processing.pushover.pushover_wall_parser import PushoverWallParser

logger = logging.getLogger(__name__)


class PushoverWallImporterV2(BasePushoverImporter):
    """Importer for pushover wall (pier) shear forces and quad rotations.

    Imports pier-level shear forces (V2 and V3) and quad rotations from Excel
    files for both X and Y directions.

    This is a refactored version using the Template Method pattern,
    reducing ~560 lines to ~280 lines.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._parser = None
        # Separate cache for quad elements
        self.quads_cache: Dict[str, Element] = {}

    def _get_parser(self) -> PushoverWallParser:
        """Get or create parser instance (cached)."""
        if self._parser is None:
            self._parser = PushoverWallParser(self.file_path)
        return self._parser

    def _create_stats_dict(self) -> Dict[str, Any]:
        """Create statistics dictionary for wall results."""
        return {
            'x_v2_shears': 0,
            'x_v3_shears': 0,
            'y_v2_shears': 0,
            'y_v3_shears': 0,
            'x_rotations': 0,
            'y_rotations': 0,
            'errors': [],
            'result_set_id': self.result_set_id,
        }

    def _ensure_entities(self):
        """Ensure all stories, pier elements, and quad elements exist."""
        parser = self._get_parser()

        # Get data from first available direction
        if self.selected_load_cases_x:
            results = parser.parse('X')
        elif self.selected_load_cases_y:
            results = parser.parse('Y')
        else:
            return

        # Process pier elements and stories from shears
        if results.shears_v2 is not None:
            self._ensure_piers_and_stories(results.shears_v2)

        # Process quad elements from rotations
        if results.rotations is not None:
            self._ensure_quads(results.rotations)

    def _ensure_piers_and_stories(self, df: pd.DataFrame):
        """Create pier elements and stories from shear DataFrame."""
        pier_col = df.columns[0]  # 'Pier'
        story_col = df.columns[1]  # 'Story'

        # Create pier elements
        pier_names = df[pier_col].unique().tolist()
        for pier_name in pier_names:
            pier_name_str = str(pier_name)
            self._get_or_create_element(pier_name_str, 'Wall')

        # Create stories and track order per pier
        for pier_name in pier_names:
            pier_df = df[df[pier_col] == pier_name]
            story_names = pier_df[story_col].tolist()

            for idx, story_name in enumerate(story_names):
                story_name_str = str(story_name)
                self._get_or_create_story(story_name_str, sort_order=idx)

                # Track per-pier story order
                story_order_key = (str(pier_name), story_name_str)
                self.story_order[story_order_key] = idx

    def _ensure_quads(self, df: pd.DataFrame):
        """Create quad elements from rotation DataFrame."""
        name_col = df.columns[0]  # 'Name'

        quad_names = df[name_col].unique().tolist()
        for quad_name_float in quad_names:
            # Quad names come as floats in Excel
            quad_name_str = str(int(float(quad_name_float)))
            element = self._get_or_create_element(quad_name_str, 'Quad')
            self.quads_cache[quad_name_str] = element

    def _import_direction(self, direction: str, selected_load_cases: Set[str]) -> Dict:
        """Import data for one direction."""
        stats = {'v2_shears': 0, 'v3_shears': 0, 'rotations': 0, 'errors': []}
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

        # Import rotations
        if results.rotations is not None:
            stats['rotations'] = self._import_rotations(
                results.rotations, selected_load_cases
            )

        return stats

    def _import_shears(
        self,
        df: pd.DataFrame,
        direction: str,
        selected_load_cases: Set[str]
    ) -> int:
        """Import wall shears from DataFrame.

        Args:
            df: DataFrame with columns: Pier, Story, [Load Cases...]
            direction: 'V2' or 'V3'
            selected_load_cases: Set of load cases to import

        Returns:
            Count of imported records
        """
        count = 0
        pier_col = df.columns[0]
        story_col = df.columns[1]

        for _, row in df.iterrows():
            pier_name = str(row[pier_col])
            story_name = str(row[story_col])

            element = self.elements_cache.get(f"Wall:{pier_name}")
            story = self.stories_cache.get(story_name)

            if not element or not story:
                continue

            # Get per-pier story order
            story_order_key = (pier_name, story_name)
            story_sort_order = self.story_order.get(story_order_key, story.sort_order)

            for load_case_name in df.columns[2:]:
                if load_case_name not in selected_load_cases:
                    continue

                value = row[load_case_name]
                if pd.isna(value):
                    continue

                load_case = self._get_or_create_load_case(load_case_name)

                shear = WallShear(
                    element_id=element.id,
                    story_id=story.id,
                    load_case_id=load_case.id,
                    direction=direction,
                    location='Bottom',  # Pushover uses bottom location
                    force=float(value),
                    story_sort_order=story_sort_order,
                )
                self.session.add(shear)
                count += 1

        return count

    def _import_rotations(
        self,
        df: pd.DataFrame,
        selected_load_cases: Set[str]
    ) -> int:
        """Import quad rotations from DataFrame.

        Args:
            df: DataFrame with columns: Name, Story, [Load Cases...]
            selected_load_cases: Set of load cases to import

        Returns:
            Count of imported records
        """
        count = 0
        name_col = df.columns[0]
        story_col = df.columns[1]

        for _, row in df.iterrows():
            # Element name comes as float
            element_name = str(int(float(row[name_col])))
            story_name = str(row[story_col])

            element = self.quads_cache.get(element_name)
            story = self.stories_cache.get(story_name)

            if not element or not story:
                continue

            for load_case_name in df.columns[2:]:
                if load_case_name not in selected_load_cases:
                    continue

                value = row[load_case_name]
                if pd.isna(value):
                    continue

                load_case = self._get_or_create_load_case(load_case_name)

                rotation = QuadRotation(
                    element_id=element.id,
                    story_id=story.id,
                    load_case_id=load_case.id,
                    rotation=float(value),
                    story_sort_order=story.sort_order,  # Global order for quads
                )
                self.session.add(rotation)
                count += 1

        return count

    def _build_cache(self):
        """Build element results cache for wall shears and quad rotations."""
        # Delete existing cache entries
        self.session.query(ElementResultsCache).filter(
            ElementResultsCache.result_set_id == self.result_set_id,
            ElementResultsCache.result_type.in_([
                'WallShears_V2', 'WallShears_V3', 'QuadRotations'
            ])
        ).delete(synchronize_session=False)

        # Build cache for wall shears
        self._cache_wall_shears('V2')
        self._cache_wall_shears('V3')

        # Build cache for quad rotations
        self._cache_quad_rotations()

        logger.info("Built element cache for wall shears and quad rotations")

    def _cache_wall_shears(self, direction: str):
        """Build cache for one wall shear direction (V2 or V3)."""
        load_case_ids = self._get_load_case_ids()
        if not load_case_ids:
            return

        records = self.session.query(
            WallShear,
            LoadCase.name,
            WallShear.element_id,
            WallShear.story_id,
            WallShear.story_sort_order
        ).join(
            LoadCase, WallShear.load_case_id == LoadCase.id
        ).filter(
            WallShear.load_case_id.in_(load_case_ids),
            WallShear.direction == direction
        ).all()

        logger.info(f"Query returned {len(records)} wall shear records for {direction}")

        if not records:
            return

        element_story_data = {}
        for shear, load_case_name, element_id, story_id, story_sort_order in records:
            key = (element_id, story_id)
            if key not in element_story_data:
                element_story_data[key] = {
                    'results_matrix': {},
                    'story_sort_order': story_sort_order
                }
            element_story_data[key]['results_matrix'][load_case_name] = shear.force

        result_type = f"WallShears_{direction}"
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

    def _cache_quad_rotations(self):
        """Build cache for quad rotations."""
        load_case_ids = self._get_load_case_ids()
        if not load_case_ids:
            return

        records = self.session.query(
            QuadRotation,
            LoadCase.name,
            QuadRotation.element_id,
            QuadRotation.story_id,
            QuadRotation.story_sort_order
        ).join(
            LoadCase, QuadRotation.load_case_id == LoadCase.id
        ).filter(
            QuadRotation.load_case_id.in_(load_case_ids)
        ).all()

        logger.info(f"Query returned {len(records)} quad rotation records")

        if not records:
            return

        element_story_data = {}
        for rotation, load_case_name, element_id, story_id, story_sort_order in records:
            key = (element_id, story_id)
            if key not in element_story_data:
                element_story_data[key] = {
                    'results_matrix': {},
                    'story_sort_order': story_sort_order
                }
            element_story_data[key]['results_matrix'][load_case_name] = rotation.rotation

        result_type = "QuadRotations"
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
PushoverWallImporter = PushoverWallImporterV2
