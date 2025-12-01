"""
Pushover Column Results Parser

Parses pushover column hinge rotations from Excel files.
Based on the approach from Old_scripts/ETPS/ETPS_Library/ETPS_Responses.py (get_columns_hinges)
"""

import pandas as pd
from dataclasses import dataclass
from typing import Dict, List, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class PushoverColumnResults:
    """Container for pushover column results data."""
    rotations_r2: Optional[pd.DataFrame] = None  # R2 rotations
    rotations_r3: Optional[pd.DataFrame] = None  # R3 rotations
    direction: str = ""  # 'X' or 'Y'


class PushoverColumnParser:
    """Parser for pushover column hinge rotation Excel files.

    Extracts rotation values (R2 and R3) for each column hinge location.

    Based on ETPS_Responses.py approach:
    - Filters to pushover direction
    - Groups by Frame/Wall, Unique Name, Output Case, Step Type
    - Extracts Max/Min values per hinge location
    """

    def __init__(self, file_path: Path):
        """Initialize parser with Excel file path.

        Args:
            file_path: Path to Excel file with pushover column hinge results
        """
        self.file_path = file_path
        self.excel_data = pd.ExcelFile(file_path)

    @staticmethod
    def _detect_direction(case_name: str) -> str:
        """
        Detect pushover direction from load case name.

        Rule: Any case name containing 'X' or 'Y' is recognized
        - X direction: Contains 'X' (case-insensitive)
        - Y direction: Contains 'Y' (case-insensitive)
        - XY bi-directional: Contains both 'X' and 'Y'

        Examples:
        - "Push Modal X" -> 'X'
        - "Push Uniform Y" -> 'Y'
        - "Push_Mod_X+Ecc+" -> 'X'
        - "Push_XY+" -> 'XY'

        Args:
            case_name: Load case name

        Returns:
            Direction string: 'X', 'Y', or 'XY'
        """
        case_upper = str(case_name).upper()

        has_x = 'X' in case_upper
        has_y = 'Y' in case_upper

        # Check for bi-directional first (both X and Y present)
        if has_x and has_y:
            return 'XY'

        # Check for X direction
        if has_x:
            return 'X'

        # Check for Y direction
        if has_y:
            return 'Y'

        return 'Unknown'

    def parse(self, direction: str) -> PushoverColumnResults:
        """Parse all column hinge results for specified direction.

        Args:
            direction: 'X', 'Y', or 'XY'

        Returns:
            PushoverColumnResults with extracted data

        Raises:
            ValueError: If invalid direction specified
        """
        if direction.upper() not in ['X', 'Y', 'XY']:
            raise ValueError(f"Invalid direction '{direction}'. Must be 'X', 'Y', or 'XY'.")

        direction = direction.upper()

        results = PushoverColumnResults(direction=direction)

        # Extract each rotation type with error handling
        try:
            results.rotations_r2 = self._extract_column_rotations(direction, 'R2')
        except Exception as e:
            logger.warning(f"Failed to extract R2 rotations for {direction}: {e}")
            results.rotations_r2 = None

        try:
            results.rotations_r3 = self._extract_column_rotations(direction, 'R3')
        except Exception as e:
            logger.warning(f"Failed to extract R3 rotations for {direction}: {e}")
            results.rotations_r3 = None

        return results

    def _extract_column_rotations(self, direction: str, rotation_column: str) -> pd.DataFrame:
        """Extract column rotations for specified direction and rotation type.

        Reads "Fiber Hinge States" sheet and calculates maximum rotation per
        column/hinge/case.

        Args:
            direction: 'X', 'Y', or 'XY'
            rotation_column: Rotation column name ('R2' or 'R3')

        Returns:
            DataFrame with columns: Frame/Wall, Unique Name, [Output Cases...]
        """
        # Read Fiber Hinge States sheet
        df = pd.read_excel(self.excel_data, sheet_name='Fiber Hinge States', header=1)
        df = df.drop(0)  # Drop units row

        # Filter columns
        df = df[['Frame/Wall', 'Unique Name', 'Output Case', 'Step Type', rotation_column]]

        # Filter by pushover direction
        if direction == 'XY':
            df = df[df['Output Case'].apply(lambda x: 'X' in str(x).upper() and 'Y' in str(x).upper())]
        else:
            df = df[df['Output Case'].apply(lambda x: direction in str(x).upper())]

        # Preserve column and hinge order from Excel
        column_order = df['Frame/Wall'].unique().tolist()
        unique_name_order = df['Unique Name'].unique().tolist()

        # Calculate maximum rotation per column, unique name, output case
        # Group by Frame/Wall, Unique Name, Output Case and take absolute max across step types (Max/Min)
        max_rotations = df.groupby(['Frame/Wall', 'Unique Name', 'Output Case'], sort=False)[rotation_column].apply(
            lambda x: x.abs().max()  # Take absolute max (handles both Max and Min step types)
        ).unstack().reset_index()

        # Restore original order
        max_rotations['Frame/Wall'] = pd.Categorical(max_rotations['Frame/Wall'], categories=column_order, ordered=True)
        max_rotations['Unique Name'] = pd.Categorical(max_rotations['Unique Name'], categories=unique_name_order, ordered=True)
        max_rotations = max_rotations.sort_values(['Frame/Wall', 'Unique Name']).reset_index(drop=True)

        # Remove column index name
        max_rotations.columns.name = None

        return max_rotations

    def get_available_directions(self) -> List[str]:
        """Detect available pushover directions from output cases.

        Returns:
            List of detected directions (e.g., ['X', 'Y', 'XY'])
        """
        # Read Fiber Hinge States sheet to detect directions
        df = pd.read_excel(self.excel_data, sheet_name='Fiber Hinge States', header=1)
        df = df.drop(0)

        output_cases = df['Output Case'].unique()

        directions = []

        # Check for bi-directional first (both X and Y in name)
        if any('X' in str(case).upper() and 'Y' in str(case).upper() for case in output_cases):
            directions.append('XY')

        # Check for uni-directional
        if any('X' in str(case).upper() for case in output_cases):
            directions.append('X')
        if any('Y' in str(case).upper() for case in output_cases):
            directions.append('Y')

        return directions

    def get_output_cases(self, direction: str) -> List[str]:
        """Get list of output cases for a direction.

        Args:
            direction: 'X', 'Y', or 'XY'

        Returns:
            List of output case names
        """
        df = pd.read_excel(self.excel_data, sheet_name='Fiber Hinge States', header=1)
        df = df.drop(0)

        direction = direction.upper()

        # Filter based on direction
        if direction == 'XY':
            # Both X and Y in name
            cases = df[df['Output Case'].apply(lambda x: 'X' in str(x).upper() and 'Y' in str(x).upper())]['Output Case'].unique()
        else:
            # X or Y in name
            cases = df[df['Output Case'].apply(lambda x: direction in str(x).upper())]['Output Case'].unique()

        return sorted(cases.tolist())

    def get_columns(self) -> List[str]:
        """Get list of all columns in the file.

        Returns:
            List of column names
        """
        df = pd.read_excel(self.excel_data, sheet_name='Fiber Hinge States', header=1)
        df = df.drop(0)

        return sorted(df['Frame/Wall'].unique().tolist())
