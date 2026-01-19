"""Process and transform result data for database storage."""

import pandas as pd
from typing import List, Dict, Any
import numpy as np


class ResultProcessor:
    """Process structural analysis results for database storage."""

    @staticmethod
    def process_story_drifts(
        df: pd.DataFrame, load_cases: List[str], stories: List[str], direction: str
    ) -> pd.DataFrame:
        """Process story drift data for a specific direction - vectorized.

        Args:
            df: Raw drift data DataFrame
            load_cases: List of load case names
            stories: List of story names (top-down order)
            direction: 'X' or 'Y'

        Returns:
            Processed DataFrame with columns: [Story, LoadCase, Direction, Drift, MaxDrift, MinDrift]
        """
        if df.empty or "Drift" not in df.columns:
            return pd.DataFrame(columns=["Story", "LoadCase", "Direction", "Drift", "MaxDrift", "MinDrift"])

        # Filter by direction once
        df_dir = df[df["Direction"] == direction].copy()
        if df_dir.empty:
            return pd.DataFrame(columns=["Story", "LoadCase", "Direction", "Drift", "MaxDrift", "MinDrift"])

        # Convert Drift to numeric
        df_dir["Drift"] = pd.to_numeric(df_dir["Drift"], errors="coerce")
        df_dir = df_dir.dropna(subset=["Drift"])
        if df_dir.empty:
            return pd.DataFrame(columns=["Story", "LoadCase", "Direction", "Drift", "MaxDrift", "MinDrift"])

        # Group by Story, Output Case and aggregate
        grouped = df_dir.groupby(["Story", "Output Case"], as_index=False).agg({
            "Drift": ["max", "min", lambda x: x.abs().max()]
        })

        # Flatten multi-level column names
        grouped.columns = ["Story", "LoadCase", "MaxDrift", "MinDrift", "Drift"]

        # Round values
        grouped["Drift"] = grouped["Drift"].round(4)
        grouped["MaxDrift"] = grouped["MaxDrift"].round(4)
        grouped["MinDrift"] = grouped["MinDrift"].round(4)
        grouped["Direction"] = direction

        return grouped[["Story", "LoadCase", "Direction", "Drift", "MaxDrift", "MinDrift"]]

    @staticmethod
    def process_story_accelerations(
        df: pd.DataFrame, load_cases: List[str], stories: List[str], direction: str
    ) -> pd.DataFrame:
        """Process story acceleration data from 'Diaphragm Accelerations' sheet - vectorized.

        Handles the format with separate Max/Min rows and Max UX/UY and Min UX/UY columns.

        Args:
            df: Raw diaphragm acceleration data DataFrame
            load_cases: List of load case names
            stories: List of story names (top-down order)
            direction: 'UX' or 'UY'

        Returns:
            Processed DataFrame with acceleration in g-units (converted from mm/sec²)
        """
        max_col = f'Max {direction}'
        min_col = f'Min {direction}'

        if df.empty or max_col not in df.columns or min_col not in df.columns:
            return pd.DataFrame(columns=["Story", "LoadCase", "Direction", "Acceleration", "MaxAcceleration", "MinAcceleration"])

        df = df.copy()

        # Convert to numeric
        df[max_col] = pd.to_numeric(df[max_col], errors="coerce")
        df[min_col] = pd.to_numeric(df[min_col], errors="coerce")

        # Split into Max and Min step types
        df_max = df[df["Step Type"] == "Max"].copy()
        df_min = df[df["Step Type"] == "Min"].copy()

        if df_max.empty or df_min.empty:
            return pd.DataFrame(columns=["Story", "LoadCase", "Direction", "Acceleration", "MaxAcceleration", "MinAcceleration"])

        # Aggregate max values per Story, Case
        max_grouped = df_max.groupby(["Story", "Output Case"], as_index=False).agg({max_col: "max"})
        max_grouped = max_grouped.rename(columns={max_col: "MaxAcceleration"})

        # Aggregate min values per Story, Case
        min_grouped = df_min.groupby(["Story", "Output Case"], as_index=False).agg({min_col: "min"})
        min_grouped = min_grouped.rename(columns={min_col: "MinAcceleration"})

        # Merge max and min
        merged = max_grouped.merge(min_grouped, on=["Story", "Output Case"], how="inner")
        if merged.empty:
            return pd.DataFrame(columns=["Story", "LoadCase", "Direction", "Acceleration", "MaxAcceleration", "MinAcceleration"])

        # Convert to g (divide by 9810)
        merged["MaxAcceleration"] = merged["MaxAcceleration"] / 9810
        merged["MinAcceleration"] = merged["MinAcceleration"] / 9810

        # Calculate absolute maximum
        merged["Acceleration"] = merged[["MaxAcceleration", "MinAcceleration"]].abs().max(axis=1)

        # Round values
        merged["Acceleration"] = merged["Acceleration"].round(3)
        merged["MaxAcceleration"] = merged["MaxAcceleration"].round(3)
        merged["MinAcceleration"] = merged["MinAcceleration"].round(3)
        merged["Direction"] = direction

        return merged.rename(columns={"Output Case": "LoadCase"})[["Story", "LoadCase", "Direction", "Acceleration", "MaxAcceleration", "MinAcceleration"]]


    @staticmethod
    def process_joint_displacements(
        df: pd.DataFrame, load_cases: List[str], stories: List[str], direction_column: str
    ) -> pd.DataFrame:
        """Process joint displacement data for a specific translational direction."""
        if direction_column not in df.columns:
            return pd.DataFrame(columns=[
                "Story",
                "LoadCase",
                "Direction",
                "Displacement",
                "MaxDisplacement",
                "MinDisplacement",
            ])

        working = df[["Story", "Output Case", direction_column]].copy()
        working.rename(columns={"Output Case": "LoadCase", direction_column: "Value"}, inplace=True)
        working["Value"] = pd.to_numeric(working["Value"], errors="coerce")
        working = working.dropna(subset=["Value"])

        if working.empty:
            return pd.DataFrame(columns=[
                "Story",
                "LoadCase",
                "Direction",
                "Displacement",
                "MaxDisplacement",
                "MinDisplacement",
            ])

        grouped = working.groupby(["Story", "LoadCase"])["Value"].agg(["max", "min"])
        grouped = grouped.reset_index()
        grouped["Displacement"] = grouped[["max", "min"]].abs().max(axis=1)
        grouped["Direction"] = direction_column.upper()
        grouped["MaxDisplacement"] = grouped["max"].round(4)
        grouped["MinDisplacement"] = grouped["min"].round(4)
        grouped["Displacement"] = grouped["Displacement"].round(4)

        return grouped[
            ["Story", "LoadCase", "Direction", "Displacement", "MaxDisplacement", "MinDisplacement"]
        ]

    @staticmethod
    def process_story_forces(
        df: pd.DataFrame, load_cases: List[str], stories: List[str], direction: str
    ) -> pd.DataFrame:
        """Process story shear force data for a specific direction - vectorized.

        Args:
            df: Raw force data DataFrame
            load_cases: List of load case names
            stories: List of story names (top-down order)
            direction: 'VX' or 'VY'

        Returns:
            Processed DataFrame with force values
        """
        if df.empty or direction not in df.columns:
            return pd.DataFrame(columns=["Story", "LoadCase", "Direction", "Location", "Force", "MaxForce", "MinForce"])

        # Filter for Bottom location only
        df_bottom = df[df["Location"] == "Bottom"].copy()
        if df_bottom.empty:
            return pd.DataFrame(columns=["Story", "LoadCase", "Direction", "Location", "Force", "MaxForce", "MinForce"])

        # Convert direction column to numeric
        df_bottom[direction] = pd.to_numeric(df_bottom[direction], errors="coerce")
        df_bottom = df_bottom.dropna(subset=[direction])
        if df_bottom.empty:
            return pd.DataFrame(columns=["Story", "LoadCase", "Direction", "Location", "Force", "MaxForce", "MinForce"])

        # Group by Story, Output Case and aggregate
        grouped = df_bottom.groupby(["Story", "Output Case"], as_index=False).agg({
            direction: ["max", "min", lambda x: x.abs().max()]
        })

        # Flatten multi-level column names
        grouped.columns = ["Story", "LoadCase", "MaxForce", "MinForce", "Force"]

        # Round values
        grouped["Force"] = grouped["Force"].round(0)
        grouped["MaxForce"] = grouped["MaxForce"].round(0)
        grouped["MinForce"] = grouped["MinForce"].round(0)
        grouped["Direction"] = direction
        grouped["Location"] = "Bottom"

        return grouped[["Story", "LoadCase", "Direction", "Location", "Force", "MaxForce", "MinForce"]]

    @staticmethod
    def process_pier_forces(
        df: pd.DataFrame, load_cases: List[str], stories: List[str], piers: List[str], direction: str
    ) -> pd.DataFrame:
        """Process pier force data for a specific direction - vectorized.

        Args:
            df: Raw pier force data DataFrame (row-based format)
            load_cases: List of load case names
            stories: List of story names (top-down order)
            piers: List of unique pier names
            direction: 'V2' or 'V3'

        Returns:
            Processed DataFrame with columns: [Story, Pier, LoadCase, Direction, Location, Force, MaxForce, MinForce]
        """
        if df.empty or direction not in df.columns:
            return pd.DataFrame(columns=["Story", "Pier", "LoadCase", "Direction", "Location", "Force", "MaxForce", "MinForce"])

        # Filter for Bottom location only (user requirement)
        df_bottom = df[df["Location"] == "Bottom"].copy()
        if df_bottom.empty:
            return pd.DataFrame(columns=["Story", "Pier", "LoadCase", "Direction", "Location", "Force", "MaxForce", "MinForce"])

        # Convert direction column to numeric once
        df_bottom[direction] = pd.to_numeric(df_bottom[direction], errors="coerce")

        # Filter to valid values
        df_bottom = df_bottom.dropna(subset=[direction])
        if df_bottom.empty:
            return pd.DataFrame(columns=["Story", "Pier", "LoadCase", "Direction", "Location", "Force", "MaxForce", "MinForce"])

        # Group by Story, Pier, Output Case and aggregate
        grouped = df_bottom.groupby(["Story", "Pier", "Output Case"], as_index=False).agg({
            direction: ["max", "min", lambda x: x.abs().max()]
        })

        # Flatten multi-level column names
        grouped.columns = ["Story", "Pier", "LoadCase", "MaxForce", "MinForce", "Force"]

        # Round values
        grouped["Force"] = grouped["Force"].round(1)
        grouped["MaxForce"] = grouped["MaxForce"].round(1)
        grouped["MinForce"] = grouped["MinForce"].round(1)
        grouped["Direction"] = direction
        grouped["Location"] = "Bottom"

        return grouped[["Story", "Pier", "LoadCase", "Direction", "Location", "Force", "MaxForce", "MinForce"]]

    @staticmethod
    def process_column_forces(
        df: pd.DataFrame, load_cases: List[str], stories: List[str], columns: List[str], direction: str
    ) -> pd.DataFrame:
        """Process column force data for a specific direction (vectorized).

        Args:
            df: Raw column force data DataFrame (row-based format)
            load_cases: List of load case names
            stories: List of story names (top-down order)
            columns: List of unique column names
            direction: 'V2' or 'V3'

        Returns:
            Processed DataFrame with columns: [Story, Column, UniqueName, LoadCase, Direction, Location, Force, MaxForce, MinForce]
        """
        if df.empty or direction not in df.columns:
            return pd.DataFrame(columns=["Story", "Column", "UniqueName", "LoadCase", "Direction", "Location", "Force", "MaxForce", "MinForce"])

        # Convert direction column to numeric once
        df = df.copy()
        df[direction] = pd.to_numeric(df[direction], errors="coerce")

        # Filter to valid values
        df = df.dropna(subset=[direction])
        if df.empty:
            return pd.DataFrame(columns=["Story", "Column", "UniqueName", "LoadCase", "Direction", "Location", "Force", "MaxForce", "MinForce"])

        # Build aggregation dict - only include Location if it exists
        agg_dict = {direction: ["max", "min", lambda x: x.abs().max()]}
        has_location = "Location" in df.columns

        if has_location:
            agg_dict["Location"] = "first"

        # Group by Story, Column, Unique Name, Output Case and aggregate
        grouped = df.groupby(["Story", "Column", "Unique Name", "Output Case"], as_index=False).agg(agg_dict)

        # Flatten multi-level column names
        if has_location:
            grouped.columns = ["Story", "Column", "UniqueName", "LoadCase", "MaxForce", "MinForce", "Force", "Location"]
        else:
            grouped.columns = ["Story", "Column", "UniqueName", "LoadCase", "MaxForce", "MinForce", "Force"]
            grouped["Location"] = None

        # Round values
        grouped["Force"] = grouped["Force"].round(1)
        grouped["MaxForce"] = grouped["MaxForce"].round(1)
        grouped["MinForce"] = grouped["MinForce"].round(1)
        grouped["Direction"] = direction

        return grouped[["Story", "Column", "UniqueName", "LoadCase", "Direction", "Location", "Force", "MaxForce", "MinForce"]]

    @staticmethod
    def process_column_axials(
        df: pd.DataFrame, load_cases: List[str], stories: List[str], columns: List[str]
    ) -> pd.DataFrame:
        """Process column axial force data (min and max P values) - vectorized.

        Args:
            df: Raw column force data DataFrame (row-based format)
            load_cases: List of load case names
            stories: List of story names (top-down order)
            columns: List of unique column names

        Returns:
            Processed DataFrame with columns: [Story, Column, UniqueName, LoadCase, Location, MinAxial, MaxAxial]

        Note:
            MinAxial = minimum P (most compression, most negative value)
            MaxAxial = maximum P (most tension, most positive value)
        """
        if df.empty or "P" not in df.columns:
            return pd.DataFrame(columns=["Story", "Column", "UniqueName", "LoadCase", "Location", "MinAxial", "MaxAxial"])

        # Convert P column to numeric once
        df = df.copy()
        df["P"] = pd.to_numeric(df["P"], errors="coerce")

        # Filter to valid values
        df = df.dropna(subset=["P"])
        if df.empty:
            return pd.DataFrame(columns=["Story", "Column", "UniqueName", "LoadCase", "Location", "MinAxial", "MaxAxial"])

        # Build aggregation dict - only include Location if it exists
        agg_dict = {"P": ["min", "max"]}
        has_location = "Location" in df.columns

        if has_location:
            agg_dict["Location"] = "first"

        # Group by Story, Column, Unique Name, Output Case and aggregate
        grouped = df.groupby(["Story", "Column", "Unique Name", "Output Case"], as_index=False).agg(agg_dict)

        # Flatten multi-level column names
        if has_location:
            grouped.columns = ["Story", "Column", "UniqueName", "LoadCase", "MinAxial", "MaxAxial", "Location"]
        else:
            grouped.columns = ["Story", "Column", "UniqueName", "LoadCase", "MinAxial", "MaxAxial"]
            grouped["Location"] = None

        # Round values
        grouped["MinAxial"] = grouped["MinAxial"].round(1)
        grouped["MaxAxial"] = grouped["MaxAxial"].round(1)

        return grouped[["Story", "Column", "UniqueName", "LoadCase", "Location", "MinAxial", "MaxAxial"]]

    @staticmethod
    def process_column_rotations(
        df: pd.DataFrame, load_cases: List[str], stories: List[str], columns: List[str], direction: str
    ) -> pd.DataFrame:
        """Process column rotation data for a specific direction (R2 or R3) - vectorized.

        Args:
            df: Raw fiber hinge state data DataFrame (row-based format)
            load_cases: List of load case names
            stories: List of story names (top-down order)
            columns: List of unique column identifiers (Frame/Wall)
            direction: 'R2' or 'R3'

        Returns:
            Processed DataFrame with columns: [Story, Column, Element, LoadCase, Direction, Rotation, MaxRotation, MinRotation]

        Note:
            Rotations are stored in radians. They will be converted to percentage (× 100) in the cache.
        """
        if df.empty or direction not in df.columns:
            return pd.DataFrame(columns=["Story", "Column", "Element", "LoadCase", "Direction", "Rotation", "MaxRotation", "MinRotation"])

        # Convert direction column to numeric once
        df = df.copy()
        df[direction] = pd.to_numeric(df[direction], errors="coerce")

        # Filter to valid values
        df = df.dropna(subset=[direction])
        if df.empty:
            return pd.DataFrame(columns=["Story", "Column", "Element", "LoadCase", "Direction", "Rotation", "MaxRotation", "MinRotation"])

        # Group by Story, Frame/Wall, Unique Name, Output Case and aggregate
        grouped = df.groupby(["Story", "Frame/Wall", "Unique Name", "Output Case"], as_index=False).agg({
            direction: ["max", "min", lambda x: x.abs().max()]
        })

        # Flatten multi-level column names
        grouped.columns = ["Story", "Column", "Element", "LoadCase", "MaxRotation", "MinRotation", "Rotation"]

        # Round values (keep precision for radians)
        grouped["Rotation"] = grouped["Rotation"].round(6)
        grouped["MaxRotation"] = grouped["MaxRotation"].round(6)
        grouped["MinRotation"] = grouped["MinRotation"].round(6)
        grouped["Direction"] = direction

        return grouped[["Story", "Column", "Element", "LoadCase", "Direction", "Rotation", "MaxRotation", "MinRotation"]]

    @staticmethod
    def process_beam_rotations(
        df: pd.DataFrame, load_cases: List[str], stories: List[str], beams: List[str]
    ) -> pd.DataFrame:
        """Process beam R3 plastic rotation data for database import - vectorized.

        Args:
            df: Raw hinge state data DataFrame (row-based format)
            load_cases: List of load case names
            stories: List of story names (preserves source order)
            beams: List of unique beam identifiers (Frame/Wall, preserves source order)

        Returns:
            Long-format DataFrame for DB import with columns:
            [Story, Beam, Element, StepType, Hinge, GeneratedHinge, RelDist, LoadCase, R3Plastic]

            Preserves ALL rows from source Excel (both Max/Min step types, both Rel Dist 0/1).

        Note:
            R3 Plastic rotations are stored in radians.
        """
        if df.empty or "R3 Plastic" not in df.columns:
            return pd.DataFrame()

        df = df.copy()

        # Convert R3 Plastic to numeric
        df["R3 Plastic"] = pd.to_numeric(df["R3 Plastic"], errors="coerce")

        # Filter out invalid values
        df = df.dropna(subset=["R3 Plastic"])
        if df.empty:
            return pd.DataFrame()

        # Vectorized column selection and rename
        result_df = pd.DataFrame({
            "Story": df["Story"].values,
            "Beam": df["Frame/Wall"].values,
            "Element": df["Unique Name"].values,
            "StepType": df["Step Type"].values if "Step Type" in df.columns else "",
            "Hinge": df["Hinge"].values if "Hinge" in df.columns else "",
            "GeneratedHinge": df["Generated Hinge"].values if "Generated Hinge" in df.columns else "",
            "RelDist": df["Rel Dist"].values if "Rel Dist" in df.columns else 0.0,
            "LoadCase": df["Output Case"].values,
            "R3Plastic": df["R3 Plastic"].values,
        })

        return result_df

    @staticmethod
    def process_beam_rotations_wide(
        df: pd.DataFrame, load_cases: List[str], stories: List[str], beams: List[str]
    ) -> pd.DataFrame:
        """Process beam R3 plastic rotation data to wide format for export.

        Matches old ETDB_Functions.get_beams_plastic_hinges format exactly.

        Args:
            df: Raw hinge state data DataFrame (row-based format)
            load_cases: List of load case names
            stories: List of story names (preserves source order)
            beams: List of unique beam identifiers (Frame/Wall, preserves source order)

        Returns:
            Wide-format DataFrame preserving source Excel row structure:
            [Story, Frame/Wall, Unique Name, Step Type, Hinge, Hinge ID, Rel Dist, <LC1>, <LC2>, ..., Avg, Max, Min]

        Note:
            R3 Plastic rotations are stored in radians. Each source row is preserved.
        """
        if df.empty or "R3 Plastic" not in df.columns:
            return pd.DataFrame()

        df = df.copy()

        # Use first load case to get the unique row structure (like old script uses TH01)
        first_case = load_cases[0] if load_cases else None
        if not first_case:
            return pd.DataFrame()

        df_template = df[df["Output Case"] == first_case].copy().reset_index(drop=True)
        if df_template.empty:
            return pd.DataFrame()

        # Build output DataFrame with metadata columns preserving source order
        result_df = pd.DataFrame()
        result_df["Story"] = df_template["Story"].values
        result_df["Frame/Wall"] = df_template["Frame/Wall"].values
        result_df["Unique Name"] = df_template["Unique Name"].values
        result_df["Step Type"] = df_template["Step Type"].values
        result_df["Hinge"] = df_template["Hinge"].values
        result_df["Hinge ID"] = df_template["Generated Hinge"].values
        result_df["Rel Dist"] = df_template["Rel Dist"].values

        # Add a column for each load case with the R3 Plastic values
        for case in load_cases:
            case_df = df[df["Output Case"] == case].reset_index(drop=True)
            if case_df.empty or len(case_df) != len(result_df):
                result_df[case] = None
            else:
                result_df[case] = pd.to_numeric(case_df["R3 Plastic"], errors="coerce").values

        # Add summary columns (Avg, Max, Min) across load case columns
        lc_cols = [c for c in result_df.columns if c in load_cases]
        if lc_cols:
            result_df["Avg"] = result_df[lc_cols].mean(axis=1)
            result_df["Max"] = result_df[lc_cols].max(axis=1)
            result_df["Min"] = result_df[lc_cols].min(axis=1)

        return result_df

    @staticmethod
    def calculate_statistics(df: pd.DataFrame, value_column: str) -> Dict[str, float]:
        """Calculate statistics across load cases.

        Args:
            df: DataFrame with processed results
            value_column: Name of the column to calculate statistics for

        Returns:
            Dictionary with Avg, Max, Min values
        """
        if value_column not in df.columns or df.empty:
            return {"Avg": 0.0, "Max": 0.0, "Min": 0.0}

        values = df[value_column]
        return {
            "Avg": round(values.mean(), 4),
            "Max": round(values.max(), 4),
            "Min": round(values.min(), 4),
        }

    @staticmethod
    def create_envelope_by_story(
        df: pd.DataFrame, stories: List[str], value_column: str
    ) -> pd.DataFrame:
        """Create envelope values grouped by story.

        Args:
            df: DataFrame with processed results
            stories: List of story names in order
            value_column: Column to create envelope from

        Returns:
            DataFrame with stories and envelope values (Avg, Max, Min)
        """
        envelope_data = []

        for story in stories:
            story_data = df[df["Story"] == story]

            if not story_data.empty:
                stats = ResultProcessor.calculate_statistics(
                    story_data, value_column
                )
                envelope_data.append(
                    {
                        "Story": story,
                        "Avg": stats["Avg"],
                        "Max": stats["Max"],
                        "Min": stats["Min"],
                    }
                )

        return pd.DataFrame(envelope_data)

    @staticmethod
    def process_quad_rotations(
        df: pd.DataFrame, load_cases: List[str], stories: List[str], piers: List[str]
    ) -> pd.DataFrame:
        """Process quad strain gauge rotation data.

        Args:
            df: Raw quad rotation data DataFrame (with columns: Story, Name, PropertyName, Output Case, StepType, Rotation, etc.)
            load_cases: List of load case names
            stories: List of story names
            piers: List of pier names (from PropertyName column)

        Returns:
            Processed DataFrame with columns: [Story, Pier, QuadName, LoadCase, Rotation, MaxRotation, MinRotation]

        Note:
            Data has Max and Min step types for each load case.
            Rotations are in radians and will be converted to percentage (multiply by 100) later.
        """
        if df.empty:
            return pd.DataFrame(columns=["Story", "Pier", "QuadName", "LoadCase", "Rotation", "MaxRotation", "MinRotation"])

        # Only keep Max/Min step types needed for envelopes
        df_filtered = df[df["StepType"].isin(["Max", "Min"])].copy()
        if df_filtered.empty:
            return pd.DataFrame(columns=["Story", "Pier", "QuadName", "LoadCase", "Rotation", "MaxRotation", "MinRotation"])

        # Pivot Max/Min into columns to avoid nested loops
        pivot = (
            df_filtered.pivot_table(
                index=["Story", "PropertyName", "Output Case", "Name"],
                columns="StepType",
                values="Rotation",
                aggfunc="first",
            )
            .reset_index()
            .rename(columns={"PropertyName": "Pier", "Output Case": "LoadCase", "Name": "QuadName"})
        )

        # Drop rows missing either Max or Min
        pivot = pivot.dropna(subset=["Max", "Min"])
        if pivot.empty:
            return pd.DataFrame(columns=["Story", "Pier", "QuadName", "LoadCase", "Rotation", "MaxRotation", "MinRotation"])

        pivot["MaxRotation"] = pivot["Max"].round(6)
        pivot["MinRotation"] = pivot["Min"].round(6)
        pivot["Rotation"] = pivot[["MaxRotation", "MinRotation"]].abs().max(axis=1)

        return pivot[["Story", "Pier", "QuadName", "LoadCase", "Rotation", "MaxRotation", "MinRotation"]]
