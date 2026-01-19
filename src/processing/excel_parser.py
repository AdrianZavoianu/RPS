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
        self._excel_file: Optional[pd.ExcelFile] = None
        self._joint_displacements_df: Optional[pd.DataFrame] = None
        self._available_sheets: Optional[List[str]] = None
        self._column_forces_df: Optional[pd.DataFrame] = None

    def _get_excel_file(self) -> pd.ExcelFile:
        if self._excel_file is None:
            self._excel_file = pd.ExcelFile(self.file_path)
        return self._excel_file

    def close(self) -> None:
        excel_file = self._excel_file
        if excel_file is not None:
            try:
                excel_file.close()
            except Exception:
                pass
            self._excel_file = None

    def __del__(self) -> None:
        self.close()

    @staticmethod
    def _normalize_header_name(name: object) -> str:
        return "".join(ch for ch in str(name).lower() if ch.isalnum())

    def _find_output_case_column(self, columns: List[object]) -> Optional[object]:
        target = "outputcase"
        for col in columns:
            if self._normalize_header_name(col) == target:
                return col
        return None

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
            df = self._get_excel_file().parse(
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
        """Parse story acceleration data from 'Diaphragm Accelerations' sheet.

        Returns:
            Tuple of (DataFrame, load_cases, stories)

        Note:
            Stories list preserves exact order from Excel (typically bottom to top from ETABS).
            Format has separate Max/Min rows with Max UX/UY and Min UX/UY columns.
            Columns: [Story, Output Case, Step Type, Max UX, Max UY, Min UX, Min UY]
        """
        sheet = "Diaphragm Accelerations"
        # Columns: Story, Diaphragm, Output Case, Case Type, Step Type, Max UX, Max UY, ..., Min UX, Min UY
        # Indices:   0       1          2           3          4         5       6             11      12
        columns = [0, 2, 4, 5, 6, 11, 12]  # Story, Output Case, Step Type, Max UX, Max UY, Min UX, Min UY

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

        Uses 'Joint Displacements' sheet for global story displacements.

        Returns:
            Tuple of (DataFrame, load_cases, stories)
        """
        sheet = "Joint Displacements"

        if not self.validate_sheet_exists(sheet):
            return pd.DataFrame(), [], []

        df_full = self._load_joint_displacements_full()
        df = df_full[["Story", "Output Case", "Ux", "Uy"]].dropna(subset=["Story", "Output Case"])

        load_cases = df["Output Case"].unique().tolist()
        stories = df["Story"].unique().tolist()

        return df, load_cases, stories

    def get_available_sheets(self) -> List[str]:
        """Get list of available sheets in the Excel file.

        Returns:
            List of sheet names
        """
        try:
            if self._available_sheets is None:
                self._available_sheets = list(self._get_excel_file().sheet_names)
            return list(self._available_sheets)
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

    def _load_joint_displacements_full(self) -> pd.DataFrame:
        """Load the Joint Displacements sheet (all needed columns) with simple caching."""
        if self._joint_displacements_df is None:
            sheet = "Joint Displacements"
            # Only pull columns we actually use (Story, Label, Unique Name, Output Case, Step Type, Ux, Uy, Uz)
            columns = [0, 1, 2, 3, 5, 6, 7, 8]
            df = self.read_sheet(sheet, columns, skiprows=[0, 2])
            df.columns = [
                "Story",
                "Label",
                "Unique Name",
                "Output Case",
                "Step Type",
                "Ux",
                "Uy",
                "Uz",
            ]
            self._joint_displacements_df = df
        return self._joint_displacements_df.copy()

    def get_load_cases_only(self, sheet_name: str) -> Optional[List[str]]:
        """Return load cases from a sheet using a lightweight single-column read."""
        if not self.validate_sheet_exists(sheet_name):
            return []

        try:
            header_df = self._get_excel_file().parse(
                sheet_name=sheet_name,
                skiprows=[0, 2],
                nrows=0,
            )
        except Exception:
            return None

        output_case_col = self._find_output_case_column(list(header_df.columns))
        if output_case_col is None:
            return None

        try:
            df = self._get_excel_file().parse(
                sheet_name=sheet_name,
                skiprows=[0, 2],
                usecols=[output_case_col],
            )
        except Exception:
            return None
        if df.empty:
            return []
        series = df.iloc[:, 0].dropna()
        if series.empty:
            return []
        return pd.unique(series.astype(str)).tolist()

    def get_column_forces(self) -> Tuple[pd.DataFrame, List[str], List[str], List[str]]:
        """Parse column force data from Excel file.

        Returns:
            Tuple of (DataFrame, load_cases, stories, columns)

        Note:
            Stories list preserves exact order from Excel (typically bottom to top from ETABS).
            Returns raw row-based data: each row contains Story, Column, Unique Name, Output Case, Location, V2, V3, etc.
        """
        sheet = "Element Forces - Columns"
        # Columns: Story, Column, Unique Name, Output Case, CaseType, Step Type, Location, P, V2, V3, T, M2, M3
        # Indices:   0       1       2           3            4          5          6      7   8    9  10  11  12
        columns = [0, 1, 2, 3, 6, 7, 8, 9]  # Story, Column, Unique Name, Output Case, Location, P, V2, V3

        if self._column_forces_df is None:
            self._column_forces_df = self.read_sheet(sheet, columns)
        df = self._column_forces_df.copy()

        # Get unique values
        unique_vals = self.get_unique_values(df, ["Output Case", "Story", "Column"])
        load_cases = unique_vals["Output Case"]
        stories = unique_vals["Story"]
        columns_list = unique_vals["Column"]

        # Keep stories in Excel order (no reversal - maintain source order)

        return df, load_cases, stories, columns_list

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

    def get_fiber_hinge_states(self) -> Tuple[pd.DataFrame, List[str], List[str], List[str]]:
        """Parse fiber hinge state data for columns from Excel file.

        Returns:
            Tuple of (DataFrame, load_cases, stories, columns)

        Note:
            Only processes columns where Frame/Wall starts with 'C' (e.g., C2, C10).
            Stories list preserves exact order from Excel (typically bottom to top from ETABS).
            Returns raw row-based data with R2 and R3 rotation values.
        """
        sheet = "Fiber Hinge States"
        # Columns: Story, Frame/Wall, Unique Name, Output Case, Step Type, R2, R3
        # Actual indices: 0=Story, 1=Frame/Wall, 2=Unique Name, 3=Output Case, 5=Step Type, 20=R2, 21=R3
        columns = [0, 1, 2, 3, 5, 20, 21]  # Story, Frame/Wall, Unique Name, Output Case, Step Type, R2, R3

        df = self.read_sheet(sheet, columns)

        # Filter only columns (Frame/Wall starts with 'C')
        if "Frame/Wall" in df.columns:
            df = df[df["Frame/Wall"].astype(str).str.startswith("C", na=False)].copy()

        # Get unique values
        unique_vals = self.get_unique_values(df, ["Output Case", "Story", "Frame/Wall"])
        load_cases = unique_vals["Output Case"]
        stories = unique_vals["Story"]
        columns_list = unique_vals["Frame/Wall"]  # Column identifiers like "C2", "C10"

        # Keep stories in Excel order (no reversal - maintain source order)

        return df, load_cases, stories, columns_list

    def get_hinge_states(self) -> Tuple[pd.DataFrame, List[str], List[str], List[str]]:
        """Parse hinge state data for beams from Excel file.

        Returns:
            Tuple of (DataFrame, load_cases, stories, beams)

        Note:
            Only processes beams where Frame/Wall starts with 'B' (e.g., B19, B20).
            Stories list preserves exact order from Excel (typically bottom to top from ETABS).
            Returns raw row-based data with R3 Plastic rotation values.
        """
        sheet = "Hinge States"
        # Columns: Story, Frame/Wall, Unique Name, Output Case, Step Type, Hinge, Generated Hinge, Rel Dist, R3 Plastic
        # Actual indices: 0=Story, 1=Frame/Wall, 2=Unique Name, 3=Output Case, 5=Step Type, 6=Hinge, 7=Generated Hinge, 8=Rel Dist, 21=R3 Plastic
        columns = [0, 1, 2, 3, 5, 6, 7, 8, 21]  # Story, Frame/Wall, Unique Name, Output Case, Step Type, Hinge, Generated Hinge, Rel Dist, R3 Plastic

        df = self.read_sheet(sheet, columns)

        # Filter only beams (Frame/Wall starts with 'B')
        if "Frame/Wall" in df.columns:
            df = df[df["Frame/Wall"].astype(str).str.startswith("B", na=False)].copy()

        # Get unique values
        unique_vals = self.get_unique_values(df, ["Output Case", "Story", "Frame/Wall"])
        load_cases = unique_vals["Output Case"]
        stories = unique_vals["Story"]
        beams_list = unique_vals["Frame/Wall"]  # Beam identifiers like "B19", "B20"

        return df, load_cases, stories, beams_list

    def get_soil_pressures(self) -> Tuple[pd.DataFrame, List[str], List[str]]:
        """Parse soil pressure data from 'Soil Pressures' sheet.

        Returns:
            Tuple of (DataFrame, load_cases, unique_elements)

        Note:
            Computes minimum soil pressure per (Unique Name, Output Case).
            Each unique name represents a foundation shell element with multiple joints.
            Returns aggregated data: one row per (Shell Object, Unique Name, Output Case) with minimum pressure.
        """
        sheet = "Soil Pressures"
        # Columns: Story, Shell Object, Unique Name, Shell Element, Joint, Output Case, Case Type, Step Type, Soil Pressure, Global X, Global Y, Global Z
        # Indices:   0        1               2             3            4         5            6           7           8              9         10        11
        columns = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]

        df = self.read_sheet(sheet, columns)

        # Ensure expected column labels
        df.columns = [
            "Story", "Shell Object", "Unique Name", "Shell Element", "Joint",
            "Output Case", "Case Type", "Step Type", "Soil Pressure",
            "Global X", "Global Y", "Global Z",
        ]

        # Numeric safety
        df['Soil Pressure'] = pd.to_numeric(df['Soil Pressure'], errors='coerce')

        # Filter to only Min step type (discard Max entries with value 1)
        df = df[df['Step Type'] == 'Min'].copy()

        # Min soil pressure per (Shell Object, Unique Name, Output Case)
        grp = (df.groupby(['Shell Object', 'Unique Name', 'Output Case'], as_index=False)['Soil Pressure']
                 .min())

        # Get unique values
        load_cases = grp['Output Case'].unique().tolist()
        unique_elements = grp['Unique Name'].unique().tolist()

        return grp, load_cases, unique_elements

    def get_foundation_joints(self) -> List[str]:
        """Parse foundation joint list from 'Fou' sheet.

        Returns:
            List of unique joint names (strings) to monitor for vertical displacements
        """
        sheet = "Fou"

        if not self.validate_sheet_exists(sheet):
            return []

        # Only read first column (Unique Name)
        df = self.read_sheet(sheet, columns=[0])

        # Column might be named "Unique Name" or just take first column
        if 'Unique Name' in df.columns:
            joint_names = df['Unique Name'].dropna().astype(str).unique().tolist()
        else:
            # Use first column regardless of name
            joint_names = df.iloc[:, 0].dropna().astype(str).unique().tolist()

        return joint_names

    def get_vertical_displacements(self, foundation_joints: Optional[List[str]] = None) -> Tuple[pd.DataFrame, List[str], List[str]]:
        """Parse vertical displacement data from 'Joint Displacements' sheet.

        Filters to joints specified in foundation_joints parameter or from 'Fou' sheet.

        Args:
            foundation_joints: Optional list of joint names to filter. If None, reads from Fou sheet.

        Returns:
            Tuple of (DataFrame, load_cases, unique_joints)

        Note:
            Computes minimum vertical displacement (Uz) per (Unique Name, Output Case).
            Each unique name represents a specific joint at a foundation location.
            Returns aggregated data: one row per (Story, Label, Unique Name, Output Case) with minimum Uz.
        """
        sheet = "Joint Displacements"

        # Get foundation joint list from parameter or Fou sheet
        if foundation_joints is None:
            foundation_joints = self.get_foundation_joints()

        if not foundation_joints:
            return pd.DataFrame(), [], []

        df = self._load_joint_displacements_full()

        # Convert Unique Name to string and filter to foundation joints only
        df['Unique Name'] = df['Unique Name'].astype(str)
        df = df[df['Unique Name'].isin(foundation_joints)].copy()

        if df.empty:
            return pd.DataFrame(), [], []

        # Numeric safety for Uz
        df['Uz'] = pd.to_numeric(df['Uz'], errors='coerce')

        # Filter to only Min step type (get minimum vertical displacement)
        df = df[df['Step Type'] == 'Min'].copy()

        # Min Uz per (Unique Name, Output Case) ONLY
        # The database unique constraint is on (project_id, result_set_id, unique_name, load_case_id)
        # so we must not include Story/Label in groupby to avoid duplicate key errors
        # Keep first Story and Label for reference (they should be consistent per joint)
        grp = (df.groupby(['Unique Name', 'Output Case'], as_index=False)
                 .agg({
                     'Uz': 'min',
                     'Story': 'first',  # Keep first Story for reference
                     'Label': 'first',  # Keep first Label for reference
                 }))

        # Rename Uz column to match expected format
        grp = grp.rename(columns={'Uz': 'Min Uz'})

        # Get unique values
        load_cases = grp['Output Case'].unique().tolist()
        unique_joints = grp['Unique Name'].unique().tolist()

        return grp, load_cases, unique_joints
