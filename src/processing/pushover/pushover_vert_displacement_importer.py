"""
Pushover Vertical Displacement Importer

Imports pushover vertical displacement results into the database.
Stores minimum Uz (vertical) displacements for foundation joints directly in JointResultsCache.
"""

import logging
from typing import Dict, List, Set, Any

import pandas as pd

from .pushover_joint_base import BasePushoverJointImporter
from .pushover_vert_displacement_parser import PushoverVertDisplacementParser
from ..import_utils import require_sheets

logger = logging.getLogger(__name__)


class PushoverVertDisplacementImporter(BasePushoverJointImporter):
    """Importer for pushover vertical displacements.

    Imports minimum vertical displacement (Uz) values for foundation joints and stores them
    directly in JointResultsCache for fast retrieval.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.vert_displacement_data: Dict[tuple, Dict] = {}  # (story, label, unique_name) → {load_case: value}

    def _create_parser(self) -> PushoverVertDisplacementParser:
        """Create vertical displacement parser."""
        return PushoverVertDisplacementParser(self.file_path)

    def _get_result_types(self) -> List[str]:
        """Return result types for vertical displacements."""
        return ['VerticalDisplacements_Min']

    def _get_stats_template(self) -> Dict:
        """Return initial stats dictionary."""
        return {
            'x_vert_displacements': 0,
            'y_vert_displacements': 0,
            'errors': []
        }

    def _validate_required_sheets(self) -> bool:
        """Check if required sheets exist."""
        parser = self._create_parser()

        if not require_sheets(['Joint Displacements'], parser.validate_sheet_exists):
            logger.warning("Joint Displacements sheet not found, skipping")
            return False

        if not require_sheets(['Fou'], parser.validate_sheet_exists):
            logger.warning("Fou sheet not found, skipping")
            return False

        return True

    def _import_direction(self, parser: PushoverVertDisplacementParser, direction: str, selected_load_cases: Set[str]) -> Dict:
        """Import data for one direction."""
        stats = {'vert_displacements': 0}

        results = parser.parse(direction)

        if results.vert_displacements is not None:
            stats['vert_displacements'] += self._import_vert_displacements(
                results.vert_displacements, selected_load_cases
            )

        return stats

    def _import_vert_displacements(self, df: pd.DataFrame, selected_load_cases: Set[str]) -> int:
        """Import vertical displacements from DataFrame."""
        count = 0

        story_col = df.columns[0]  # 'Story'
        label_col = df.columns[1]  # 'Label'
        unique_name_col = df.columns[2]  # 'Unique Name'

        for _, row in df.iterrows():
            story_name = str(row[story_col])
            label = str(int(float(row[label_col])))
            unique_name = str(int(float(row[unique_name_col])))

            joint_key = (story_name, label, unique_name)

            if joint_key not in self.vert_displacement_data:
                self.vert_displacement_data[joint_key] = {}

            for load_case_name in df.columns[3:]:
                if load_case_name not in selected_load_cases:
                    continue

                value = row[load_case_name]
                if pd.isna(value):
                    continue

                self._get_or_create_load_case(load_case_name)
                self.vert_displacement_data[joint_key][load_case_name] = float(value)
                count += 1

        return count

    def _build_cache(self) -> None:
        """Build joint results cache for vertical displacements."""
        self._delete_existing_cache(self._get_result_types())

        result_type = "VerticalDisplacements_Min"
        count = 0

        for (story, label, unique_name), displacement_data in self.vert_displacement_data.items():
            # Create joint identifier (Story-Label format for shell_object)
            shell_object = f"{story}-{label}"

            cache_entry = self._create_cache_entry(
                shell_object=shell_object,
                unique_name=unique_name,
                result_type=result_type,
                results_matrix=displacement_data
            )
            self.session.add(cache_entry)
            count += 1

        logger.info(f"Created {count} cache entries for {result_type}")
