"""
Pushover Joint Results Importer

Imports pushover joint displacements into the database.
Stores Ux, Uy, Uz displacements for each joint directly in JointResultsCache.
"""

import logging
from typing import Dict, List, Set, Any

import pandas as pd

from .pushover_joint_base import BasePushoverJointImporter
from .pushover_joint_parser import PushoverJointParser

logger = logging.getLogger(__name__)


class PushoverJointImporter(BasePushoverJointImporter):
    """Importer for pushover joint displacements.

    Imports Ux, Uy, Uz displacement values for each joint and stores them
    directly in JointResultsCache for fast retrieval.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.joint_data: Dict[tuple, Dict] = {}  # (story, label, unique_name) → {displacement_type: {load_case: value}}

    def _create_parser(self) -> PushoverJointParser:
        """Create joint parser."""
        return PushoverJointParser(self.file_path)

    def _get_result_types(self) -> List[str]:
        """Return result types for joint displacements."""
        return ['JointDisplacements_Ux', 'JointDisplacements_Uy', 'JointDisplacements_Uz']

    def _get_stats_template(self) -> Dict:
        """Return initial stats dictionary."""
        return {
            'x_ux_displacements': 0,
            'x_uy_displacements': 0,
            'x_uz_displacements': 0,
            'y_ux_displacements': 0,
            'y_uy_displacements': 0,
            'y_uz_displacements': 0,
            'errors': []
        }

    def _merge_stats(self, stats: Dict, direction_stats: Dict, prefix: str) -> None:
        """Merge direction stats into main stats dict."""
        for key, value in direction_stats.items():
            stats_key = f"{prefix}_{key}"
            if stats_key in stats:
                stats[stats_key] += value

    def _import_direction(self, parser: PushoverJointParser, direction: str, selected_load_cases: Set[str]) -> Dict:
        """Import data for one direction."""
        stats = {'ux_displacements': 0, 'uy_displacements': 0, 'uz_displacements': 0}

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
        """Import joint displacements from DataFrame."""
        count = 0

        story_col = df.columns[0]  # 'Story'
        label_col = df.columns[1]  # 'Label'
        unique_name_col = df.columns[2]  # 'Unique Name'

        for _, row in df.iterrows():
            story_name = str(row[story_col])
            label = str(int(float(row[label_col])))
            unique_name = str(int(float(row[unique_name_col])))

            joint_key = (story_name, label, unique_name)

            if joint_key not in self.joint_data:
                self.joint_data[joint_key] = {}

            for load_case_name in df.columns[3:]:
                if load_case_name not in selected_load_cases:
                    continue

                value = row[load_case_name]
                if pd.isna(value):
                    continue

                self._get_or_create_load_case(load_case_name)

                if displacement_type not in self.joint_data[joint_key]:
                    self.joint_data[joint_key][displacement_type] = {}

                self.joint_data[joint_key][displacement_type][load_case_name] = float(value)
                count += 1

        return count

    def _build_cache(self) -> None:
        """Build joint results cache for joint displacements."""
        self._delete_existing_cache(self._get_result_types())

        # Build cache for each displacement type (Ux, Uy, Uz)
        for displacement_type in ['Ux', 'Uy', 'Uz']:
            self._cache_displacement_type(displacement_type)

        logger.info(f"Built joint cache for {len(self.joint_data)} joints")

    def _cache_displacement_type(self, displacement_type: str) -> None:
        """Build cache for one displacement type (Ux, Uy, or Uz)."""
        result_type = f"JointDisplacements_{displacement_type}"
        count = 0

        for (story, label, unique_name), displacement_data in self.joint_data.items():
            if displacement_type not in displacement_data:
                continue

            # Create joint identifier (Story-Label format for shell_object)
            shell_object = f"{story}-{label}"

            cache_entry = self._create_cache_entry(
                shell_object=shell_object,
                unique_name=unique_name,
                result_type=result_type,
                results_matrix=displacement_data[displacement_type]
            )
            self.session.add(cache_entry)
            count += 1

        logger.info(f"Created {count} cache entries for {result_type}")
