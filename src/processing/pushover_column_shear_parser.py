"""
Pushover Column Shear Parser

Parses pushover column shear forces (V2, V3) from "Element Forces - Columns" sheet.
"""

import pandas as pd
from dataclasses import dataclass
from typing import Dict, List, Optional
from pathlib import Path
import logging

from utils.pushover_utils import detect_direction

logger = logging.getLogger(__name__)


@dataclass
class PushoverColumnShearResults:
    """Container for pushover column shear results data."""
    shears_v2: Optional[pd.DataFrame] = None  # V2 shear forces
    shears_v3: Optional[pd.DataFrame] = None  # V3 shear forces
    direction: str = ""  # 'X' or 'Y'


class PushoverColumnShearParser:
    """Parser for pushover column shear force Excel files.

    Extracts shear force values (V2, V3) for each column from "Element Forces - Columns" sheet.
    """

    def __init__(self, file_path: Path):
        """Initialize parser with Excel file path.

        Args:
            file_path: Path to Excel file with pushover column shear results
        """
        self.file_path = file_path
        self.excel_data = pd.ExcelFile(file_path)

    def parse(self, direction: str) -> PushoverColumnShearResults:
        """Parse all column shear results for specified direction.

        Args:
            direction: 'X', 'Y', or 'XY'

        Returns:
            PushoverColumnShearResults with extracted data

        Raises:
            ValueError: If invalid direction specified
        """
        if direction.upper() not in ['X', 'Y', 'XY']:
            raise ValueError(f"Invalid direction '{direction}'. Must be 'X', 'Y', or 'XY'.")

        direction = direction.upper()

        results = PushoverColumnShearResults(direction=direction)

        # Extract shears with error handling
        try:
            results.shears_v2 = self._extract_column_shears(direction, 'V2')
        except Exception as e:
            logger.warning(f"Failed to extract V2 shears for {direction}: {e}")
            results.shears_v2 = None

        try:
            results.shears_v3 = self._extract_column_shears(direction, 'V3')
        except Exception as e:
            logger.warning(f"Failed to extract V3 shears for {direction}: {e}")
            results.shears_v3 = None

        return results

    def _extract_column_shears(self, direction: str, shear_direction: str) -> pd.DataFrame:
        """Extract column shears for specified pushover and shear directions.

        Reads "Element Forces - Columns" sheet and calculates maximum shear per
        column/story/case.

        Args:
            direction: Pushover direction 'X', 'Y', or 'XY'
            shear_direction: Shear direction 'V2' or 'V3'

        Returns:
            DataFrame with columns: Column, Story, [Output Cases...]
        """
        # Read Element Forces - Columns sheet
        df = pd.read_excel(self.excel_data, sheet_name='Element Forces - Columns', header=1)
        df = df.drop(0)  # Drop units row

        # Filter columns
        required_cols = ['Story', 'Column', 'Output Case', 'Step Type', shear_direction]
        df = df[required_cols]

        # Filter by pushover direction
        if direction == 'XY':
            df = df[df['Output Case'].apply(lambda x: 'X' in str(x).upper() and 'Y' in str(x).upper())]
        else:
            df = df[df['Output Case'].apply(lambda x: direction in str(x).upper())]

        # Preserve column and story order from Excel
        column_order = df['Column'].unique().tolist()
        story_order = df['Story'].unique().tolist()

        # Calculate maximum absolute shear per column, story, output case
        # Group by Column, Story, Output Case and take absolute max across step types (Max/Min)
        max_shears = df.groupby(['Column', 'Story', 'Output Case'], sort=False)[shear_direction].apply(
            lambda x: x.abs().max()  # Take absolute max (handles both Max and Min step types)
        ).unstack(fill_value=0.0).reset_index()

        # Restore original order
        max_shears['Column'] = pd.Categorical(max_shears['Column'], categories=column_order, ordered=True)
        max_shears['Story'] = pd.Categorical(max_shears['Story'], categories=story_order, ordered=True)
        max_shears = max_shears.sort_values(['Column', 'Story']).reset_index(drop=True)

        # Remove column index name
        max_shears.columns.name = None

        return max_shears

    def get_available_directions(self) -> List[str]:
        """Detect available pushover directions from output cases.

        Returns:
            List of detected directions (e.g., ['X', 'Y', 'XY'])
        """
        # Read Element Forces - Columns sheet to detect directions
        df = pd.read_excel(self.excel_data, sheet_name='Element Forces - Columns', header=1)
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
        df = pd.read_excel(self.excel_data, sheet_name='Element Forces - Columns', header=1)
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
        df = pd.read_excel(self.excel_data, sheet_name='Element Forces - Columns', header=1)
        df = df.drop(0)

        return sorted(df['Column'].unique().tolist())
