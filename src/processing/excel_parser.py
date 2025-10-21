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
        """
        sheet = "Story Drifts"
        columns = [0, 1, 3, 4, 5]  # Output Case, Story, Direction, Drift columns

        df = self.read_sheet(sheet, columns)

        # Get unique load cases and stories
        unique_vals = self.get_unique_values(df, ["Output Case", "Story"])
        load_cases = unique_vals["Output Case"]
        stories = unique_vals["Story"]

        # Reverse stories to get top-down order
        stories.reverse()

        return df, load_cases, stories

    def get_story_accelerations(self) -> Tuple[pd.DataFrame, List[str], List[str]]:
        """Parse story acceleration data from Excel file.

        Returns:
            Tuple of (DataFrame, load_cases, stories)
        """
        sheet = "Story Accelerations"
        columns = [0, 1, 3, 4, 5]  # Output Case, Story, Direction, UX, UY

        df = self.read_sheet(sheet, columns)

        # Get unique load cases and stories
        unique_vals = self.get_unique_values(df, ["Output Case", "Story"])
        load_cases = unique_vals["Output Case"]
        stories = unique_vals["Story"]

        stories.reverse()

        return df, load_cases, stories

    def get_story_forces(self) -> Tuple[pd.DataFrame, List[str], List[str]]:
        """Parse story force data from Excel file.

        Returns:
            Tuple of (DataFrame, load_cases, stories)
        """
        sheet = "Story Forces"
        columns = [0, 1, 3, 4, 6, 7]  # Output Case, Story, Location, Direction, VX, VY

        df = self.read_sheet(sheet, columns)

        # Get unique load cases and stories
        unique_vals = self.get_unique_values(df, ["Output Case", "Story"])
        load_cases = unique_vals["Output Case"]
        stories = unique_vals["Story"]

        stories.reverse()

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
