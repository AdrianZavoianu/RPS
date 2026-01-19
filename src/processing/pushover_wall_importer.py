"""
Pushover Wall Results Importer

Imports pushover wall (pier) shear forces into the database.
Similar to NLTHA wall shear importer but for pushover analysis data.
"""

import logging
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set

import pandas as pd
from sqlalchemy.orm import Session

from database.models import (
    Project,
    ResultSet,
    Story,
    LoadCase,
    Element,
    WallShear,
)
from processing.pushover_wall_parser import PushoverWallParser

logger = logging.getLogger(__name__)


class PushoverWallImporter:
    """Importer for pushover wall (pier) shear forces.

    Imports pier-level shear forces (V2 and V3) from Excel files
    for both X and Y directions.
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
            result_set_id: ID of the result set to add wall results to
            file_path: Path to Excel file containing wall results
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

        self.result_set = None
        self.stories_cache = {}  # story_name → Story object
        self.load_cases_cache = {}  # load_case_name → LoadCase object
        self.elements_cache = {}  # pier_name → Element object (Wall type)
        self.quads_cache = {}  # quad_name → Element object (Quad type)
        self.story_order = {}  # (pier_name, story_name) → order index

    def import_all(self) -> Dict:
        """Import all pushover wall results.

        Returns:
            Dict with import statistics
        """
        try:
            self._log_progress("Loading result set...", 0, 100)

            # Get existing result set
            self.result_set = self.session.query(ResultSet).get(self.result_set_id)
            if not self.result_set:
                raise ValueError(f"Result set ID {self.result_set_id} not found")

            parser = PushoverWallParser(self.file_path)

            # Ensure stories and elements exist
            self._ensure_stories_and_elements(parser)

            # Import data for each direction
            stats = {
                'x_v2_shears': 0,
                'x_v3_shears': 0,
                'y_v2_shears': 0,
                'y_v3_shears': 0,
                'x_rotations': 0,
                'y_rotations': 0,
                'errors': []
            }

            # Import X direction
            if self.selected_load_cases_x:
                self._log_progress("Importing X direction...", 30, 100)
                x_stats = self._import_direction(parser, 'X', self.selected_load_cases_x)
                stats['x_v2_shears'] += x_stats['v2_shears']
                stats['x_v3_shears'] += x_stats['v3_shears']
                stats['x_rotations'] += x_stats['rotations']

            # Import Y direction
            if self.selected_load_cases_y:
                self._log_progress("Importing Y direction...", 60, 100)
                y_stats = self._import_direction(parser, 'Y', self.selected_load_cases_y)
                stats['y_v2_shears'] += y_stats['v2_shears']
                stats['y_v3_shears'] += y_stats['v3_shears']
                stats['y_rotations'] += y_stats['rotations']

            # Flush all records
            self._log_progress("Flushing data...", 90, 100)
            self.session.flush()
            logger.info(f"Flushed all wall shear records to database")

            # Build element results cache
            self._log_progress("Building cache...", 95, 100)
            self._build_element_cache()

            self._log_progress("Import complete!", 100, 100)
            self.session.commit()

            return stats

        except Exception as e:
            self.session.rollback()
            logger.exception("Pushover wall import failed")
            raise

    def _import_direction(self, parser: PushoverWallParser, direction: str, selected_load_cases: Set[str]) -> Dict:
        """Import data for one direction.

        Args:
            parser: Parser for Excel file
            direction: 'X' or 'Y'
            selected_load_cases: Set of load cases to import

        Returns:
            Dict with counts of imported records
        """
        stats = {'v2_shears': 0, 'v3_shears': 0, 'rotations': 0}

        # Parse wall results
        results = parser.parse(direction)

        # Import V2 shears
        if results.shears_v2 is not None:
            stats['v2_shears'] += self._import_shears(results.shears_v2, 'V2', selected_load_cases)

        # Import V3 shears
        if results.shears_v3 is not None:
            stats['v3_shears'] += self._import_shears(results.shears_v3, 'V3', selected_load_cases)

        # Import rotations
        if results.rotations is not None:
            stats['rotations'] += self._import_rotations(results.rotations, selected_load_cases)

        return stats

    def _import_shears(self, df: pd.DataFrame, direction: str, selected_load_cases: Set[str]) -> int:
        """Import wall shears from DataFrame.

        Args:
            df: DataFrame with columns: Pier, Story, [Load Cases...]
            direction: 'V2' or 'V3'
            selected_load_cases: Set of load cases to import

        Returns:
            Count of imported records
        """
        count = 0

        # Get pier and story column names (first two columns)
        pier_col = df.columns[0]
        story_col = df.columns[1]

        for _, row in df.iterrows():
            pier_name = str(row[pier_col])
            story_name = str(row[story_col])

            element = self.elements_cache.get(pier_name)
            story = self.stories_cache.get(story_name)

            if not element or not story:
                continue

            # Import each load case column
            for load_case_name in df.columns[2:]:  # Skip pier and story columns
                if load_case_name not in selected_load_cases:
                    continue

                value = row[load_case_name]

                if pd.isna(value):
                    continue

                # Get or create load case
                load_case = self._get_or_create_load_case(load_case_name)

                # Get story order for this pier
                story_order_key = (pier_name, story_name)
                story_sort_order = self.story_order.get(story_order_key)

                # Create wall shear record
                shear = WallShear(
                    element_id=element.id,
                    story_id=story.id,
                    load_case_id=load_case.id,
                    direction=direction,
                    location='Bottom',  # Pushover uses bottom location (per ETPS pattern)
                    force=float(value),
                    story_sort_order=story_sort_order,
                )

                self.session.add(shear)
                count += 1

        return count

    def _import_rotations(self, df: pd.DataFrame, selected_load_cases: Set[str]) -> int:
        """Import quad rotations from DataFrame.

        Args:
            df: DataFrame with columns: Name, Story, [Load Cases...]
            selected_load_cases: Set of load cases to import

        Returns:
            Count of imported records
        """
        from database.models import QuadRotation

        count = 0

        # Get element name and story column names (first two columns)
        name_col = df.columns[0]  # 'Name'
        story_col = df.columns[1]  # 'Story'

        for _, row in df.iterrows():
            # Convert element name to string (comes as float)
            element_name = str(int(float(row[name_col])))
            story_name = str(row[story_col])

            # Look up element in quads_cache (quad elements)
            element = self.quads_cache.get(element_name)
            story = self.stories_cache.get(story_name)

            if not element or not story:
                continue

            # Import each load case column
            for load_case_name in df.columns[2:]:  # Skip name and story columns
                if load_case_name not in selected_load_cases:
                    continue

                value = row[load_case_name]

                if pd.isna(value):
                    continue

                # Get or create load case
                load_case = self._get_or_create_load_case(load_case_name)

                # Get story order for this element (use global order, same as NLTHA)
                story_sort_order = story.sort_order

                # Create quad rotation record
                rotation = QuadRotation(
                    element_id=element.id,
                    story_id=story.id,
                    load_case_id=load_case.id,
                    rotation=float(value),
                    story_sort_order=story_sort_order,
                )

                self.session.add(rotation)
                count += 1

        return count

    def _ensure_stories_and_elements(self, parser: PushoverWallParser):
        """Ensure all stories and pier elements from data exist in database."""

        # Get piers and stories from first parse
        if self.selected_load_cases_x:
            results = parser.parse('X')
        elif self.selected_load_cases_y:
            results = parser.parse('Y')
        else:
            return

        if results.shears_v2 is None:
            return

        # Extract pier names and story names from DataFrame
        pier_names = results.shears_v2.iloc[:, 0].unique().tolist()
        df = results.shears_v2

        # Create/get elements (piers)
        for pier_name in pier_names:
            pier_name_str = str(pier_name)

            element = self.session.query(Element).filter(
                Element.project_id == self.project_id,
                Element.name == pier_name_str,
                Element.element_type == 'Wall'  # Piers are walls
            ).first()

            if not element:
                element = Element(
                    project_id=self.project_id,
                    name=pier_name_str,
                    element_type='Wall'
                )
                self.session.add(element)
                self.session.flush()

            self.elements_cache[pier_name_str] = element

        # Create/get stories and track order per pier
        for pier_name in pier_names:
            pier_df = df[df.iloc[:, 0] == pier_name]
            story_names = pier_df.iloc[:, 1].tolist()

            for idx, story_name in enumerate(story_names):
                story_name_str = str(story_name)

                # Create/get story (if not already cached)
                if story_name_str not in self.stories_cache:
                    story = self.session.query(Story).filter(
                        Story.project_id == self.project_id,
                        Story.name == story_name_str
                    ).first()

                    if not story:
                        story = Story(
                            project_id=self.project_id,
                            name=story_name_str,
                            sort_order=idx  # Will be overwritten if multiple piers
                        )
                        self.session.add(story)
                        self.session.flush()

                    self.stories_cache[story_name_str] = story

                # Track story order for this pier (per-element ordering)
                story_order_key = (str(pier_name), story_name_str)
                self.story_order[story_order_key] = idx

        # Create/get quad elements from rotations data
        if results.rotations is not None:
            # Extract quad names from DataFrame (first column is 'Name')
            quad_names = results.rotations.iloc[:, 0].unique().tolist()

            for quad_name_float in quad_names:
                # Convert to string (quad names come as floats)
                quad_name_str = str(int(float(quad_name_float)))

                element = self.session.query(Element).filter(
                    Element.project_id == self.project_id,
                    Element.name == quad_name_str,
                    Element.element_type == 'Quad'  # Quad elements
                ).first()

                if not element:
                    element = Element(
                        project_id=self.project_id,
                        name=quad_name_str,
                        element_type='Quad'
                    )
                    self.session.add(element)
                    self.session.flush()

                self.quads_cache[quad_name_str] = element

    def _get_or_create_load_case(self, load_case_name: str) -> LoadCase:
        """Get or create load case."""
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

    def _build_element_cache(self):
        """Build element results cache for wall shears and quad rotations."""
        from database.models import ElementResultsCache

        # Delete existing element cache for this result set (wall shears and quad rotations)
        self.session.query(ElementResultsCache).filter(
            ElementResultsCache.result_set_id == self.result_set_id,
            ElementResultsCache.result_type.in_(['WallShears_V2', 'WallShears_V3', 'QuadRotations'])
        ).delete(synchronize_session=False)

        # Build cache for wall shears (V2 and V3)
        self._cache_wall_direction('V2')
        self._cache_wall_direction('V3')

        # Build cache for quad rotations
        self._cache_quad_rotations()

        logger.info(f"Built element cache for wall shears and quad rotations")

    def _cache_wall_direction(self, direction: str):
        """Build cache for one wall shear direction (V2 or V3).

        Args:
            direction: 'V2' or 'V3'
        """
        from database.models import ElementResultsCache, WallShear, LoadCase

        # Get load case IDs
        load_case_ids = [lc.id for lc in self.load_cases_cache.values()]

        if not load_case_ids:
            logger.warning(f"No load cases in cache for {direction}")
            return

        # Query all wall shears for this direction and result set
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
            logger.warning(f"No wall shear records found for {direction}")
            return

        # Group by element and story
        # Format: {(element_id, story_id): {'results_matrix': {load_case_name: value, ...}, 'story_sort_order': order}}
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
        """Build cache for quad rotations.

        Note: Unlike wall shears which use per-pier story ordering, quad rotations
        use global story ordering (same as NLTHA pattern).
        """
        from database.models import ElementResultsCache, QuadRotation, LoadCase

        # Get load case IDs
        load_case_ids = [lc.id for lc in self.load_cases_cache.values()]

        if not load_case_ids:
            logger.warning(f"No load cases in cache for quad rotations")
            return

        # Query all quad rotations for this result set
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
            logger.warning(f"No quad rotation records found")
            return

        # Group by element and story
        # Format: {(element_id, story_id): {'results_matrix': {load_case_name: value, ...}, 'story_sort_order': order}}
        element_story_data = {}

        for rotation, load_case_name, element_id, story_id, story_sort_order in records:
            key = (element_id, story_id)

            if key not in element_story_data:
                element_story_data[key] = {
                    'results_matrix': {},
                    'story_sort_order': story_sort_order  # Global story order
                }

            element_story_data[key]['results_matrix'][load_case_name] = rotation.rotation

        # Create cache entries
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

    def _log_progress(self, message: str, current: int, total: int):
        """Log progress message."""
        if self.progress_callback:
            self.progress_callback(message, current, total)
        logger.info(f"{message} ({current}/{total})")
