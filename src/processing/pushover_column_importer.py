"""
Pushover Column Results Importer

Imports pushover column hinge rotations into the database.
Similar to NLTHA column rotations but for pushover analysis data.
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
    ColumnRotation,
)
from processing.pushover_column_parser import PushoverColumnParser

logger = logging.getLogger(__name__)


class PushoverColumnImporter:
    """Importer for pushover column hinge rotations.

    Imports column rotation values (R2 and R3) from Excel files
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
            result_set_id: ID of the result set to add column results to
            file_path: Path to Excel file containing column results
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
        self.columns_cache = {}  # column_name → Element object (Column type)
        self.unique_name_story_map = {}  # unique_name → story_name (from Excel data)

    def import_all(self) -> Dict:
        """Import all pushover column results.

        Returns:
            Dict with import statistics
        """
        try:
            self._log_progress("Loading result set...", 0, 100)

            # Get existing result set
            self.result_set = self.session.query(ResultSet).get(self.result_set_id)
            if not self.result_set:
                raise ValueError(f"Result set ID {self.result_set_id} not found")

            # Ensure stories and elements exist
            self._ensure_stories_and_elements()

            # Import data for each direction
            stats = {
                'x_r2_rotations': 0,
                'x_r3_rotations': 0,
                'y_r2_rotations': 0,
                'y_r3_rotations': 0,
                'errors': []
            }

            parser = PushoverColumnParser(self.file_path)

            # Import X direction
            if self.selected_load_cases_x:
                self._log_progress("Importing X direction...", 30, 100)
                x_stats = self._import_direction(parser, 'X', self.selected_load_cases_x)
                stats['x_r2_rotations'] += x_stats['r2_rotations']
                stats['x_r3_rotations'] += x_stats['r3_rotations']

            # Import Y direction
            if self.selected_load_cases_y:
                self._log_progress("Importing Y direction...", 60, 100)
                y_stats = self._import_direction(parser, 'Y', self.selected_load_cases_y)
                stats['y_r2_rotations'] += y_stats['r2_rotations']
                stats['y_r3_rotations'] += y_stats['r3_rotations']

            # Flush all records
            self._log_progress("Flushing data...", 90, 100)
            self.session.flush()
            logger.info(f"Flushed all column rotation records to database")

            # Build element results cache
            self._log_progress("Building cache...", 95, 100)
            self._build_element_cache()

            self._log_progress("Import complete!", 100, 100)
            self.session.commit()

            return stats

        except Exception as e:
            self.session.rollback()
            logger.exception("Pushover column import failed")
            raise

    def _import_direction(self, parser: PushoverColumnParser, direction: str, selected_load_cases: Set[str]) -> Dict:
        """Import data for one direction.

        Args:
            parser: Parser for Excel file
            direction: 'X' or 'Y'
            selected_load_cases: Set of load cases to import

        Returns:
            Dict with counts of imported records
        """
        stats = {'r2_rotations': 0, 'r3_rotations': 0}

        # Parse column results
        results = parser.parse(direction)

        # Import R2 rotations
        if results.rotations_r2 is not None:
            stats['r2_rotations'] += self._import_rotations(results.rotations_r2, 'R2', selected_load_cases)

        # Import R3 rotations
        if results.rotations_r3 is not None:
            stats['r3_rotations'] += self._import_rotations(results.rotations_r3, 'R3', selected_load_cases)

        return stats

    def _import_rotations(self, df: pd.DataFrame, direction: str, selected_load_cases: Set[str]) -> int:
        """Import column rotations from DataFrame.

        Args:
            df: DataFrame with columns: Frame/Wall, Unique Name, [Load Cases...]
            direction: 'R2' or 'R3'
            selected_load_cases: Set of load cases to import

        Returns:
            Count of imported records
        """
        count = 0

        # Get column and unique name column names (first two columns)
        column_col = df.columns[0]  # 'Frame/Wall'
        unique_name_col = df.columns[1]  # 'Unique Name'

        for _, row in df.iterrows():
            column_name = str(row[column_col])
            unique_name = str(int(float(row[unique_name_col])))  # Convert float to int to string

            # Look up column element and story
            element = self.columns_cache.get(column_name)
            story_name = self.unique_name_story_map.get(unique_name)
            story = self.stories_cache.get(story_name) if story_name else None

            if not element or not story:
                continue

            # Import each load case column
            for load_case_name in df.columns[2:]:  # Skip column and unique name columns
                if load_case_name not in selected_load_cases:
                    continue

                value = row[load_case_name]

                if pd.isna(value):
                    continue

                # Get or create load case
                load_case = self._get_or_create_load_case(load_case_name)

                # Get story order (use global story order for columns)
                story_sort_order = story.sort_order

                # Create column rotation record
                rotation = ColumnRotation(
                    element_id=element.id,
                    story_id=story.id,
                    load_case_id=load_case.id,
                    direction=direction,
                    rotation=float(value),
                    story_sort_order=story_sort_order,
                )

                self.session.add(rotation)
                count += 1

        return count

    def _ensure_stories_and_elements(self):
        """Ensure all stories and column elements from data exist in database."""
        parser = PushoverColumnParser(self.file_path)

        # Get columns and stories from first parse
        if self.selected_load_cases_x:
            results = parser.parse('X')
        elif self.selected_load_cases_y:
            results = parser.parse('Y')
        else:
            return

        if results.rotations_r2 is None:
            return

        df = results.rotations_r2

        # Extract column names from DataFrame
        column_names = df.iloc[:, 0].unique().tolist()

        # Create/get elements (columns)
        for column_name in column_names:
            column_name_str = str(column_name)

            element = self.session.query(Element).filter(
                Element.project_id == self.project_id,
                Element.name == column_name_str,
                Element.element_type == 'Column'
            ).first()

            if not element:
                element = Element(
                    project_id=self.project_id,
                    name=column_name_str,
                    element_type='Column'
                )
                self.session.add(element)
                self.session.flush()

            self.columns_cache[column_name_str] = element

        # Build unique name → story mapping from raw Excel data
        # Read raw data to get Story column
        raw_df = pd.read_excel(parser.excel_data, sheet_name='Fiber Hinge States', header=1)
        raw_df = raw_df.drop(0)  # Drop units row

        for _, row in raw_df.iterrows():
            unique_name = str(int(float(row['Unique Name'])))
            story_name = str(row['Story'])
            self.unique_name_story_map[unique_name] = story_name

        # Create/get stories
        unique_story_names = set(self.unique_name_story_map.values())

        for story_name in unique_story_names:
            if story_name not in self.stories_cache:
                story = self.session.query(Story).filter(
                    Story.project_id == self.project_id,
                    Story.name == story_name
                ).first()

                if not story:
                    # Assign a default sort order (will be overwritten by global results if imported)
                    story = Story(
                        project_id=self.project_id,
                        name=story_name,
                        sort_order=0
                    )
                    self.session.add(story)
                    self.session.flush()

                self.stories_cache[story_name] = story

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
        """Build element results cache for column rotations."""
        from database.models import ElementResultsCache

        # Delete existing element cache for this result set (column rotations only)
        self.session.query(ElementResultsCache).filter(
            ElementResultsCache.result_set_id == self.result_set_id,
            ElementResultsCache.result_type.in_(['ColumnRotations_R2', 'ColumnRotations_R3'])
        ).delete(synchronize_session=False)

        # Build cache for each direction (R2 and R3)
        self._cache_column_direction('R2')
        self._cache_column_direction('R3')

        logger.info(f"Built element cache for column rotations")

    def _cache_column_direction(self, direction: str):
        """Build cache for one column rotation direction (R2 or R3).

        Args:
            direction: 'R2' or 'R3'
        """
        from database.models import ElementResultsCache, ColumnRotation, LoadCase

        # Get load case IDs
        load_case_ids = [lc.id for lc in self.load_cases_cache.values()]

        if not load_case_ids:
            logger.warning(f"No load cases in cache for {direction}")
            return

        # Query all column rotations for this direction and result set
        records = self.session.query(
            ColumnRotation,
            LoadCase.name,
            ColumnRotation.element_id,
            ColumnRotation.story_id,
            ColumnRotation.story_sort_order
        ).join(
            LoadCase, ColumnRotation.load_case_id == LoadCase.id
        ).filter(
            ColumnRotation.load_case_id.in_(load_case_ids),
            ColumnRotation.direction == direction
        ).all()

        logger.info(f"Query returned {len(records)} column rotation records for {direction}")

        if not records:
            logger.warning(f"No column rotation records found for {direction}")
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
        result_type = f"ColumnRotations_{direction}"

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
