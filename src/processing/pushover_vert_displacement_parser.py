"""
Pushover Vertical Displacement Parser

Parses pushover vertical displacement results from Excel files.
Extracts Uz (vertical) displacements for foundation joints specified in Fou sheet.
"""

import pandas as pd
from dataclasses import dataclass
from typing import Dict, List, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class PushoverVertDisplacementResults:
    """Container for pushover vertical displacement data."""
    vert_displacements: Optional[pd.DataFrame] = None  # Uz displacements
    direction: str = ""  # 'X' or 'Y'


class PushoverVertDisplacementParser:
    """Parser for pushover vertical displacement Excel files.

    Extracts vertical displacement (Uz) values for foundation joints at pushover steps.
    Uses Fou sheet to determine which joints to monitor.

    Based on NLTHA pattern:
    - Reads foundation joint list from Fou sheet
    - Filters Joint Displacements to those joints only
    - Filters to pushover direction
    - Groups by Story, Label, Unique Name, Output Case
    - Takes minimum Uz per joint/case (from Min step type)
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
        self._foundation_joints = None

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

    def parse(self, direction: str) -> PushoverVertDisplacementResults:
        """Parse vertical displacement results for specified direction.

        Args:
            direction: 'X' or 'Y'

        Returns:
            PushoverVertDisplacementResults with extracted data

        Raises:
            ValueError: If invalid direction specified
        """
        if direction.upper() not in ['X', 'Y']:
            raise ValueError(f"Invalid direction '{direction}'. Must be 'X' or 'Y'.")

        direction = direction.upper()

        cached = self._results_cache.get(direction)
        if cached is not None:
            return cached

        results = PushoverVertDisplacementResults(direction=direction)

        # Extract vertical displacements with error handling
        try:
            results.vert_displacements = self._extract_vert_displacements(direction)
        except Exception as e:
            logger.warning(f"Failed to extract vertical displacements for {direction}: {e}")
            results.vert_displacements = None

        self._results_cache[direction] = results
        return results

    def _extract_vert_displacements(self, direction: str) -> pd.DataFrame:
        """Extract vertical displacements for specified direction.

        Reads "Joint Displacements" sheet filtered to foundation joints from Fou sheet.
        Calculates minimum Uz per joint/case.

        Args:
            direction: 'X' or 'Y'

        Returns:
            DataFrame with columns: Story, Label, Unique Name, [Output Cases...]
        """
        # Get foundation joint list
        foundation_joints = self.get_foundation_joints()

        if not foundation_joints:
            logger.warning("No foundation joints found in Fou sheet")
            return pd.DataFrame()

        # Read Joint Displacements sheet
        df = self._read_sheet('Joint Displacements')

        # Filter to required columns
        required_cols = ['Story', 'Label', 'Unique Name', 'Output Case', 'Step Type', 'Uz']
        df = df[required_cols]

        # Convert Unique Name to string for filtering
        df['Unique Name'] = df['Unique Name'].astype(str).str.split('.').str[0]  # Remove decimal part

        # Filter to foundation joints only
        df = df[df['Unique Name'].isin(foundation_joints)]

        if df.empty:
            logger.warning(f"No foundation joint data found for direction {direction}")
            return pd.DataFrame()

        # Filter by pushover direction (pattern: X or Y in the Output Case name)
        import re
        pattern = f'{direction}[+-]?'  # Matches X+, X-, Y+, Y-, X, Y
        df = df[df['Output Case'].str.contains(pattern, na=False, regex=True, case=False)]

        # Numeric safety
        df['Uz'] = pd.to_numeric(df['Uz'], errors='coerce')

        # Filter to only Min step type (get minimum vertical displacement)
        df = df[df['Step Type'] == 'Min'].copy()

        # Preserve joint order from Excel
        story_order = df['Story'].unique().tolist()
        label_order = df['Label'].unique().tolist()
        unique_name_order = df['Unique Name'].unique().tolist()

        # Min Uz per (Story, Label, Unique Name, Output Case)
        min_displacements = df.groupby(
            ['Story', 'Label', 'Unique Name', 'Output Case'],
            sort=False
        )['Uz'].min().unstack().reset_index()

        # Restore original order
        min_displacements['Story'] = pd.Categorical(
            min_displacements['Story'],
            categories=story_order,
            ordered=True
        )
        min_displacements['Label'] = pd.Categorical(
            min_displacements['Label'],
            categories=label_order,
            ordered=True
        )
        min_displacements['Unique Name'] = pd.Categorical(
            min_displacements['Unique Name'],
            categories=unique_name_order,
            ordered=True
        )
        min_displacements = min_displacements.sort_values(['Story', 'Label', 'Unique Name']).reset_index(drop=True)

        # Remove column index name
        min_displacements.columns.name = None

        return min_displacements

    def get_foundation_joints(self) -> List[str]:
        """Get foundation joint list from Fou sheet.

        Returns:
            List of foundation joint unique names
        """
        if self._foundation_joints is not None:
            return self._foundation_joints

        if not self.validate_sheet_exists('Fou'):
            logger.warning("Fou sheet not found in Excel file")
            return []

        try:
            # Read Fou sheet
            df = self._read_sheet('Fou', header=0, drop_units=False)

            # Get unique names (first column)
            if 'Unique Name' in df.columns:
                joints = df['Unique Name'].dropna().astype(str).str.split('.').str[0].unique().tolist()
            else:
                # Use first column if 'Unique Name' not found
                joints = df.iloc[:, 0].dropna().astype(str).str.split('.').str[0].unique().tolist()

            self._foundation_joints = joints
            return joints

        except Exception as e:
            logger.error(f"Failed to read Fou sheet: {e}")
            return []

    def get_available_directions(self) -> List[str]:
        """Detect available pushover directions from output cases.

        Returns:
            List of detected directions (e.g., ['X', 'Y'])
        """
        # Read Joint Displacements sheet to detect directions
        df = self._read_sheet('Joint Displacements')

        if 'Output Case' not in df.columns:
            return []

        output_cases = df['Output Case'].dropna().unique()

        directions = []
        if any('X' in str(case).upper() for case in output_cases):
            directions.append('X')
        if any('Y' in str(case).upper() for case in output_cases):
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

        if 'Output Case' not in df.columns:
            return []

        # Filter by pushover direction in Output Case name
        direction = direction.upper()
        pattern = f'{direction}[+-]?'  # Matches X+, X-, Y+, Y-, X, Y
        cases = df[df['Output Case'].str.contains(pattern, na=False, regex=True, case=False)]['Output Case'].unique()

        return sorted(cases.tolist())

    def get_foundation_joints_with_data(self) -> List[str]:
        """Get list of foundation joints that have displacement data.

        Returns:
            List of unique joint identifiers (Unique Name)
        """
        foundation_joints = self.get_foundation_joints()

        if not foundation_joints:
            return []

        # Read Joint Displacements to see which foundation joints have data
        df = self._read_sheet('Joint Displacements')

        if 'Unique Name' not in df.columns:
            return []

        # Convert Unique Name to string
        df['Unique Name'] = df['Unique Name'].astype(str).str.split('.').str[0]

        # Filter to foundation joints with data
        joints_with_data = df[df['Unique Name'].isin(foundation_joints)]['Unique Name'].unique().tolist()

        return sorted(joints_with_data)

    def validate_sheet_exists(self, sheet_name: str) -> bool:
        """Check if a sheet exists in the Excel file.

        Args:
            sheet_name: Name of sheet to check

        Returns:
            True if sheet exists, False otherwise
        """
        return sheet_name in self.excel_data.sheet_names
