"""
Pushover Global Results Importer

Imports pushover global results (drifts, displacements, forces) into the database.
Similar to NLTHA folder importer but for pushover analysis data.
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
    StoryDrift,
    StoryDisplacement,
    StoryForce,
    GlobalResultsCache,
)
from processing.pushover_global_parser import PushoverGlobalParser

logger = logging.getLogger(__name__)


def ensure_pushover_result_set(
    session: Session,
    project_id: int,
    result_set_name: str,
) -> ResultSet:
    """Ensure a pushover result set exists for the project."""
    result_set = session.query(ResultSet).filter(
        ResultSet.project_id == project_id,
        ResultSet.name == result_set_name,
    ).first()

    if not result_set:
        result_set = ResultSet(
            project_id=project_id,
            name=result_set_name,
            description="Pushover global results",
            analysis_type="Pushover",
        )
        session.add(result_set)
        session.flush()
        return result_set

    if getattr(result_set, "analysis_type", None) != "Pushover":
        result_set.analysis_type = "Pushover"
    if not getattr(result_set, "description", None):
        result_set.description = "Pushover global results"
    return result_set


class PushoverGlobalImporter:
    """Importer for pushover global results.

    Imports story-level results (drifts, displacements, forces) from Excel files
    for both X and Y directions.
    """

    def __init__(
        self,
        project_id: int,
        session: Session,
        folder_path: Path,
        result_set_name: str,
        valid_files: List[Path],
        selected_load_cases_x: List[str],
        selected_load_cases_y: List[str],
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
    ):
        """Initialize importer.

        Args:
            project_id: ID of the project
            session: Database session
            folder_path: Path to folder containing Excel files
            result_set_name: Name for the result set
            valid_files: List of valid Excel file paths
            selected_load_cases_x: List of selected load cases for X direction
            selected_load_cases_y: List of selected load cases for Y direction
            progress_callback: Optional callback for progress updates
        """
        self.project_id = project_id
        self.session = session
        self.folder_path = folder_path
        self.result_set_name = result_set_name
        self.valid_files = valid_files
        self.selected_load_cases_x = set(selected_load_cases_x)
        self.selected_load_cases_y = set(selected_load_cases_y)
        self.progress_callback = progress_callback

        self.result_set = None
        self.stories_cache = {}  # story_name → Story object
        self.load_cases_cache = {}  # load_case_name → LoadCase object
        self.story_order = {}  # story_name → order index (from Excel sheet order)

    def import_all(self) -> Dict:
        """Import all pushover global results.

        Returns:
            Dict with import statistics
        """
        try:
            self._log_progress("Creating result set...", 0, 100)

            # Create or get result set
            self.result_set = self._get_or_create_result_set()

            first_parser = None
            if self.valid_files:
                first_parser = PushoverGlobalParser(self.valid_files[0])

            # Ensure stories exist
            self._ensure_stories(first_parser)

            # Import data for each direction
            stats = {
                'files_processed': 0,
                'x_drifts': 0,
                'x_displacements': 0,
                'x_forces': 0,
                'y_drifts': 0,
                'y_displacements': 0,
                'y_forces': 0,
                'errors': []
            }

            total_tasks = len(self.valid_files) * 2  # X and Y for each file
            current_task = 0

            for file_path in self.valid_files:
                try:
                    if first_parser and file_path == self.valid_files[0]:
                        parser = first_parser
                    else:
                        parser = PushoverGlobalParser(file_path)

                    # Import X direction
                    if self.selected_load_cases_x:
                        current_task += 1
                        self._log_progress(f"Importing X from {file_path.name}...", current_task, total_tasks)

                        x_stats = self._import_direction(parser, 'X', self.selected_load_cases_x)
                        stats['x_drifts'] += x_stats['drifts']
                        stats['x_displacements'] += x_stats['displacements']
                        stats['x_forces'] += x_stats['forces']

                    # Import Y direction
                    if self.selected_load_cases_y:
                        current_task += 1
                        self._log_progress(f"Importing Y from {file_path.name}...", current_task, total_tasks)

                        y_stats = self._import_direction(parser, 'Y', self.selected_load_cases_y)
                        stats['y_drifts'] += y_stats['drifts']
                        stats['y_displacements'] += y_stats['displacements']
                        stats['y_forces'] += y_stats['forces']

                    stats['files_processed'] += 1

                except Exception as e:
                    error_msg = f"Failed to import {file_path.name}: {str(e)}"
                    logger.exception(error_msg)
                    stats['errors'].append(error_msg)

            # Flush all pending records before building cache
            self._log_progress("Flushing data...", 90, 100)
            self.session.flush()
            logger.info(f"Flushed all records to database")

            # Build cache
            self._log_progress("Building cache...", 95, 100)
            self._build_cache()

            self._log_progress("Import complete!", 100, 100)
            self.session.commit()

            return stats

        except Exception as e:
            self.session.rollback()
            logger.exception("Pushover global import failed")
            raise

    def _import_direction(self, parser: PushoverGlobalParser, direction: str, selected_load_cases: Set[str]) -> Dict:
        """Import data for one direction.

        Args:
            parser: Parser for Excel file
            direction: 'X' or 'Y'
            selected_load_cases: Set of load cases to import

        Returns:
            Dict with counts of imported records
        """
        stats = {'drifts': 0, 'displacements': 0, 'forces': 0}

        # Parse all result types
        results = parser.parse(direction)

        # Import drifts
        if results.drifts is not None:
            stats['drifts'] += self._import_drifts(results.drifts, direction, selected_load_cases)

        # Import displacements
        if results.displacements is not None:
            stats['displacements'] += self._import_displacements(results.displacements, direction, selected_load_cases)

        # Import forces
        if results.forces is not None:
            stats['forces'] += self._import_forces(results.forces, direction, selected_load_cases)

        return stats

    def _import_drifts(self, df: pd.DataFrame, direction: str, selected_load_cases: Set[str]) -> int:
        """Import story drifts from DataFrame."""
        count = 0

        # Get story column name (first column)
        story_col = df.columns[0]

        for _, row in df.iterrows():
            story_name = str(row[story_col])
            story = self.stories_cache.get(story_name)

            if not story:
                continue

            # Import each load case column
            for load_case_name in df.columns[1:]:  # Skip story column
                if load_case_name not in selected_load_cases:
                    continue

                value = row[load_case_name]

                if pd.isna(value):
                    continue

                # Get or create load case
                load_case = self._get_or_create_load_case(load_case_name)

                # Create drift record
                drift = StoryDrift(
                    story_id=story.id,
                    load_case_id=load_case.id,
                    direction=direction,
                    drift=float(value),
                    story_sort_order=self.story_order.get(story_name),
                )

                self.session.add(drift)
                count += 1

        return count

    def _import_displacements(self, df: pd.DataFrame, direction: str, selected_load_cases: Set[str]) -> int:
        """Import story displacements from DataFrame."""
        count = 0

        story_col = df.columns[0]

        for _, row in df.iterrows():
            story_name = str(row[story_col])
            story = self.stories_cache.get(story_name)

            if not story:
                continue

            for load_case_name in df.columns[1:]:
                if load_case_name not in selected_load_cases:
                    continue

                value = row[load_case_name]

                if pd.isna(value):
                    continue

                load_case = self._get_or_create_load_case(load_case_name)

                displacement = StoryDisplacement(
                    story_id=story.id,
                    load_case_id=load_case.id,
                    direction=direction,
                    displacement=float(value),
                    story_sort_order=self.story_order.get(story_name),
                )

                self.session.add(displacement)
                count += 1

        return count

    def _import_forces(self, df: pd.DataFrame, direction: str, selected_load_cases: Set[str]) -> int:
        """Import story forces (shears) from DataFrame."""
        count = 0

        story_col = df.columns[0]

        for _, row in df.iterrows():
            story_name = str(row[story_col])
            story = self.stories_cache.get(story_name)

            if not story:
                continue

            for load_case_name in df.columns[1:]:
                if load_case_name not in selected_load_cases:
                    continue

                value = row[load_case_name]

                if pd.isna(value):
                    continue

                load_case = self._get_or_create_load_case(load_case_name)

                force = StoryForce(
                    story_id=story.id,
                    load_case_id=load_case.id,
                    direction=direction,
                    force=float(value),
                    story_sort_order=self.story_order.get(story_name),
                )

                self.session.add(force)
                count += 1

        return count

    def _get_or_create_result_set(self) -> ResultSet:
        """Get existing or create new result set."""
        result_set = self.session.query(ResultSet).filter(
            ResultSet.project_id == self.project_id,
            ResultSet.name == self.result_set_name
        ).first()

        if not result_set:
            result_set = ResultSet(
                project_id=self.project_id,
                name=self.result_set_name,
                description=f"Pushover global results",
                analysis_type="Pushover"
            )
            self.session.add(result_set)
            self.session.flush()

        return result_set

    def _ensure_stories(self, parser: Optional[PushoverGlobalParser] = None):
        """Ensure all stories from data exist in database."""
        # Get stories from first file
        if not self.valid_files:
            return

        if parser is None:
            parser = PushoverGlobalParser(self.valid_files[0])

        # Get stories from drifts (all result types should have same stories)
        if self.selected_load_cases_x:
            results = parser.parse('X')
        elif self.selected_load_cases_y:
            results = parser.parse('Y')
        else:
            return

        if results.drifts is None:
            return

        story_names = results.drifts.iloc[:, 0].tolist()

        # Create stories if they don't exist and track their Excel sheet order
        for idx, story_name in enumerate(story_names):
            story_name_str = str(story_name)

            story = self.session.query(Story).filter(
                Story.project_id == self.project_id,
                Story.name == story_name_str
            ).first()

            if not story:
                story = Story(
                    project_id=self.project_id,
                    name=story_name_str,
                    sort_order=idx  # Global order
                )
                self.session.add(story)
                self.session.flush()

            self.stories_cache[story_name_str] = story
            # Track story order from Excel sheet (0-based index)
            self.story_order[story_name_str] = idx

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

    def _build_cache(self):
        """Build global results cache for visualization.

        Cache format matches NLTHA pattern:
        - result_type: "Drifts", "Forces", "Displacements" (no direction suffix)
        - results_matrix: {load_case_name: value, ...} for all load cases (X and Y combined)
        """
        # Delete existing cache for this result set
        self.session.query(GlobalResultsCache).filter(
            GlobalResultsCache.result_set_id == self.result_set.id
        ).delete()

        # Cache each result type (merging X and Y data)
        self._cache_result_type('Drifts')
        self._cache_result_type('Displacements')
        self._cache_result_type('Forces')

    def _cache_result_type(self, result_type: str):
        """Build cache for one result type (both X and Y directions combined)."""
        # Map result type to model and direction suffix
        direction_suffix_map = {
            'X': {'Drifts': '_X', 'Forces': '_VX', 'Displacements': '_UX'},
            'Y': {'Drifts': '_Y', 'Forces': '_VY', 'Displacements': '_UY'}
        }

        if result_type == 'Drifts':
            model = StoryDrift
            value_col = 'drift'
        elif result_type == 'Displacements':
            model = StoryDisplacement
            value_col = 'displacement'
        elif result_type == 'Forces':
            model = StoryForce
            value_col = 'force'
        else:
            return

        # Get load case IDs that were imported in this session
        if not self.load_cases_cache:
            logger.warning(f"No load cases in cache for {result_type}")
            return

        load_case_ids = [lc.id for lc in self.load_cases_cache.values()]
        logger.info(f"Building cache for {result_type}: {len(load_case_ids)} load cases")
        logger.debug(f"Load case names: {list(self.load_cases_cache.keys())}")

        # Query data for imported load cases only (both X and Y directions)
        from database.models import LoadCase, Story

        records = self.session.query(model, LoadCase.name, Story.name, model.story_sort_order, model.direction).join(
            LoadCase, model.load_case_id == LoadCase.id
        ).join(
            Story, model.story_id == Story.id
        ).filter(
            model.load_case_id.in_(load_case_ids)
        ).all()

        logger.info(f"Query returned {len(records)} records for {result_type}")

        if not records:
            logger.warning(f"No records found for {result_type}")
            return

        # Debug: Check directions in records
        directions_in_records = set(r[4] for r in records)
        stories_in_records = set(r[2] for r in records)
        logger.debug(f"Directions in records: {directions_in_records}")
        logger.debug(f"Stories in records: {stories_in_records}")

        # Build cache grouped by story
        # Format: {story_id: {load_case_name: value, ...}}
        story_data = {}

        for record, load_case_name, story_name, story_sort_order, direction in records:
            story_id = record.story_id

            if story_id not in story_data:
                story_data[story_id] = {
                    'results_matrix': {},
                    'story_sort_order': story_sort_order,  # From result record (Excel sheet order)
                }

            # Add load case value to results matrix with direction suffix (matching NLTHA pattern)
            # For pushover, replace underscores in load case name to prevent transformer from splitting incorrectly
            # e.g., "Push_X+Ecc+" becomes "Push-X+Ecc+_X" for Drifts X direction
            # The transformer will strip "_X" and display "Push-X+Ecc+"
            suffix = direction_suffix_map[direction][result_type]

            # Replace underscores with hyphens in load case name to prevent split issues
            safe_load_case_name = load_case_name.replace('_', '-')
            load_case_key = f"{safe_load_case_name}{suffix}"
            value = getattr(record, value_col)
            story_data[story_id]['results_matrix'][load_case_key] = value

        # Create cache entries (one per story per result type)
        logger.info(f"Creating {len(story_data)} cache entries for {result_type}")
        for story_id, data in story_data.items():
            story_name = self.session.query(Story).get(story_id).name
            load_case_count = len(data['results_matrix'])
            logger.debug(f"  {story_name}: {load_case_count} load cases")

            cache_entry = GlobalResultsCache(
                project_id=self.project_id,
                result_set_id=self.result_set.id,
                result_type=result_type,  # Just "Drifts", "Forces", "Displacements"
                story_id=story_id,
                results_matrix=data['results_matrix'],
                story_sort_order=data['story_sort_order'],
            )
            self.session.add(cache_entry)

    def _log_progress(self, message: str, current: int, total: int):
        """Log progress message."""
        if self.progress_callback:
            self.progress_callback(message, current, total)
        logger.info(f"{message} ({current}/{total})")
