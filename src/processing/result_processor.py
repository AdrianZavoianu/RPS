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
        """Process story drift data for a specific direction.

        Args:
            df: Raw drift data DataFrame
            load_cases: List of load case names
            stories: List of story names (top-down order)
            direction: 'X' or 'Y'

        Returns:
            Processed DataFrame with columns: [Story, LoadCase, Drift, MaxDrift, MinDrift]
        """
        results = []

        for story in stories:
            for case in load_cases:
                # Filter data for this story, case, and direction
                filtered = df.loc[
                    (df["Output Case"] == case)
                    & (df["Direction"] == direction)
                    & (df["Story"] == story)
                ]

                if not filtered.empty:
                    # Get drift values
                    drift_values = filtered["Drift"]
                    abs_max_drift = drift_values.abs().max()
                    max_drift = drift_values.max()
                    min_drift = drift_values.min()

                    results.append(
                        {
                            "Story": story,
                            "LoadCase": case,
                            "Direction": direction,
                            "Drift": round(abs_max_drift, 4),
                            "MaxDrift": round(max_drift, 4),
                            "MinDrift": round(min_drift, 4),
                        }
                    )

        return pd.DataFrame(results)

    @staticmethod
    def process_story_accelerations(
        df: pd.DataFrame, load_cases: List[str], stories: List[str], direction: str
    ) -> pd.DataFrame:
        """Process story acceleration data from 'Diaphragm Accelerations' sheet.

        Handles the format with separate Max/Min rows and Max UX/UY and Min UX/UY columns.

        Args:
            df: Raw diaphragm acceleration data DataFrame
            load_cases: List of load case names
            stories: List of story names (top-down order)
            direction: 'UX' or 'UY'

        Returns:
            Processed DataFrame with acceleration in g-units (converted from mm/sec²)
        """
        results = []

        # Column names for max and min values based on direction
        max_col = f'Max {direction}'
        min_col = f'Min {direction}'

        for story in stories:
            for case in load_cases:
                # Filter Max row for this story and case
                filtered_max = df.loc[
                    (df["Output Case"] == case)
                    & (df["Story"] == story)
                    & (df["Step Type"] == "Max")
                ]

                # Filter Min row for this story and case
                filtered_min = df.loc[
                    (df["Output Case"] == case)
                    & (df["Story"] == story)
                    & (df["Step Type"] == "Min")
                ]

                if not filtered_max.empty and not filtered_min.empty:
                    # Get the max value from Max row and convert to g (divide by 9810)
                    max_value = filtered_max[max_col].max() / 9810

                    # Get the min value from Min row and convert to g (divide by 9810)
                    min_value = filtered_min[min_col].min() / 9810

                    # Take the absolute maximum (matching old script logic)
                    abs_max_accel = max(abs(max_value), abs(min_value))

                    results.append(
                        {
                            "Story": story,
                            "LoadCase": case,
                            "Direction": direction,
                            "Acceleration": round(abs_max_accel, 3),
                            "MaxAcceleration": round(max_value, 3),
                            "MinAcceleration": round(min_value, 3),
                        }
                    )

        return pd.DataFrame(results)


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
        """Process story shear force data for a specific direction.

        Args:
            df: Raw force data DataFrame
            load_cases: List of load case names
            stories: List of story names (top-down order)
            direction: 'VX' or 'VY'

        Returns:
            Processed DataFrame with force values
        """
        results = []

        for story in stories:
            for case in load_cases:
                # Filter data for this story, case, direction, and bottom location
                filtered = df.loc[
                    (df["Output Case"] == case)
                    & (df["Story"] == story)
                    & (df["Location"] == "Bottom")
                ]

                if not filtered.empty:
                    # Get force values
                    force_values = filtered[direction]
                    abs_max_force = force_values.abs().max()
                    max_force = force_values.max()
                    min_force = force_values.min()

                    results.append(
                        {
                            "Story": story,
                            "LoadCase": case,
                            "Direction": direction,
                            "Location": "Bottom",
                            "Force": round(abs_max_force, 0),
                            "MaxForce": round(max_force, 0),
                            "MinForce": round(min_force, 0),
                        }
                    )

        return pd.DataFrame(results)

    @staticmethod
    def process_pier_forces(
        df: pd.DataFrame, load_cases: List[str], stories: List[str], piers: List[str], direction: str
    ) -> pd.DataFrame:
        """Process pier force data for a specific direction.

        Args:
            df: Raw pier force data DataFrame (row-based format)
            load_cases: List of load case names
            stories: List of story names (top-down order)
            piers: List of unique pier names
            direction: 'V2' or 'V3'

        Returns:
            Processed DataFrame with columns: [Story, Pier, LoadCase, Direction, Location, Force, MaxForce, MinForce]
        """
        results = []

        # Filter for Bottom location only (user requirement)
        df_bottom = df[df["Location"] == "Bottom"].copy()

        for story in stories:
            for pier in piers:
                for case in load_cases:
                    # Filter data for this story, pier, and case
                    filtered = df_bottom.loc[
                        (df_bottom["Story"] == story)
                        & (df_bottom["Pier"] == pier)
                        & (df_bottom["Output Case"] == case)
                    ]

                    if not filtered.empty and direction in filtered.columns:
                        # Get force values for this direction
                        force_values = pd.to_numeric(filtered[direction], errors="coerce").dropna()

                        if not force_values.empty:
                            abs_max_force = force_values.abs().max()
                            max_force = force_values.max()
                            min_force = force_values.min()

                            results.append(
                                {
                                    "Story": story,
                                    "Pier": pier,
                                    "LoadCase": case,
                                    "Direction": direction,
                                    "Location": "Bottom",
                                    "Force": round(abs_max_force, 1),
                                    "MaxForce": round(max_force, 1),
                                    "MinForce": round(min_force, 1),
                                }
                            )

        return pd.DataFrame(results)

    @staticmethod
    def process_column_forces(
        df: pd.DataFrame, load_cases: List[str], stories: List[str], columns: List[str], direction: str
    ) -> pd.DataFrame:
        """Process column force data for a specific direction.

        Args:
            df: Raw column force data DataFrame (row-based format)
            load_cases: List of load case names
            stories: List of story names (top-down order)
            columns: List of unique column names
            direction: 'V2' or 'V3'

        Returns:
            Processed DataFrame with columns: [Story, Column, UniqueNameList, LoadCase, Direction, Location, Force, MaxForce, MinForce]

        Note:
            Unlike walls/piers, columns have multiple unique names per column identifier.
            We process each unique name separately for detailed results.
        """
        results = []

        for story in stories:
            for col in columns:
                for case in load_cases:
                    # Filter data for this story, column, and case
                    filtered = df.loc[
                        (df["Story"] == story)
                        & (df["Column"] == col)
                        & (df["Output Case"] == case)
                    ].copy()

                    if not filtered.empty and direction in filtered.columns:
                        # Get unique column instances (Unique Name)
                        unique_names = filtered["Unique Name"].unique().tolist()

                        # Process each unique column instance
                        for unique_name in unique_names:
                            filtered_unique = filtered[filtered["Unique Name"] == unique_name]

                            # Get force values for this direction
                            force_values = pd.to_numeric(filtered_unique[direction], errors="coerce").dropna()

                            if not force_values.empty:
                                abs_max_force = force_values.abs().max()
                                max_force = force_values.max()
                                min_force = force_values.min()

                                # Determine location (typically 'Top' or 'Bottom')
                                location = filtered_unique["Location"].iloc[0] if "Location" in filtered_unique.columns else None

                                results.append(
                                    {
                                        "Story": story,
                                        "Column": col,
                                        "UniqueName": unique_name,
                                        "LoadCase": case,
                                        "Direction": direction,
                                        "Location": location,
                                        "Force": round(abs_max_force, 1),
                                        "MaxForce": round(max_force, 1),
                                        "MinForce": round(min_force, 1),
                                    }
                                )

        return pd.DataFrame(results)

    @staticmethod
    def process_column_axials(
        df: pd.DataFrame, load_cases: List[str], stories: List[str], columns: List[str]
    ) -> pd.DataFrame:
        """Process column axial force data (min and max P values).

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
        results = []

        for story in stories:
            for col in columns:
                for case in load_cases:
                    # Filter data for this story, column, and case
                    filtered = df.loc[
                        (df["Story"] == story)
                        & (df["Column"] == col)
                        & (df["Output Case"] == case)
                    ].copy()

                    if not filtered.empty and "P" in filtered.columns:
                        # Get unique column instances (Unique Name)
                        unique_names = filtered["Unique Name"].unique().tolist()

                        # Process each unique column instance
                        for unique_name in unique_names:
                            filtered_unique = filtered[filtered["Unique Name"] == unique_name]

                            # Get P values (axial forces - negative = compression, positive = tension)
                            p_values = pd.to_numeric(filtered_unique["P"], errors="coerce").dropna()

                            if not p_values.empty:
                                # Minimum P (most compression - most negative value)
                                min_axial = p_values.min()
                                # Maximum P (most tension - most positive value)
                                max_axial = p_values.max()

                                # Determine location (typically 'Top' or 'Bottom')
                                location = filtered_unique["Location"].iloc[0] if "Location" in filtered_unique.columns else None

                                results.append(
                                    {
                                        "Story": story,
                                        "Column": col,
                                        "UniqueName": unique_name,
                                        "LoadCase": case,
                                        "Location": location,
                                        "MinAxial": round(min_axial, 1),
                                        "MaxAxial": round(max_axial, 1),
                                    }
                                )

        return pd.DataFrame(results)

    @staticmethod
    def process_column_rotations(
        df: pd.DataFrame, load_cases: List[str], stories: List[str], columns: List[str], direction: str
    ) -> pd.DataFrame:
        """Process column rotation data for a specific direction (R2 or R3).

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
        results = []

        for story in stories:
            for col in columns:
                for case in load_cases:
                    # Filter data for this story, column, and case
                    filtered = df.loc[
                        (df["Story"] == story)
                        & (df["Frame/Wall"] == col)
                        & (df["Output Case"] == case)
                    ].copy()

                    if not filtered.empty and direction in filtered.columns:
                        # Get element identifiers (Unique Name column)
                        elements = filtered["Unique Name"].unique().tolist()

                        # Process each element
                        for element in elements:
                            filtered_element = filtered[filtered["Unique Name"] == element]

                            # Get rotation values for this direction
                            rotation_values = pd.to_numeric(filtered_element[direction], errors="coerce").dropna()

                            if not rotation_values.empty:
                                # Use absolute max rotation (similar to column forces)
                                abs_max_rotation = rotation_values.abs().max()
                                max_rotation = rotation_values.max()
                                min_rotation = rotation_values.min()

                                results.append(
                                    {
                                        "Story": story,
                                        "Column": col,
                                        "Element": element,
                                        "LoadCase": case,
                                        "Direction": direction,
                                        "Rotation": round(abs_max_rotation, 6),  # Keep precision for radians
                                        "MaxRotation": round(max_rotation, 6),
                                        "MinRotation": round(min_rotation, 6),
                                    }
                                )

        return pd.DataFrame(results)

    @staticmethod
    def process_beam_rotations(
        df: pd.DataFrame, load_cases: List[str], stories: List[str], beams: List[str]
    ) -> pd.DataFrame:
        """Process beam R3 plastic rotation data for database import.

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

        # Build long-format output preserving source order
        results = []
        for idx, row in df.iterrows():
            r3_val = pd.to_numeric(row.get("R3 Plastic"), errors="coerce")
            if pd.isna(r3_val):
                continue

            results.append({
                "Story": row["Story"],
                "Beam": row["Frame/Wall"],
                "Element": row["Unique Name"],
                "StepType": row.get("Step Type", ""),
                "Hinge": row.get("Hinge", ""),
                "GeneratedHinge": row.get("Generated Hinge", ""),
                "RelDist": row.get("Rel Dist", 0.0),
                "LoadCase": row["Output Case"],
                "R3Plastic": r3_val,
            })

        return pd.DataFrame(results)

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
