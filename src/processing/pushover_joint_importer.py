"""
Pushover Joint Results Importer

Imports pushover joint displacements into the database.
Stores Ux, Uy, Uz displacements for each joint directly in JointResultsCache.
"""

import logging
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set

import pandas as pd
from sqlalchemy.orm import Session

from database.models import (
    Project,
    ResultSet,
    LoadCase,
)
from processing.pushover_joint_parser import PushoverJointParser

logger = logging.getLogger(__name__)


class PushoverJointImporter:
    """Importer for pushover joint displacements.

    Imports Ux, Uy, Uz displacement values for each joint and stores them
    directly in JointResultsCache for fast retrieval.
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
            result_set_id: ID of the result set to add joint results to
            file_path: Path to Excel file containing joint displacement results
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
        self.load_cases_cache = {}  # load_case_name → LoadCase object
        self.joint_data = {}  # (story, label, unique_name) → {direction: {load_case: value}}

    def import_all(self) -> Dict:
        """Import all pushover joint displacement results.

        Returns:
            Dict with import statistics
        """
        try:
            self._log_progress("Loading result set...", 0, 100)

            # Get existing result set
            self.result_set = self.session.query(ResultSet).get(self.result_set_id)
            if not self.result_set:
                raise ValueError(f"Result set ID {self.result_set_id} not found")

            # Import data for each direction
            stats = {
                'x_ux_displacements': 0,
                'x_uy_displacements': 0,
                'x_uz_displacements': 0,
                'y_ux_displacements': 0,
                'y_uy_displacements': 0,
                'y_uz_displacements': 0,
                'errors': []
            }

            parser = PushoverJointParser(self.file_path)

            # Import X direction
            if self.selected_load_cases_x:
                self._log_progress("Importing X direction...", 30, 100)
                x_stats = self._import_direction(parser, 'X', self.selected_load_cases_x)
                stats['x_ux_displacements'] += x_stats['ux_displacements']
                stats['x_uy_displacements'] += x_stats['uy_displacements']
                stats['x_uz_displacements'] += x_stats['uz_displacements']

            # Import Y direction
            if self.selected_load_cases_y:
                self._log_progress("Importing Y direction...", 60, 100)
                y_stats = self._import_direction(parser, 'Y', self.selected_load_cases_y)
                stats['y_ux_displacements'] += y_stats['ux_displacements']
                stats['y_uy_displacements'] += y_stats['uy_displacements']
                stats['y_uz_displacements'] += y_stats['uz_displacements']

            # Build joint results cache
            self._log_progress("Building cache...", 90, 100)
            self._build_joint_cache()

            self._log_progress("Import complete!", 100, 100)
            self.session.commit()

            return stats

        except Exception as e:
            self.session.rollback()
            logger.exception("Pushover joint import failed")
            raise

    def _import_direction(self, parser: PushoverJointParser, direction: str, selected_load_cases: Set[str]) -> Dict:
        """Import data for one direction.

        Args:
            parser: Parser for Excel file
            direction: 'X' or 'Y'
            selected_load_cases: Set of load cases to import

        Returns:
            Dict with counts of imported records
        """
        stats = {'ux_displacements': 0, 'uy_displacements': 0, 'uz_displacements': 0}

        # Parse joint results
        results = parser.parse(direction)

        # Import Ux displacements
        if results.displacements_ux is not None:
            stats['ux_displacements'] += self._import_displacements(
                results.displacements_ux, 'Ux', selected_load_cases
            )

        # Import Uy displacements
        if results.displacements_uy is not None:
            stats['uy_displacements'] += self._import_displacements(
                results.displacements_uy, 'Uy', selected_load_cases
            )

        # Import Uz displacements
        if results.displacements_uz is not None:
            stats['uz_displacements'] += self._import_displacements(
                results.displacements_uz, 'Uz', selected_load_cases
            )

        return stats

    def _import_displacements(self, df: pd.DataFrame, displacement_type: str, selected_load_cases: Set[str]) -> int:
        """Import joint displacements from DataFrame.

        Args:
            df: DataFrame with columns: Story, Label, Unique Name, [Load Cases...]
            displacement_type: 'Ux', 'Uy', or 'Uz'
            selected_load_cases: Set of load cases to import

        Returns:
            Count of imported records
        """
        count = 0

        # Get joint identification column names (first three columns)
        story_col = df.columns[0]  # 'Story'
        label_col = df.columns[1]  # 'Label'
        unique_name_col = df.columns[2]  # 'Unique Name'

        for _, row in df.iterrows():
            story_name = str(row[story_col])
            label = str(int(float(row[label_col])))  # Convert float to int to string
            unique_name = str(int(float(row[unique_name_col])))  # Convert float to int to string

            # Joint key
            joint_key = (story_name, label, unique_name)

            # Initialize joint data structure if needed
            if joint_key not in self.joint_data:
                self.joint_data[joint_key] = {}

            # Import each load case column
            for load_case_name in df.columns[3:]:  # Skip story, label, unique name columns
                if load_case_name not in selected_load_cases:
                    continue

                value = row[load_case_name]

                if pd.isna(value):
                    continue

                # Get or create load case
                load_case = self._get_or_create_load_case(load_case_name)

                # Store in joint_data structure for cache building
                # Format: joint_data[(story, label, unique_name)][displacement_type] = {load_case: value}
                if displacement_type not in self.joint_data[joint_key]:
                    self.joint_data[joint_key][displacement_type] = {}

                self.joint_data[joint_key][displacement_type][load_case_name] = float(value)
                count += 1

        return count

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

    def _build_joint_cache(self):
        """Build joint results cache for joint displacements."""
        from database.models import JointResultsCache

        # Delete existing joint cache for this result set (joint displacements only)
        self.session.query(JointResultsCache).filter(
            JointResultsCache.result_set_id == self.result_set_id,
            JointResultsCache.result_type.in_(['JointDisplacements_Ux', 'JointDisplacements_Uy', 'JointDisplacements_Uz'])
        ).delete(synchronize_session=False)

        # Build cache for each displacement type (Ux, Uy, Uz)
        self._cache_displacement_type('Ux')
        self._cache_displacement_type('Uy')
        self._cache_displacement_type('Uz')

        logger.info(f"Built joint cache for {len(self.joint_data)} joints")

    def _cache_displacement_type(self, displacement_type: str):
        """Build cache for one displacement type (Ux, Uy, or Uz).

        Args:
            displacement_type: 'Ux', 'Uy', or 'Uz'
        """
        from database.models import JointResultsCache

        result_type = f"JointDisplacements_{displacement_type}"
        count = 0

        # Create cache entry for each joint
        for (story, label, unique_name), displacement_data in self.joint_data.items():
            if displacement_type not in displacement_data:
                continue  # No data for this displacement type at this joint

            # Create joint identifier (Story-Label format for shell_object)
            shell_object = f"{story}-{label}"

            # Build results matrix
            results_matrix = displacement_data[displacement_type]

            cache_entry = JointResultsCache(
                project_id=self.project_id,
                result_set_id=self.result_set_id,
                shell_object=shell_object,
                unique_name=unique_name,
                result_type=result_type,
                results_matrix=results_matrix
            )
            self.session.add(cache_entry)
            count += 1

        logger.info(f"Created {count} cache entries for {result_type}")

    def _log_progress(self, message: str, current: int, total: int):
        """Log progress message."""
        if self.progress_callback:
            self.progress_callback(message, current, total)
        logger.info(f"{message} ({current}/{total})")
