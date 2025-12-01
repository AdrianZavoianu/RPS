"""
Pushover Soil Pressure Parser

Parses pushover soil pressure results from Excel files.
Extracts minimum soil pressure per foundation element for each pushover step.
"""

import pandas as pd
from dataclasses import dataclass
from typing import Dict, List, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class PushoverSoilPressureResults:
    """Container for pushover soil pressure data."""
    soil_pressures: Optional[pd.DataFrame] = None  # Min soil pressures per element
    direction: str = ""  # 'X' or 'Y'


class PushoverSoilPressureParser:
    """Parser for pushover soil pressure Excel files.

    Extracts minimum soil pressure values for each foundation element at pushover steps.

    Based on NLTHA pattern:
    - Filters to pushover direction
    - Groups by Shell Object, Unique Name, Output Case
    - Takes minimum soil pressure per element/case (from Min step type)
    """

    def __init__(self, file_path: Path):
        """Initialize parser with Excel file path.

        Args:
            file_path: Path to Excel file with pushover soil pressure results
        """
        self.file_path = file_path
        self.excel_data = pd.ExcelFile(file_path)

    def parse(self, direction: str) -> PushoverSoilPressureResults:
        """Parse soil pressure results for specified direction.

        Args:
            direction: 'X' or 'Y'

        Returns:
            PushoverSoilPressureResults with extracted data

        Raises:
            ValueError: If invalid direction specified
        """
        if direction.upper() not in ['X', 'Y']:
            raise ValueError(f"Invalid direction '{direction}'. Must be 'X' or 'Y'.")

        direction = direction.upper()

        results = PushoverSoilPressureResults(direction=direction)

        # Extract soil pressures with error handling
        try:
            results.soil_pressures = self._extract_soil_pressures(direction)
        except Exception as e:
            logger.warning(f"Failed to extract soil pressures for {direction}: {e}")
            results.soil_pressures = None

        return results

    def _extract_soil_pressures(self, direction: str) -> pd.DataFrame:
        """Extract soil pressures for specified direction.

        Reads "Soil Pressures" sheet and calculates minimum pressure per element/case.

        Args:
            direction: 'X' or 'Y'

        Returns:
            DataFrame with columns: Shell Object, Unique Name, [Output Cases...]
        """
        # Read Soil Pressures sheet
        df = pd.read_excel(self.excel_data, sheet_name='Soil Pressures', header=1)
        df = df.drop(0)  # Drop units row

        # Ensure expected columns
        expected_cols = ['Story', 'Shell Object', 'Unique Name', 'Shell Element', 'Joint',
                        'Output Case', 'Case Type', 'Step Type', 'Soil Pressure',
                        'Global X', 'Global Y', 'Global Z']

        if not all(col in df.columns for col in expected_cols):
            raise ValueError(f"Soil Pressures sheet missing expected columns")

        # Filter to relevant columns
        df = df[expected_cols]

        # Filter by pushover direction (pattern: _X+ or _Y+ in the Output Case name)
        import re
        pattern = f'{direction}[+-]?'  # Matches X+, X-, Y+, Y-, X, Y (no underscore for pushover)
        df = df[df['Output Case'].str.contains(pattern, na=False, regex=True, case=False)]

        # Numeric safety
        df['Soil Pressure'] = pd.to_numeric(df['Soil Pressure'], errors='coerce')

        # Filter to only Min step type (discard Max entries)
        df = df[df['Step Type'] == 'Min'].copy()

        # Preserve element order from Excel
        shell_object_order = df['Shell Object'].unique().tolist()
        unique_name_order = df['Unique Name'].unique().tolist()

        # Min soil pressure per (Shell Object, Unique Name, Output Case)
        min_pressures = df.groupby(
            ['Shell Object', 'Unique Name', 'Output Case'],
            sort=False
        )['Soil Pressure'].min().unstack().reset_index()

        # Restore original order
        min_pressures['Shell Object'] = pd.Categorical(
            min_pressures['Shell Object'],
            categories=shell_object_order,
            ordered=True
        )
        min_pressures['Unique Name'] = pd.Categorical(
            min_pressures['Unique Name'],
            categories=unique_name_order,
            ordered=True
        )
        min_pressures = min_pressures.sort_values(['Shell Object', 'Unique Name']).reset_index(drop=True)

        # Remove column index name
        min_pressures.columns.name = None

        return min_pressures

    def get_available_directions(self) -> List[str]:
        """Detect available pushover directions from output cases.

        Returns:
            List of detected directions (e.g., ['X', 'Y'])
        """
        # Read Soil Pressures sheet to detect directions
        df = pd.read_excel(self.excel_data, sheet_name='Soil Pressures', header=1)
        df = df.drop(0)

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
        df = pd.read_excel(self.excel_data, sheet_name='Soil Pressures', header=1)
        df = df.drop(0)

        if 'Output Case' not in df.columns:
            return []

        # Filter by pushover direction in Output Case name
        direction = direction.upper()
        pattern = f'{direction}[+-]?'  # Matches X+, X-, Y+, Y-, X, Y
        cases = df[df['Output Case'].str.contains(pattern, na=False, regex=True, case=False)]['Output Case'].unique()

        return sorted(cases.tolist())

    def get_foundation_elements(self) -> List[str]:
        """Get list of all foundation elements in the file.

        Returns:
            List of unique foundation element identifiers (Unique Name)
        """
        df = pd.read_excel(self.excel_data, sheet_name='Soil Pressures', header=1)
        df = df.drop(0)

        if 'Unique Name' not in df.columns:
            return []

        # Get unique foundation elements
        elements = df['Unique Name'].dropna().astype(str).unique().tolist()

        return sorted(elements)

    def validate_sheet_exists(self, sheet_name: str) -> bool:
        """Check if a sheet exists in the Excel file.

        Args:
            sheet_name: Name of sheet to check

        Returns:
            True if sheet exists, False otherwise
        """
        return sheet_name in self.excel_data.sheet_names
