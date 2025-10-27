"""Excel file parser for ETABS/SAP2000 results.

Refactored from ETDB_Functions.py to be more modular and database-oriented.
"""

import pandas as pd
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any


class ExcelParser:
    """Parser for ETABS/SAP2000 Excel result files."""

    def __init__(self, file_path: str):
        """Initialize parser with Excel file path.

        Args:
            file_path: Path to Excel file
        """
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"Excel file not found: {file_path}")

    def read_sheet(
        self,
        sheet_name: str,
        columns: List[int],
        skiprows: Optional[List[int]] = None,
    ) -> pd.DataFrame:
        """Read a specific sheet from the Excel file.

        Args:
            sheet_name: Name of the sheet to read
            columns: List of column indices to read
            skiprows: List of row indices to skip (default: [0, 2] for ETABS format)

        Returns:
            DataFrame containing the sheet data
        """
        if skiprows is None:
            skiprows = [0, 2]  # Standard ETABS format

        try:
            df = pd.read_excel(
                self.file_path,
                sheet_name=sheet_name,
                skiprows=skiprows,
                usecols=columns,
            )
            return df
        except Exception as e:
            raise ValueError(f"Error reading sheet '{sheet_name}': {e}")

    def get_unique_values(
        self, df: pd.DataFrame, column_names: List[str]
    ) -> Dict[str, List[Any]]:
        """Get unique values for specified columns.

        Args:
            df: DataFrame to process
            column_names: List of column names to extract unique values from

        Returns:
            Dictionary mapping column names to lists of unique values
        """
        result = {}
        for col_name in column_names:
            if col_name in df.columns:
                unique_vals = df[col_name].unique().tolist()
                result[col_name] = unique_vals
            else:
                raise ValueError(f"Column '{col_name}' not found in DataFrame")
        return result

    def get_story_drifts(self) -> Tuple[pd.DataFrame, List[str], List[str]]:
        """Parse story drift data from Excel file.

        Returns:
            Tuple of (DataFrame, load_cases, stories)

        Note:
            Stories list preserves exact order from Excel (typically bottom to top from ETABS).
            sort_order = index in this list (0=first story in Excel, typically ground floor).
            For plotting: higher sort_order = higher in building.
        """
        sheet = "Story Drifts"
        columns = [0, 1, 3, 4, 5]  # Output Case, Story, Direction, Drift columns

        df = self.read_sheet(sheet, columns)

        # Get unique load cases and stories
        unique_vals = self.get_unique_values(df, ["Output Case", "Story"])
        load_cases = unique_vals["Output Case"]
        stories = unique_vals["Story"]

        # Keep stories in Excel order (no reversal - maintain source order)
        # ETABS typically exports bottom-to-top (Ground, 1st, 2nd, ..., Roof)

        return df, load_cases, stories

    def get_story_accelerations(self) -> Tuple[pd.DataFrame, List[str], List[str]]:
        """Parse story acceleration data from Excel file.

        Returns:
            Tuple of (DataFrame, load_cases, stories)

        Note:
            Stories list preserves exact order from Excel (typically bottom to top from ETABS).
        """
        sheet = "Story Accelerations"
        columns = [0, 1, 3, 4, 5]  # Output Case, Story, Direction, UX, UY

        df = self.read_sheet(sheet, columns)

        # Get unique load cases and stories
        unique_vals = self.get_unique_values(df, ["Output Case", "Story"])
        load_cases = unique_vals["Output Case"]
        stories = unique_vals["Story"]

        # Keep stories in Excel order (no reversal - maintain source order)

        return df, load_cases, stories

    def get_story_forces(self) -> Tuple[pd.DataFrame, List[str], List[str]]:
        """Parse story force data from Excel file.

        Returns:
            Tuple of (DataFrame, load_cases, stories)

        Note:
            Stories list preserves exact order from Excel (typically bottom to top from ETABS).
        """
        sheet = "Story Forces"
        columns = [0, 1, 3, 4, 6, 7]  # Output Case, Story, Location, Direction, VX, VY

        df = self.read_sheet(sheet, columns)

        # Get unique load cases and stories
        unique_vals = self.get_unique_values(df, ["Output Case", "Story"])
        load_cases = unique_vals["Output Case"]
        stories = unique_vals["Story"]

        # Keep stories in Excel order (no reversal - maintain source order)

        return df, load_cases, stories

    def get_pier_forces(self) -> Tuple[pd.DataFrame, List[str], List[str], List[str]]:
        """Parse pier force data from Excel file.

        Returns:
            Tuple of (DataFrame, load_cases, stories, piers)

        Note:
            Stories list preserves exact order from Excel (typically bottom to top from ETABS).
            Returns raw row-based data: each row contains Story, Pier, Output Case, Location, V2, V3, etc.
        """
        sheet = "Pier Forces"
        # Columns: Story, Pier, Output Case, Step Type, Location, P, V2, V3, T, M2, M3
        columns = [0, 1, 2, 4, 5, 7, 8]  # Story, Pier, Output Case, Location, P, V2, V3

        df = self.read_sheet(sheet, columns)

        # Get unique values
        unique_vals = self.get_unique_values(df, ["Output Case", "Story", "Pier"])
        load_cases = unique_vals["Output Case"]
        stories = unique_vals["Story"]
        piers = unique_vals["Pier"]

        # Keep stories in Excel order (no reversal - maintain source order)

        return df, load_cases, stories, piers

    def get_joint_displacements(self) -> Tuple[pd.DataFrame, List[str], List[str]]:
        """Parse joint displacement data (global) from Excel file.

        Only the 'Joint DisplacementsG' sheet is considered valid for global story displacements.

        Returns:
            Tuple of (DataFrame, load_cases, stories)
        """
        sheet = "Joint DisplacementsG"

        if not self.validate_sheet_exists(sheet):
            return pd.DataFrame(), [], []

        # Columns: Story, Label, Unique Name, Output Case, Case Type, Step Type, Ux, Uy, Uz, Rx, Ry, Rz
        df = self.read_sheet(sheet, columns=[0, 1, 2, 3, 5, 6, 7, 8, 9, 10, 11], skiprows=[0, 2])
        df = df.rename(columns=lambda c: str(c).strip())

        expected_columns = {"Story", "Output Case", "Ux", "Uy"}
        missing = expected_columns - set(df.columns)
        if missing:
            raise ValueError(f"Missing expected columns in 'Joint DisplacementsG': {missing}")

        df = df[["Story", "Output Case", "Ux", "Uy"]].dropna(subset=["Story", "Output Case"])

        load_cases = df["Output Case"].unique().tolist()
        stories = df["Story"].unique().tolist()

        return df, load_cases, stories

    def get_available_sheets(self) -> List[str]:
        """Get list of available sheets in the Excel file.

        Returns:
            List of sheet names
        """
        try:
            excel_file = pd.ExcelFile(self.file_path)
            return excel_file.sheet_names
        except Exception as e:
            raise ValueError(f"Error reading Excel file: {e}")

    def validate_sheet_exists(self, sheet_name: str) -> bool:
        """Check if a sheet exists in the Excel file.

        Args:
            sheet_name: Name of sheet to check

        Returns:
            True if sheet exists, False otherwise
        """
        available_sheets = self.get_available_sheets()
        return sheet_name in available_sheets

    def get_quad_rotations(self) -> Tuple[pd.DataFrame, List[str], List[str], List[str]]:
        """Parse quad strain gauge rotation data from Excel file.

        Returns:
            Tuple of (DataFrame, load_cases, stories, piers)

        Note:
            Stories list preserves exact order from Excel (typically bottom to top from ETABS).
            Returns raw row-based data: each row contains Story, quad Name, PropertyName (pier), Output Case, etc.
            PropertyName column contains the pier/wall identifier.
        """
        sheet = "Quad Strain Gauge - Rotation"
        # Columns: Story, Name, PropertyName, Output Case, CaseType, StepType, Direction, Rotation, MaxRotation, MinRotation
        columns = [0, 1, 2, 3, 5, 6, 7, 8, 9]  # Story, Name, PropertyName, Output Case, StepType, Direction, Rotation, MaxRotation, MinRotation

        df = self.read_sheet(sheet, columns)

        # Get unique values
        unique_vals = self.get_unique_values(df, ["Output Case", "Story", "PropertyName"])
        load_cases = unique_vals["Output Case"]
        stories = unique_vals["Story"]
        piers = unique_vals["PropertyName"]  # PropertyName contains pier identifiers like "B-B"

        # Keep stories in Excel order (no reversal - maintain source order)

        return df, load_cases, stories, piers
