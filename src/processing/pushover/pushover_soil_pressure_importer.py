"""
Pushover Soil Pressure Importer

Imports pushover soil pressure results into the database.
Stores minimum soil pressure values for each foundation element directly in JointResultsCache.
"""

import logging
from typing import Dict, List, Set, Any

import pandas as pd

from .pushover_joint_base import BasePushoverJointImporter
from .pushover_soil_pressure_parser import PushoverSoilPressureParser
from ..import_utils import require_sheets

logger = logging.getLogger(__name__)


class PushoverSoilPressureImporter(BasePushoverJointImporter):
    """Importer for pushover soil pressures.

    Imports minimum soil pressure values for each foundation element and stores them
    directly in JointResultsCache for fast retrieval.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.soil_pressure_data: Dict[tuple, Dict] = {}  # (shell_object, unique_name) → {load_case: value}

    def _create_parser(self) -> PushoverSoilPressureParser:
        """Create soil pressure parser."""
        return PushoverSoilPressureParser(self.file_path)

    def _get_result_types(self) -> List[str]:
        """Return result types for soil pressures."""
        return ['SoilPressures_Min']

    def _get_stats_template(self) -> Dict:
        """Return initial stats dictionary."""
        return {
            'x_soil_pressures': 0,
            'y_soil_pressures': 0,
            'errors': []
        }

    def _validate_required_sheets(self) -> bool:
        """Check if Soil Pressures sheet exists."""
        parser = self._create_parser()
        if not require_sheets(['Soil Pressures'], parser.validate_sheet_exists):
            logger.warning("Soil Pressures sheet not found, skipping")
            return False
        return True

    def _import_direction(self, parser: PushoverSoilPressureParser, direction: str, selected_load_cases: Set[str]) -> Dict:
        """Import data for one direction."""
        stats = {'soil_pressures': 0}

        results = parser.parse(direction)

        if results.soil_pressures is not None:
            stats['soil_pressures'] += self._import_soil_pressures(
                results.soil_pressures, selected_load_cases
            )

        return stats

    def _import_soil_pressures(self, df: pd.DataFrame, selected_load_cases: Set[str]) -> int:
        """Import soil pressures from DataFrame."""
        count = 0

        shell_object_col = df.columns[0]  # 'Shell Object'
        unique_name_col = df.columns[1]  # 'Unique Name'

        for _, row in df.iterrows():
            shell_object = str(row[shell_object_col])
            unique_name = str(int(float(row[unique_name_col])))

            element_key = (shell_object, unique_name)

            if element_key not in self.soil_pressure_data:
                self.soil_pressure_data[element_key] = {}

            for load_case_name in df.columns[2:]:
                if load_case_name not in selected_load_cases:
                    continue

                value = row[load_case_name]
                if pd.isna(value):
                    continue

                self._get_or_create_load_case(load_case_name)
                self.soil_pressure_data[element_key][load_case_name] = float(value)
                count += 1

        return count

    def _build_cache(self) -> None:
        """Build joint results cache for soil pressures."""
        self._delete_existing_cache(self._get_result_types())

        result_type = "SoilPressures_Min"
        count = 0

        for (shell_object, unique_name), pressure_data in self.soil_pressure_data.items():
            cache_entry = self._create_cache_entry(
                shell_object=shell_object,
                unique_name=unique_name,
                result_type=result_type,
                results_matrix=pressure_data
            )
            self.session.add(cache_entry)
            count += 1

        logger.info(f"Created {count} cache entries for {result_type}")
