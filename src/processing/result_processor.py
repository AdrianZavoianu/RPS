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
