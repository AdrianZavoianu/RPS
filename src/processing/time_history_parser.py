"""Parser for time-history Excel files from ETABS/SAP2000.

Extracts step-by-step time series data for:
- Story Drifts (X, Y directions)
- Story Forces (VX, VY shears)
- Joint Displacements (Ux, Uy)
- Diaphragm Accelerations (UX, UY)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class TimeSeriesData:
    """Container for a single time series (one story, one direction)."""

    story: str
    direction: str
    time_steps: List[float]
    values: List[float]
    story_sort_order: int = 0


@dataclass
class TimeHistoryParseResult:
    """Container for all parsed time history data from a file."""

    load_case_name: str
    drifts_x: List[TimeSeriesData] = field(default_factory=list)
    drifts_y: List[TimeSeriesData] = field(default_factory=list)
    forces_x: List[TimeSeriesData] = field(default_factory=list)
    forces_y: List[TimeSeriesData] = field(default_factory=list)
    displacements_x: List[TimeSeriesData] = field(default_factory=list)
    displacements_y: List[TimeSeriesData] = field(default_factory=list)
    accelerations_x: List[TimeSeriesData] = field(default_factory=list)
    accelerations_y: List[TimeSeriesData] = field(default_factory=list)
    stories: List[str] = field(default_factory=list)  # Story names in building order


class TimeHistoryParser:
    """Parser for time-history Excel files."""

    # Sheet name mappings
    STORY_DRIFTS_SHEET = "Story Drifts"
    STORY_FORCES_SHEET = "Story Forces"
    JOINT_DISPLACEMENTS_SHEET = "Joint Displacements"
    DIAPHRAGM_ACCELERATIONS_SHEET = "Diaphragm Accelerations"

    def __init__(self, file_path: str | Path):
        self.file_path = Path(file_path)
        self._xl: Optional[pd.ExcelFile] = None

    def parse(self) -> TimeHistoryParseResult:
        """Parse the Excel file and extract all time series data."""
        self._xl = pd.ExcelFile(self.file_path)

        # Detect load case name from Story Drifts sheet
        load_case_name = self._detect_load_case_name()

        result = TimeHistoryParseResult(load_case_name=load_case_name)

        # Parse each sheet
        if self.STORY_DRIFTS_SHEET in self._xl.sheet_names:
            result.drifts_x, result.drifts_y, result.stories = self._parse_story_drifts()

        if self.STORY_FORCES_SHEET in self._xl.sheet_names:
            result.forces_x, result.forces_y, _ = self._parse_story_forces()

        if self.JOINT_DISPLACEMENTS_SHEET in self._xl.sheet_names:
            result.displacements_x, result.displacements_y, _ = self._parse_joint_displacements()

        if self.DIAPHRAGM_ACCELERATIONS_SHEET in self._xl.sheet_names:
            result.accelerations_x, result.accelerations_y, _ = self._parse_diaphragm_accelerations()

        self._xl.close()
        return result

    def _detect_load_case_name(self) -> str:
        """Detect the load case name from the Story Drifts sheet."""
        if self.STORY_DRIFTS_SHEET not in self._xl.sheet_names:
            return "Unknown"

        df = pd.read_excel(self._xl, sheet_name=self.STORY_DRIFTS_SHEET, header=0, skiprows=[1], nrows=5)
        # Column 1 is "Output Case"
        output_case_col = df.columns[1]
        first_case = df[output_case_col].dropna().iloc[0] if not df[output_case_col].dropna().empty else "Unknown"
        return str(first_case)

    def _parse_story_drifts(self) -> Tuple[List[TimeSeriesData], List[TimeSeriesData], List[str]]:
        """Parse Story Drifts sheet for X and Y directions.

        Returns:
            Tuple of (drifts_x, drifts_y, story_order)
        """
        df = pd.read_excel(self._xl, sheet_name=self.STORY_DRIFTS_SHEET, header=0, skiprows=[1])

        # Map to proper column names
        # Columns: Story, Output Case, Case Type, Step Type, Step Number, Direction, Drift, ...
        col_mapping = {
            df.columns[0]: "Story",
            df.columns[1]: "Output_Case",
            df.columns[2]: "Case_Type",
            df.columns[3]: "Step_Type",
            df.columns[4]: "Step_Num",
            df.columns[5]: "Direction",
            df.columns[6]: "Drift",
        }
        df = df.rename(columns=col_mapping)

        # Filter valid rows
        df = df.dropna(subset=["Story"])
        df = df[df["Step_Type"] == "Step By Step"]

        # Get story order (preserve first-occurrence order)
        story_order = df["Story"].unique().tolist()

        # Parse X direction
        drifts_x = self._extract_time_series_by_direction(df, "X", "Drift", story_order)

        # Parse Y direction
        drifts_y = self._extract_time_series_by_direction(df, "Y", "Drift", story_order)

        return drifts_x, drifts_y, story_order

    def _parse_story_forces(self) -> Tuple[List[TimeSeriesData], List[TimeSeriesData], List[str]]:
        """Parse Story Forces sheet for VX and VY shears.

        Returns:
            Tuple of (forces_x, forces_y, story_order)
        """
        df = pd.read_excel(self._xl, sheet_name=self.STORY_FORCES_SHEET, header=0, skiprows=[1])

        # Columns: Story, Output Case, Case Type, Step Type, Step Number, Location, P, VX, VY, T, MX, MY
        col_mapping = {
            df.columns[0]: "Story",
            df.columns[1]: "Output_Case",
            df.columns[2]: "Case_Type",
            df.columns[3]: "Step_Type",
            df.columns[4]: "Step_Num",
            df.columns[5]: "Location",
            df.columns[6]: "P",
            df.columns[7]: "VX",
            df.columns[8]: "VY",
        }
        df = df.rename(columns=col_mapping)

        # Filter valid rows - use Bottom location for shears
        df = df.dropna(subset=["Story"])
        df = df[df["Step_Type"] == "Step By Step"]
        df = df[df["Location"] == "Bottom"]

        # Get story order
        story_order = df["Story"].unique().tolist()

        # Parse VX (X direction shear)
        forces_x = self._extract_time_series_direct(df, "VX", story_order)

        # Parse VY (Y direction shear)
        forces_y = self._extract_time_series_direct(df, "VY", story_order)

        return forces_x, forces_y, story_order

    def _parse_joint_displacements(self) -> Tuple[List[TimeSeriesData], List[TimeSeriesData], List[str]]:
        """Parse Joint Displacements sheet for Ux and Uy.

        Uses Label=1 joint (typically center of mass or reference joint).

        Returns:
            Tuple of (displacements_x, displacements_y, story_order)
        """
        df = pd.read_excel(self._xl, sheet_name=self.JOINT_DISPLACEMENTS_SHEET, header=0, skiprows=[1])

        # Columns: Story, Label, Unique Name, Output Case, Case Type, Step Type, Step Number, Ux, Uy, Uz, ...
        col_mapping = {
            df.columns[0]: "Story",
            df.columns[1]: "Label",
            df.columns[2]: "Unique_Name",
            df.columns[3]: "Output_Case",
            df.columns[4]: "Case_Type",
            df.columns[5]: "Step_Type",
            df.columns[6]: "Step_Num",
            df.columns[7]: "Ux",
            df.columns[8]: "Uy",
            df.columns[9]: "Uz",
        }
        df = df.rename(columns=col_mapping)

        # Filter valid rows - use Label=1 joint for floor displacements
        df = df.dropna(subset=["Story"])
        df = df[df["Step_Type"] == "Step By Step"]
        df = df[df["Label"] == 1]

        # Get story order
        story_order = df["Story"].unique().tolist()

        # Parse Ux (X direction displacement)
        displacements_x = self._extract_time_series_direct(df, "Ux", story_order)

        # Parse Uy (Y direction displacement)
        displacements_y = self._extract_time_series_direct(df, "Uy", story_order)

        return displacements_x, displacements_y, story_order

    def _parse_diaphragm_accelerations(self) -> Tuple[List[TimeSeriesData], List[TimeSeriesData], List[str]]:
        """Parse Diaphragm Accelerations sheet for UX and UY.

        Returns:
            Tuple of (accelerations_x, accelerations_y, story_order)
        """
        df = pd.read_excel(self._xl, sheet_name=self.DIAPHRAGM_ACCELERATIONS_SHEET, header=0, skiprows=[1])

        # Columns: Story, Diaphragm, Output Case, Case Type, Step Type, Step Number, Max UX, Max UY, ...
        col_mapping = {
            df.columns[0]: "Story",
            df.columns[1]: "Diaphragm",
            df.columns[2]: "Output_Case",
            df.columns[3]: "Case_Type",
            df.columns[4]: "Step_Type",
            df.columns[5]: "Step_Num",
            df.columns[6]: "Max_UX",
            df.columns[7]: "Max_UY",
        }
        df = df.rename(columns=col_mapping)

        # Filter valid rows
        df = df.dropna(subset=["Story"])
        df = df[df["Step_Type"] == "Step By Step"]

        # Get story order
        story_order = df["Story"].unique().tolist()

        # Parse Max UX (X direction acceleration)
        accelerations_x = self._extract_time_series_direct(df, "Max_UX", story_order)

        # Parse Max UY (Y direction acceleration)
        accelerations_y = self._extract_time_series_direct(df, "Max_UY", story_order)

        return accelerations_x, accelerations_y, story_order

    def _extract_time_series_by_direction(
        self, df: pd.DataFrame, direction: str, value_col: str, story_order: List[str]
    ) -> List[TimeSeriesData]:
        """Extract time series for each story filtered by direction column."""
        result = []

        df_dir = df[df["Direction"] == direction]

        for idx, story in enumerate(story_order):
            story_df = df_dir[df_dir["Story"] == story].sort_values("Step_Num")

            if story_df.empty:
                continue

            time_steps = story_df["Step_Num"].tolist()
            values = story_df[value_col].tolist()

            result.append(TimeSeriesData(
                story=story,
                direction=direction,
                time_steps=time_steps,
                values=values,
                story_sort_order=idx,
            ))

        return result

    def _extract_time_series_direct(
        self, df: pd.DataFrame, value_col: str, story_order: List[str]
    ) -> List[TimeSeriesData]:
        """Extract time series for each story from a direct value column."""
        result = []

        # Determine direction from column name
        if value_col in ("VX", "Ux", "Max_UX"):
            direction = "X"
        elif value_col in ("VY", "Uy", "Max_UY"):
            direction = "Y"
        else:
            direction = ""

        for idx, story in enumerate(story_order):
            story_df = df[df["Story"] == story].sort_values("Step_Num")

            if story_df.empty:
                continue

            time_steps = story_df["Step_Num"].tolist()
            values = story_df[value_col].tolist()

            result.append(TimeSeriesData(
                story=story,
                direction=direction,
                time_steps=time_steps,
                values=values,
                story_sort_order=idx,
            ))

        return result


def prescan_time_history_file(file_path: str | Path) -> Dict:
    """Quick prescan of time history file to get metadata without full parsing.

    Returns:
        Dict with keys: load_case_name, num_stories, num_time_steps, available_sheets
    """
    xl = pd.ExcelFile(file_path)

    result = {
        "load_case_name": "Unknown",
        "num_stories": 0,
        "num_time_steps": 0,
        "available_sheets": xl.sheet_names,
    }

    # Get load case name and story count from Story Drifts
    if "Story Drifts" in xl.sheet_names:
        df = pd.read_excel(xl, sheet_name="Story Drifts", header=0, skiprows=[1])
        df = df.dropna(subset=[df.columns[0]])

        if not df.empty:
            result["load_case_name"] = str(df.iloc[:, 1].dropna().iloc[0])
            result["num_stories"] = df.iloc[:, 0].nunique()
            result["num_time_steps"] = df.iloc[:, 4].nunique()

    xl.close()
    return result
