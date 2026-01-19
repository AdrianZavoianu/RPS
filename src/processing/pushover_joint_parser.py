"""
Pushover Joint Results Parser

Parses pushover joint displacements from Excel files.
Extracts Ux, Uy, Uz displacements for joints at each pushover step.
"""

import pandas as pd
from dataclasses import dataclass
from typing import Dict, List, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class PushoverJointResults:
    """Container for pushover joint displacement data."""
    displacements_ux: Optional[pd.DataFrame] = None  # Ux displacements
    displacements_uy: Optional[pd.DataFrame] = None  # Uy displacements
    displacements_uz: Optional[pd.DataFrame] = None  # Uz displacements
    direction: str = ""  # 'X' or 'Y'


class PushoverJointParser:
    """Parser for pushover joint displacement Excel files.

    Extracts displacement values (Ux, Uy, Uz) for each joint at pushover steps.

    Based on NLTHA pattern:
    - Filters to pushover direction
    - Groups by Story, Label, Unique Name, Output Case, Step Type
    - Takes absolute max across Max/Min step types per joint/case
    """

    def __init__(self, file_path: Path):
        """Initialize parser with Excel file path.

        Args:
            file_path: Path to Excel file with pushover joint displacement results
        """
        self.file_path = file_path
        self.excel_data = pd.ExcelFile(file_path)
        self._sheet_cache = {}
        self._results_cache = {}

    def _read_sheet(self, sheet_name: str, header: int = 1, drop_units: bool = True) -> pd.DataFrame:
        """Read and cache a sheet from the Excel file."""
        cache_key = (sheet_name, header, drop_units)
        if cache_key in self._sheet_cache:
            return self._sheet_cache[cache_key].copy()

        df = pd.read_excel(self.excel_data, sheet_name=sheet_name, header=header)
        if drop_units and len(df) > 0:
            df = df.drop(0)

        self._sheet_cache[cache_key] = df
        return df.copy()

    def parse(self, direction: str) -> PushoverJointResults:
        """Parse all joint displacement results for specified direction.

        Args:
            direction: 'X' or 'Y'

        Returns:
            PushoverJointResults with extracted data

        Raises:
            ValueError: If invalid direction specified
        """
        if direction.upper() not in ['X', 'Y']:
            raise ValueError(f"Invalid direction '{direction}'. Must be 'X' or 'Y'.")

        direction = direction.upper()

        cached = self._results_cache.get(direction)
        if cached is not None:
            return cached

        results = PushoverJointResults(direction=direction)

        # Extract displacements with error handling
        try:
            results.displacements_ux = self._extract_joint_displacements(direction, 'Ux')
        except Exception as e:
            logger.warning(f"Failed to extract Ux displacements for {direction}: {e}")
            results.displacements_ux = None

        try:
            results.displacements_uy = self._extract_joint_displacements(direction, 'Uy')
        except Exception as e:
            logger.warning(f"Failed to extract Uy displacements for {direction}: {e}")
            results.displacements_uy = None

        try:
            results.displacements_uz = self._extract_joint_displacements(direction, 'Uz')
        except Exception as e:
            logger.warning(f"Failed to extract Uz displacements for {direction}: {e}")
            results.displacements_uz = None

        self._results_cache[direction] = results
        return results

    def _extract_joint_displacements(self, direction: str, displacement_column: str) -> pd.DataFrame:
        """Extract joint displacements for specified direction and displacement type.

        Reads "Joint Displacements" sheet and calculates maximum displacement per
        joint/case.

        Args:
            direction: 'X' or 'Y'
            displacement_column: 'Ux', 'Uy', or 'Uz'

        Returns:
            DataFrame with columns: Story, Label, Unique Name, [Output Cases...]
        """
        # Read Joint Displacements sheet
        df = self._read_sheet('Joint Displacements')

        # Filter columns
        df = df[['Story', 'Label', 'Unique Name', 'Output Case', 'Step Type', displacement_column]]

        # Filter by pushover direction (pattern: _X+ or _Y+ in the Output Case name)
        import re
        pattern = f'[_/]{direction}[+-]'  # Matches _X+, _X-, _Y+, _Y- etc.
        df = df[df['Output Case'].str.contains(pattern, na=False, regex=True)]

        # Preserve joint order from Excel
        story_order = df['Story'].unique().tolist()
        label_order = df['Label'].unique().tolist()
        unique_name_order = df['Unique Name'].unique().tolist()

        # Calculate maximum displacement per joint, output case
        # Group by Story, Label, Unique Name, Output Case and take absolute max across step types (Max/Min)
        max_displacements = df.groupby(
            ['Story', 'Label', 'Unique Name', 'Output Case'],
            sort=False
        )[displacement_column].apply(
            lambda x: x.abs().max()  # Take absolute max (handles both Max and Min step types)
        ).unstack().reset_index()

        # Restore original order
        max_displacements['Story'] = pd.Categorical(max_displacements['Story'], categories=story_order, ordered=True)
        max_displacements['Label'] = pd.Categorical(max_displacements['Label'], categories=label_order, ordered=True)
        max_displacements['Unique Name'] = pd.Categorical(max_displacements['Unique Name'], categories=unique_name_order, ordered=True)
        max_displacements = max_displacements.sort_values(['Story', 'Label', 'Unique Name']).reset_index(drop=True)

        # Remove column index name
        max_displacements.columns.name = None

        return max_displacements

    def get_available_directions(self) -> List[str]:
        """Detect available pushover directions from output cases.

        Returns:
            List of detected directions (e.g., ['X', 'Y'])
        """
        # Read Joint Displacements sheet to detect directions
        df = self._read_sheet('Joint Displacements')

        output_cases = df['Output Case'].dropna().unique()

        directions = []
        if any('X' in str(case) for case in output_cases):
            directions.append('X')
        if any('Y' in str(case) for case in output_cases):
            directions.append('Y')

        return directions

    def get_output_cases(self, direction: str) -> List[str]:
        """Get list of output cases for a direction.

        Args:
            direction: 'X' or 'Y'

        Returns:
            List of output case names
        """
        df = self._read_sheet('Joint Displacements')

        # Filter by pushover direction in Output Case name
        direction = direction.upper()

        import re
        pattern = f'[_/]{direction}[+-]'  # Matches _X+, _X-, _Y+, _Y- etc.
        cases = df[df['Output Case'].str.contains(pattern, na=False, regex=True)]['Output Case'].unique()

        return sorted(cases.tolist())

    def get_joints(self) -> List[str]:
        """Get list of all unique joints in the file.

        Returns:
            List of unique joint identifiers (Story-Label-UniqueName)
        """
        df = self._read_sheet('Joint Displacements')

        # Create unique joint identifiers
        joints = df.apply(
            lambda row: f"{row['Story']}-{row['Label']}-{int(float(row['Unique Name']))}",
            axis=1
        ).unique().tolist()

        return sorted(joints)
