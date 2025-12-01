"""
Pushover Wall Results Parser

Parses pushover wall (pier) forces from Excel files.
Based on the approach from Old_scripts/ETPS/ETPS_Library/ETPS_Responses.py (get_walls_piers_forces)
"""

import pandas as pd
from dataclasses import dataclass
from typing import Dict, List, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class PushoverWallResults:
    """Container for pushover wall results data."""
    shears_v2: Optional[pd.DataFrame] = None  # V2 shear forces
    shears_v3: Optional[pd.DataFrame] = None  # V3 shear forces
    rotations: Optional[pd.DataFrame] = None  # Quad rotations
    direction: str = ""  # 'X' or 'Y'


class PushoverWallParser:
    """Parser for pushover wall (pier) forces Excel files.

    Extracts maximum and minimum force values per pier, story, and output case for:
    - V2 shear (in-plane direction 2)
    - V3 shear (in-plane direction 3)

    Based on ETPS_Responses.py approach:
    - Filters to Bottom location only
    - Groups by Pier, Story, Output Case
    - Extracts Max/Min step type values
    """

    def __init__(self, file_path: Path):
        """Initialize parser with Excel file path.

        Args:
            file_path: Path to Excel file with pushover wall results
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

    def parse(self, direction: str) -> PushoverWallResults:
        """Parse all wall results for specified direction.

        Args:
            direction: 'X', 'Y', or 'XY'

        Returns:
            PushoverWallResults with extracted data

        Raises:
            ValueError: If invalid direction specified
        """
        if direction.upper() not in ['X', 'Y', 'XY']:
            raise ValueError(f"Invalid direction '{direction}'. Must be 'X', 'Y', or 'XY'.")

        direction = direction.upper()

        results = PushoverWallResults(direction=direction)

        # Extract each force type with error handling
        try:
            results.shears_v2 = self._extract_pier_forces(direction, 'V2')
        except Exception as e:
            logger.warning(f"Failed to extract V2 shears for {direction}: {e}")
            results.shears_v2 = None

        try:
            results.shears_v3 = self._extract_pier_forces(direction, 'V3')
        except Exception as e:
            logger.warning(f"Failed to extract V3 shears for {direction}: {e}")
            results.shears_v3 = None

        # Extract rotations
        try:
            results.rotations = self._extract_quad_rotations(direction)
        except Exception as e:
            logger.warning(f"Failed to extract rotations for {direction}: {e}")
            results.rotations = None

        return results

    def _extract_pier_forces(self, direction: str, force_column: str) -> pd.DataFrame:
        """Extract pier forces for specified direction and force type.

        Reads "Pier Forces" sheet and calculates maximum force per pier/story/case.

        Args:
            direction: 'X', 'Y', or 'XY'
            force_column: Force column name ('V2' or 'V3')

        Returns:
            DataFrame with columns: Pier, Story, [Output Cases...]
        """
        # Read Pier Forces sheet
        df = pd.read_excel(self.excel_data, sheet_name='Pier Forces', header=1)
        df = df.drop(0)  # Drop units row

        # Filter columns
        df = df[['Story', 'Pier', 'Output Case', 'Step Type', 'Location', force_column]]

        # Filter by pushover direction
        if direction == 'XY':
            df = df[df['Output Case'].apply(lambda x: 'X' in str(x).upper() and 'Y' in str(x).upper())]
        else:
            df = df[df['Output Case'].apply(lambda x: direction in str(x).upper())]

        # Filter to Bottom location only (per ETPS pattern)
        df = df[df['Location'] == 'Bottom']

        # Preserve pier and story order from Excel
        pier_order = df['Pier'].unique().tolist()
        story_order = df['Story'].unique().tolist()

        # Calculate maximum force per pier, story, output case
        # Group by Pier, Story, Output Case and take max across step types (Max/Min)
        max_forces = df.groupby(['Pier', 'Story', 'Output Case'], sort=False)[force_column].apply(
            lambda x: x.abs().max()  # Take absolute max (handles both Max and Min step types)
        ).unstack().reset_index()

        # Restore original order
        max_forces['Pier'] = pd.Categorical(max_forces['Pier'], categories=pier_order, ordered=True)
        max_forces['Story'] = pd.Categorical(max_forces['Story'], categories=story_order, ordered=True)
        max_forces = max_forces.sort_values(['Pier', 'Story']).reset_index(drop=True)

        # Remove column index name
        max_forces.columns.name = None

        return max_forces

    def _extract_quad_rotations(self, direction: str) -> pd.DataFrame:
        """Extract quad rotations for specified direction.

        Reads "Quad Strain Gauge - Rotation" sheet and calculates maximum rotation
        per quad/story/case.

        Args:
            direction: 'X', 'Y', or 'XY'

        Returns:
            DataFrame with columns: Name, Story, [Output Cases...]
        """
        # Read Quad Strain Gauge - Rotation sheet
        df = pd.read_excel(self.excel_data, sheet_name='Quad Strain Gauge - Rotation', header=1)
        df = df.drop(0)  # Drop units row

        # Filter columns
        df = df[['Story', 'Name', 'Output Case', 'StepType', 'Rotation']]

        # Filter by pushover direction
        if direction == 'XY':
            df = df[df['Output Case'].apply(lambda x: 'X' in str(x).upper() and 'Y' in str(x).upper())]
        else:
            df = df[df['Output Case'].apply(lambda x: direction in str(x).upper())]

        # Preserve element and story order from Excel
        element_order = df['Name'].unique().tolist()
        story_order = df['Story'].unique().tolist()

        # Calculate maximum rotation per element, story, output case
        # Group by Name, Story, Output Case and take absolute max across step types (Max/Min)
        max_rotations = df.groupby(['Name', 'Story', 'Output Case'], sort=False)['Rotation'].apply(
            lambda x: x.abs().max()  # Take absolute max (handles both Max and Min step types)
        ).unstack().reset_index()

        # Restore original order
        max_rotations['Name'] = pd.Categorical(max_rotations['Name'], categories=element_order, ordered=True)
        max_rotations['Story'] = pd.Categorical(max_rotations['Story'], categories=story_order, ordered=True)
        max_rotations = max_rotations.sort_values(['Name', 'Story']).reset_index(drop=True)

        # Remove column index name
        max_rotations.columns.name = None

        return max_rotations

    def get_available_directions(self) -> List[str]:
        """Detect available pushover directions from output cases.

        Returns:
            List of detected directions (e.g., ['X', 'Y', 'XY'])
        """
        # Read Pier Forces sheet to detect directions
        df = pd.read_excel(self.excel_data, sheet_name='Pier Forces', header=1)
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
        df = pd.read_excel(self.excel_data, sheet_name='Pier Forces', header=1)
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

    def get_piers(self) -> List[str]:
        """Get list of all piers in the file.

        Returns:
            List of pier names
        """
        df = pd.read_excel(self.excel_data, sheet_name='Pier Forces', header=1)
        df = df.drop(0)

        return sorted(df['Pier'].unique().tolist())

    def get_quads(self) -> List[str]:
        """Get list of all quad elements in the file.

        Returns:
            List of quad element names
        """
        try:
            df = pd.read_excel(self.excel_data, sheet_name='Quad Strain Gauge - Rotation', header=1)
            df = df.drop(0)

            # Convert Name column to strings (they're stored as floats)
            return sorted([str(int(name)) for name in df['Name'].unique().tolist()])
        except Exception:
            return []
