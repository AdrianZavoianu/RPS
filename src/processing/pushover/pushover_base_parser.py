"""
Base class for pushover result parsers.

Provides common functionality for all pushover parsers:
- Excel file loading and sheet reading
- Direction filtering
- Order preservation
- Common method signatures

Subclasses only need to implement:
- _get_primary_sheet(): Return the main sheet name for this parser
- parse(direction): Parse results for a specific direction
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Any
import logging

import pandas as pd

from utils.pushover_utils import detect_direction, preserve_order, restore_categorical_order

logger = logging.getLogger(__name__)


class BasePushoverParser(ABC):
    """Abstract base class for all pushover result parsers.

    Provides shared functionality:
    - Excel file management
    - Sheet reading with units row removal
    - Direction detection and filtering
    - Order preservation utilities

    Subclasses implement parse() for their specific result type.
    """

    # Valid directions for pushover analysis
    VALID_DIRECTIONS = ('X', 'Y', 'XY')

    def __init__(self, file_path: Path):
        """Initialize parser with Excel file path.

        Args:
            file_path: Path to Excel file with pushover results
        """
        self.file_path = file_path
        self.excel_data = pd.ExcelFile(file_path)

    def _read_sheet(self, sheet_name: str, drop_units: bool = True) -> pd.DataFrame:
        """Read Excel sheet with standard preprocessing.

        Args:
            sheet_name: Name of sheet to read
            drop_units: If True, drop the units row (row 0 after header)

        Returns:
            DataFrame with sheet data

        Raises:
            ValueError: If sheet does not exist
        """
        if sheet_name not in self.excel_data.sheet_names:
            raise ValueError(f"Sheet '{sheet_name}' not found in {self.file_path.name}")

        df = pd.read_excel(self.excel_data, sheet_name=sheet_name, header=1)
        if drop_units and len(df) > 0:
            df = df.drop(0)  # Drop units row
        return df

    def _filter_by_direction(
        self,
        df: pd.DataFrame,
        direction: str,
        column: str = 'Output Case'
    ) -> pd.DataFrame:
        """Filter DataFrame by pushover direction.

        Args:
            df: DataFrame to filter
            direction: 'X', 'Y', or 'XY'
            column: Column containing output case names

        Returns:
            Filtered DataFrame
        """
        direction = direction.upper()

        if direction == 'XY':
            # Bi-directional: both X and Y in name
            mask = df[column].apply(
                lambda x: 'X' in str(x).upper() and 'Y' in str(x).upper()
            )
        else:
            # Uni-directional: X or Y in name
            mask = df[column].apply(lambda x: direction in str(x).upper())

        return df[mask].copy()

    def _filter_by_direction_regex(
        self,
        df: pd.DataFrame,
        direction: str,
        column: str = 'Output Case'
    ) -> pd.DataFrame:
        """Filter DataFrame by direction using regex pattern.

        More precise filtering that matches direction patterns like X+, X-, Y+, Y-.

        Args:
            df: DataFrame to filter
            direction: 'X' or 'Y'
            column: Column containing output case names

        Returns:
            Filtered DataFrame
        """
        pattern = f'{direction.upper()}[+-]?'
        return df[df[column].str.contains(pattern, na=False, regex=True, case=False)].copy()

    def _preserve_order(self, df: pd.DataFrame, column: str) -> List[Any]:
        """Get unique values preserving first-occurrence order.

        Args:
            df: DataFrame to extract values from
            column: Column name

        Returns:
            List of unique values in Excel order
        """
        return preserve_order(df, column)

    def _restore_order(
        self,
        df: pd.DataFrame,
        column: str,
        order: List[Any]
    ) -> pd.DataFrame:
        """Restore original order using Pandas Categorical.

        Args:
            df: DataFrame to sort
            column: Column to use for ordering
            order: List of values in desired order

        Returns:
            DataFrame sorted by the categorical order
        """
        return restore_categorical_order(df, column, order)

    def _aggregate_max_abs(
        self,
        df: pd.DataFrame,
        group_cols: List[str],
        value_col: str
    ) -> pd.DataFrame:
        """Aggregate by taking absolute maximum across step types.

        Common pattern for extracting max/min envelope values.

        Args:
            df: DataFrame with data
            group_cols: Columns to group by (e.g., ['Pier', 'Story', 'Output Case'])
            value_col: Column to aggregate (e.g., 'V2', 'Rotation')

        Returns:
            Wide-format DataFrame with Output Case columns
        """
        result = df.groupby(group_cols, sort=False)[value_col].apply(
            lambda x: x.abs().max()
        ).unstack().reset_index()

        # Clean up column index name
        result.columns.name = None
        return result

    def _validate_direction(self, direction: str) -> str:
        """Validate and normalize direction string.

        Args:
            direction: Direction to validate

        Returns:
            Normalized direction string (uppercase)

        Raises:
            ValueError: If direction is invalid
        """
        direction = direction.upper()
        if direction not in self.VALID_DIRECTIONS:
            raise ValueError(
                f"Invalid direction '{direction}'. Must be one of {self.VALID_DIRECTIONS}"
            )
        return direction

    def validate_sheet_exists(self, sheet_name: str) -> bool:
        """Check if a sheet exists in the Excel file.

        Args:
            sheet_name: Name of sheet to check

        Returns:
            True if sheet exists
        """
        return sheet_name in self.excel_data.sheet_names

    @abstractmethod
    def _get_primary_sheet(self) -> str:
        """Return the primary sheet name for this parser.

        Used by get_available_directions() and get_output_cases().

        Returns:
            Sheet name string
        """
        pass

    @abstractmethod
    def parse(self, direction: str) -> Any:
        """Parse results for specified direction.

        Args:
            direction: 'X', 'Y', or 'XY'

        Returns:
            Parser-specific results container (dataclass)
        """
        pass

    def get_available_directions(self) -> List[str]:
        """Detect available pushover directions from output cases.

        Reads the primary sheet and checks output case names for X/Y patterns.

        Returns:
            List of detected directions (e.g., ['X', 'Y'])
        """
        sheet_name = self._get_primary_sheet()
        if not self.validate_sheet_exists(sheet_name):
            return []

        df = self._read_sheet(sheet_name)

        if 'Output Case' not in df.columns:
            return []

        output_cases = df['Output Case'].dropna().unique()

        directions = []

        # Check for bi-directional first
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
            Sorted list of output case names
        """
        sheet_name = self._get_primary_sheet()
        if not self.validate_sheet_exists(sheet_name):
            return []

        df = self._read_sheet(sheet_name)

        if 'Output Case' not in df.columns:
            return []

        direction = direction.upper()

        if direction == 'XY':
            mask = df['Output Case'].apply(
                lambda x: 'X' in str(x).upper() and 'Y' in str(x).upper()
            )
        else:
            mask = df['Output Case'].apply(lambda x: direction in str(x).upper())

        cases = df[mask]['Output Case'].unique()
        return sorted(cases.tolist())
