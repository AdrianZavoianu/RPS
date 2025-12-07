"""
Pushover Beam Results Parser

Parses pushover beam hinge rotations from Excel files.
Based on the approach from Old_scripts/ETPS/ETPS_Library/ETPS_Responses.py (get_beams_hinges)
"""

import pandas as pd
from dataclasses import dataclass
from typing import Dict, List, Optional
from pathlib import Path
import logging

from utils.pushover_utils import detect_direction

logger = logging.getLogger(__name__)


@dataclass
class PushoverBeamResults:
    """Container for pushover beam results data."""
    rotations: Optional[pd.DataFrame] = None  # R3 Plastic rotations
    direction: str = ""  # 'X' or 'Y'


class PushoverBeamParser:
    """Parser for pushover beam hinge rotation Excel files.

    Extracts plastic rotation values (R3 Plastic) for each beam hinge location.

    Based on ETPS_Responses.py approach:
    - Filters to pushover direction
    - Groups by Frame/Wall, Unique Name, Output Case, Step Type
    - Extracts R3 Plastic values per hinge location
    """

    def __init__(self, file_path: Path):
        """Initialize parser with Excel file path.

        Args:
            file_path: Path to Excel file with pushover beam hinge results
        """
        self.file_path = file_path
        self.excel_data = pd.ExcelFile(file_path)

    def parse(self, direction: str) -> PushoverBeamResults:
        """Parse all beam hinge results for specified direction.

        Args:
            direction: 'X', 'Y', or 'XY'

        Returns:
            PushoverBeamResults with extracted data

        Raises:
            ValueError: If invalid direction specified
        """
        if direction.upper() not in ['X', 'Y', 'XY']:
            raise ValueError(f"Invalid direction '{direction}'. Must be 'X', 'Y', or 'XY'.")

        direction = direction.upper()

        results = PushoverBeamResults(direction=direction)

        # Extract rotations with error handling
        try:
            results.rotations = self._extract_beam_rotations(direction)
        except Exception as e:
            logger.warning(f"Failed to extract R3 Plastic rotations for {direction}: {e}")
            results.rotations = None

        return results

    def _extract_beam_rotations(self, direction: str) -> pd.DataFrame:
        """Extract beam rotations for specified direction.

        Reads "Hinge States" sheet and calculates maximum rotation per
        beam/hinge/case.

        Args:
            direction: 'X', 'Y', or 'XY'

        Returns:
            DataFrame with columns: Frame/Wall, Unique Name, [Output Cases...]
        """
        # Read Hinge States sheet
        df = pd.read_excel(self.excel_data, sheet_name='Hinge States', header=1)
        df = df.drop(0)  # Drop units row

        # Filter columns
        df = df[['Frame/Wall', 'Unique Name', 'Output Case', 'Step Type', 'R3 Plastic']]

        # Filter by pushover direction
        if direction == 'XY':
            df = df[df['Output Case'].apply(lambda x: 'X' in str(x).upper() and 'Y' in str(x).upper())]
        else:
            df = df[df['Output Case'].apply(lambda x: direction in str(x).upper())]

        # Preserve beam and hinge order from Excel
        beam_order = df['Frame/Wall'].unique().tolist()
        unique_name_order = df['Unique Name'].unique().tolist()

        # Calculate maximum rotation per beam, unique name, output case
        # Group by Frame/Wall, Unique Name, Output Case and take absolute max across step types (Max/Min)
        max_rotations = df.groupby(['Frame/Wall', 'Unique Name', 'Output Case'], sort=False)['R3 Plastic'].apply(
            lambda x: x.abs().max()  # Take absolute max (handles both Max and Min step types)
        ).unstack().reset_index()

        # Restore original order
        max_rotations['Frame/Wall'] = pd.Categorical(max_rotations['Frame/Wall'], categories=beam_order, ordered=True)
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
        # Read Hinge States sheet to detect directions
        df = pd.read_excel(self.excel_data, sheet_name='Hinge States', header=1)
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
        df = pd.read_excel(self.excel_data, sheet_name='Hinge States', header=1)
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

    def get_beams(self) -> List[str]:
        """Get list of all beams in the file.

        Returns:
            List of beam names
        """
        df = pd.read_excel(self.excel_data, sheet_name='Hinge States', header=1)
        df = df.drop(0)

        return sorted(df['Frame/Wall'].unique().tolist())
