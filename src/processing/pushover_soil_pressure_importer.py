"""
Pushover Soil Pressure Importer

Imports pushover soil pressure results into the database.
Stores minimum soil pressure values for each foundation element directly in JointResultsCache.
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
from processing.pushover_soil_pressure_parser import PushoverSoilPressureParser
from .import_utils import require_sheets

logger = logging.getLogger(__name__)


class PushoverSoilPressureImporter:
    """Importer for pushover soil pressures.

    Imports minimum soil pressure values for each foundation element and stores them
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
            result_set_id: ID of the result set to add soil pressure results to
            file_path: Path to Excel file containing soil pressure results
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
        self.soil_pressure_data = {}  # (shell_object, unique_name) → {load_case: value}

    def import_all(self) -> Dict:
        """Import all pushover soil pressure results.

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
                'x_soil_pressures': 0,
                'y_soil_pressures': 0,
                'errors': []
            }

            parser = PushoverSoilPressureParser(self.file_path)

            # Check if Soil Pressures sheet exists
            if not require_sheets(['Soil Pressures'], parser.validate_sheet_exists):
                logger.warning("Soil Pressures sheet not found, skipping")
                return stats

            # Import X direction
            if self.selected_load_cases_x:
                self._log_progress("Importing X direction...", 30, 100)
                x_count = self._import_direction(parser, 'X', self.selected_load_cases_x)
                stats['x_soil_pressures'] += x_count

            # Import Y direction
            if self.selected_load_cases_y:
                self._log_progress("Importing Y direction...", 60, 100)
                y_count = self._import_direction(parser, 'Y', self.selected_load_cases_y)
                stats['y_soil_pressures'] += y_count

            # Build joint results cache
            self._log_progress("Building cache...", 90, 100)
            self._build_soil_pressure_cache()

            self._log_progress("Import complete!", 100, 100)
            self.session.commit()

            return stats

        except Exception as e:
            self.session.rollback()
            logger.exception("Pushover soil pressure import failed")
            raise

    def _import_direction(self, parser: PushoverSoilPressureParser, direction: str, selected_load_cases: Set[str]) -> int:
        """Import data for one direction.

        Args:
            parser: Parser for Excel file
            direction: 'X' or 'Y'
            selected_load_cases: Set of load cases to import

        Returns:
            Count of imported records
        """
        count = 0

        # Parse soil pressure results
        results = parser.parse(direction)

        if results.soil_pressures is not None:
            count += self._import_soil_pressures(results.soil_pressures, selected_load_cases)

        return count

    def _import_soil_pressures(self, df: pd.DataFrame, selected_load_cases: Set[str]) -> int:
        """Import soil pressures from DataFrame.

        Args:
            df: DataFrame with columns: Shell Object, Unique Name, [Load Cases...]
            selected_load_cases: Set of load cases to import

        Returns:
            Count of imported records
        """
        count = 0

        # Get identification column names (first two columns)
        shell_object_col = df.columns[0]  # 'Shell Object'
        unique_name_col = df.columns[1]  # 'Unique Name'

        for _, row in df.iterrows():
            shell_object = str(row[shell_object_col])
            unique_name = str(int(float(row[unique_name_col])))  # Convert float to int to string

            # Element key
            element_key = (shell_object, unique_name)

            # Initialize element data structure if needed
            if element_key not in self.soil_pressure_data:
                self.soil_pressure_data[element_key] = {}

            # Import each load case column
            for load_case_name in df.columns[2:]:  # Skip shell object and unique name columns
                if load_case_name not in selected_load_cases:
                    continue

                value = row[load_case_name]

                if pd.isna(value):
                    continue

                # Get or create load case
                load_case = self._get_or_create_load_case(load_case_name)

                # Store in soil_pressure_data structure for cache building
                self.soil_pressure_data[element_key][load_case_name] = float(value)
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

    def _build_soil_pressure_cache(self):
        """Build joint results cache for soil pressures."""
        from database.models import JointResultsCache

        # Delete existing soil pressure cache for this result set
        self.session.query(JointResultsCache).filter(
            JointResultsCache.result_set_id == self.result_set_id,
            JointResultsCache.result_type == 'SoilPressures_Min'
        ).delete(synchronize_session=False)

        result_type = "SoilPressures_Min"
        count = 0

        # Create cache entry for each foundation element
        for (shell_object, unique_name), pressure_data in self.soil_pressure_data.items():
            # Build results matrix
            results_matrix = pressure_data

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
