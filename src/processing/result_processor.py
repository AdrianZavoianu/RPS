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
        """Process story acceleration data for a specific direction.

        Args:
            df: Raw acceleration data DataFrame
            load_cases: List of load case names
            stories: List of story names (top-down order)
            direction: 'UX' or 'UY'

        Returns:
            Processed DataFrame with acceleration in g-units
        """
        results = []

        for story in stories:
            for case in load_cases:
                # Filter data for this story and case
                filtered = df.loc[
                    (df["Output Case"] == case) & (df["Story"] == story)
                ]

                if not filtered.empty:
                    # Get acceleration values and convert to g-units (divide by 9810)
                    accel_values = filtered[direction] / 9810
                    abs_max_accel = accel_values.abs().max()
                    max_accel = accel_values.max()
                    min_accel = accel_values.min()

                    results.append(
                        {
                            "Story": story,
                            "LoadCase": case,
                            "Direction": direction,
                            "Acceleration": round(abs_max_accel, 3),
                            "MaxAcceleration": round(max_accel, 3),
                            "MinAcceleration": round(min_accel, 3),
                        }
                    )

        return pd.DataFrame(results)


    @staticmethod
    def process_joint_displacements(
        df: pd.DataFrame, load_cases: List[str], stories: List[str], direction_column: str
    ) -> pd.DataFrame:
        """Process joint displacement data for a specific translational direction."""
        results = []

        if direction_column not in df.columns:
            return pd.DataFrame(results)

        for story in stories:
            story_df = df[df["Story"] == story]
            if story_df.empty:
                continue

            for case in load_cases:
                filtered = story_df[story_df["Output Case"] == case]
                if filtered.empty:
                    continue

                values = pd.to_numeric(filtered[direction_column], errors="coerce").dropna()
                if values.empty:
                    continue

                max_val = values.max()
                min_val = values.min()
                abs_max = values.abs().max()

                results.append({
                    "Story": story,
                    "LoadCase": case,
                    "Direction": direction_column.upper(),
                    "Displacement": round(abs_max, 4),
                    "MaxDisplacement": round(max_val, 4),
                    "MinDisplacement": round(min_val, 4),
                })

        return pd.DataFrame(results)

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
        results = []

        for story in stories:
            for pier in piers:
                for case in load_cases:
                    # Filter data for this story, pier (PropertyName), and case
                    filtered = df.loc[
                        (df["Story"] == story)
                        & (df["PropertyName"] == pier)
                        & (df["Output Case"] == case)
                    ]

                    if not filtered.empty:
                        # Get Max and Min step type rows
                        max_row = filtered[filtered["StepType"] == "Max"]
                        min_row = filtered[filtered["StepType"] == "Min"]

                        if not max_row.empty and not min_row.empty:
                            # Extract rotation values
                            max_rotation = max_row["Rotation"].values[0]
                            min_rotation = min_row["Rotation"].values[0]

                            # Get quad name from Name column
                            quad_name = max_row["Name"].values[0] if "Name" in max_row.columns else None

                            # Compute absolute max rotation
                            abs_max_rotation = max(abs(max_rotation), abs(min_rotation))

                            results.append(
                                {
                                    "Story": story,
                                    "Pier": pier,
                                    "QuadName": quad_name,
                                    "LoadCase": case,
                                    "Rotation": round(abs_max_rotation, 6),  # 6 decimals for radians
                                    "MaxRotation": round(max_rotation, 6),
                                    "MinRotation": round(min_rotation, 6),
                                }
                            )

        return pd.DataFrame(results)
