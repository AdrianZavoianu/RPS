"""
Pushover Global Results Parser

Parses pushover global results from Excel files (Story Drifts, Displacements, Forces).
Based on the approach from Old_scripts/ETPS/ETPS_Library/ETPS_Responses.py
"""

import pandas as pd
from dataclasses import dataclass
from typing import Dict, List, Optional
from pathlib import Path


@dataclass
class PushoverGlobalResults:
    """Container for pushover global results data."""
    drifts: Optional[pd.DataFrame] = None
    displacements: Optional[pd.DataFrame] = None
    forces: Optional[pd.DataFrame] = None
    direction: str = ""  # 'X' or 'Y'


class PushoverGlobalParser:
    """Parser for pushover global results Excel files.

    Extracts maximum values per story and output case for:
    - Story Drifts (max drift per story/case)
    - Story Displacements (max absolute displacement per story/case)
    - Story Forces (max absolute shear per story/case)

    Based on ETPS_Responses.py approach.
    """

    def __init__(self, file_path: Path):
        """Initialize parser with Excel file path.

        Args:
            file_path: Path to Excel file with pushover global results
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

    def parse(self, direction: str) -> PushoverGlobalResults:
        """Parse all global results for specified direction.

        Args:
            direction: 'X', 'Y', or 'XY'

        Returns:
            PushoverGlobalResults with extracted data

        Raises:
            ValueError: If invalid direction specified
        """
        if direction.upper() not in ['X', 'Y', 'XY']:
            raise ValueError(f"Invalid direction '{direction}'. Must be 'X', 'Y', or 'XY'.")

        direction = direction.upper()

        results = PushoverGlobalResults(direction=direction)

        # Extract each result type with error handling
        try:
            results.drifts = self._extract_drifts(direction)
        except Exception as e:
            import logging
            logging.warning(f"Failed to extract drifts for {direction}: {e}")
            results.drifts = None

        try:
            results.displacements = self._extract_displacements(direction)
        except Exception as e:
            import logging
            logging.warning(f"Failed to extract displacements for {direction}: {e}")
            results.displacements = None

        try:
            results.forces = self._extract_forces(direction)
        except Exception as e:
            import logging
            logging.warning(f"Failed to extract forces for {direction}: {e}")
            results.forces = None

        return results

    def _extract_drifts(self, direction: str) -> pd.DataFrame:
        """Extract story drifts for specified direction.

        Reads "Story Drifts" sheet and calculates maximum drift per story/case.

        Args:
            direction: 'X', 'Y', or 'XY'

        Returns:
            DataFrame with columns: Story, [Output Cases...]
        """
        # Read Story Drifts sheet
        df = pd.read_excel(self.excel_data, sheet_name='Story Drifts', header=1)
        df = df.drop(0)  # Drop units row

        # Filter columns
        df = df[['Story', 'Output Case', 'Step Type', 'Direction', 'Drift']]

        # Filter by pushover direction (not drift component direction!)
        # Keep only cases where the pushover is in the specified direction
        if direction == 'XY':
            # Bi-directional: match cases with both X and Y in name
            df = df[df['Output Case'].apply(lambda x: 'X' in str(x).upper() and 'Y' in str(x).upper())]

            # For XY, we need both X and Y components to compute resultant
            # Get X drifts
            df_x = df[df['Direction'] == 'X'].copy()
            df_x = df_x.rename(columns={'Drift': 'Drift_X'})

            # Get Y drifts
            df_y = df[df['Direction'] == 'Y'].copy()
            df_y = df_y.rename(columns={'Drift': 'Drift_Y'})

            # Merge X and Y drifts
            df_merged = pd.merge(
                df_x[['Story', 'Output Case', 'Step Type', 'Drift_X']],
                df_y[['Story', 'Output Case', 'Step Type', 'Drift_Y']],
                on=['Story', 'Output Case', 'Step Type'],
                how='inner'
            )

            # Compute resultant drift: sqrt(Drift_X^2 + Drift_Y^2)
            df_merged['Drift'] = ((df_merged['Drift_X']**2 + df_merged['Drift_Y']**2)**0.5)

            df = df_merged[['Story', 'Output Case', 'Step Type', 'Drift']]
        else:
            # Uni-directional: X or Y
            # Match cases with direction letter in name
            df = df[df['Output Case'].apply(lambda x: direction in str(x).upper())]

            # Filter to only the primary drift component (Direction matches pushover direction)
            # For X pushover, use X drift; for Y pushover, use Y drift
            df = df[df['Direction'] == direction]

        # Preserve story order from Excel (first occurrence order)
        story_order = df['Story'].unique().tolist()

        # Calculate maximum drift per story and output case
        max_drifts = df.groupby(['Story', 'Output Case'], sort=False)['Drift'].apply(
            lambda x: x.max()
        ).unstack().reset_index()

        # Restore original story order (groupby may have changed it)
        max_drifts['Story'] = pd.Categorical(max_drifts['Story'], categories=story_order, ordered=True)
        max_drifts = max_drifts.sort_values('Story').reset_index(drop=True)

        # Remove column index name
        max_drifts.columns.name = None

        return max_drifts

    def _extract_displacements(self, direction: str) -> pd.DataFrame:
        """Extract story displacements for specified direction.

        Reads "Joint Displacements" sheet and calculates maximum absolute
        displacement per story/case.

        Args:
            direction: 'X', 'Y', or 'XY'

        Returns:
            DataFrame with columns: Story, [Output Cases...]
        """
        # Read Joint Displacements sheet
        df = pd.read_excel(self.excel_data, sheet_name='Joint Displacements', header=1)
        df = df.drop(0)  # Drop units row

        # Handle based on direction
        if direction == 'XY':
            # Bi-directional: compute resultant from Ux and Uy
            df = df[df['Output Case'].apply(lambda x: 'X' in str(x).upper() and 'Y' in str(x).upper())]

            # Filter columns
            df = df[['Story', 'Output Case', 'Step Type', 'Ux', 'Uy']]

            # Compute resultant displacement
            df['Disp'] = ((df['Ux']**2 + df['Uy']**2)**0.5)
            col_disp = 'Disp'
        else:
            # Uni-directional: X or Y
            col_disp = 'Ux' if direction == 'X' else 'Uy'

            # Filter columns
            df = df[['Story', 'Output Case', 'Step Type', col_disp]]

            # Filter by pushover direction
            df = df[df['Output Case'].apply(lambda x: direction in str(x).upper())]

        # Preserve story order from Excel (first occurrence order)
        story_order = df['Story'].unique().tolist()

        # Calculate maximum absolute displacement per story and output case
        max_abs_disp = df.groupby(['Story', 'Output Case'], sort=False)[col_disp].apply(
            lambda x: x.abs().max()
        ).unstack().reset_index()

        # Restore original story order
        max_abs_disp['Story'] = pd.Categorical(max_abs_disp['Story'], categories=story_order, ordered=True)
        max_abs_disp = max_abs_disp.sort_values('Story').reset_index(drop=True)

        # Remove column index name
        max_abs_disp.columns.name = None

        return max_abs_disp

    def _extract_forces(self, direction: str) -> pd.DataFrame:
        """Extract story forces (shears) for specified direction.

        Reads "Story Forces" sheet and calculates maximum absolute shear
        per story/case (bottom location only).

        Args:
            direction: 'X', 'Y', or 'XY'

        Returns:
            DataFrame with columns: Story, [Output Cases...]
        """
        # Read Story Forces sheet
        df = pd.read_excel(self.excel_data, sheet_name='Story Forces', header=1)
        df = df.drop(0)  # Drop units row

        # Filter to Bottom location only (exclude Top)
        df = df[~df['Location'].str.contains('Top', na=False)]

        # Handle based on direction
        if direction == 'XY':
            # Bi-directional: compute resultant from VX and VY
            df = df[df['Output Case'].apply(lambda x: 'X' in str(x).upper() and 'Y' in str(x).upper())]

            # Filter columns
            df = df[['Story', 'Output Case', 'Step Type', 'Location', 'VX', 'VY']]

            # Compute resultant shear
            df['Shear'] = ((df['VX']**2 + df['VY']**2)**0.5)
            col_shear = 'Shear'
        else:
            # Uni-directional: X or Y
            col_shear = 'VX' if direction == 'X' else 'VY'

            # Filter columns
            df = df[['Story', 'Output Case', 'Step Type', 'Location', col_shear]]

            # Filter by pushover direction
            df = df[df['Output Case'].apply(lambda x: direction in str(x).upper())]

        # Preserve story order from Excel (first occurrence order)
        story_order = df['Story'].unique().tolist()

        # Calculate maximum absolute shear per story and output case
        max_shears = df.groupby(['Story', 'Output Case'], sort=False)[col_shear].apply(
            lambda x: x.abs().max()
        ).unstack().reset_index()

        # Restore original story order
        max_shears['Story'] = pd.Categorical(max_shears['Story'], categories=story_order, ordered=True)
        max_shears = max_shears.sort_values('Story').reset_index(drop=True)

        # Remove column index name
        max_shears.columns.name = None

        return max_shears

    def get_available_directions(self) -> List[str]:
        """Detect available pushover directions from output cases.

        Returns:
            List of detected directions (e.g., ['X', 'Y', 'XY'])
        """
        # Read Story Drifts sheet to detect directions
        df = pd.read_excel(self.excel_data, sheet_name='Story Drifts', header=1)
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
        df = pd.read_excel(self.excel_data, sheet_name='Story Drifts', header=1)
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
