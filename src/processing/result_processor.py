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
        """Process column axial force data (minimum P values).

        Args:
            df: Raw column force data DataFrame (row-based format)
            load_cases: List of load case names
            stories: List of story names (top-down order)
            columns: List of unique column names

        Returns:
            Processed DataFrame with columns: [Story, Column, UniqueNameList, LoadCase, Location, MinAxial]

        Note:
            Unlike shears which track both directions, axial forces only track the minimum (most compression) P value.
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

                            # Get P values (axial forces - negative = compression)
                            p_values = pd.to_numeric(filtered_unique["P"], errors="coerce").dropna()

                            if not p_values.empty:
                                # Minimum P (most compression - most negative value)
                                min_axial = p_values.min()

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
        """Process beam R3 plastic rotation data.

        Args:
            df: Raw hinge state data DataFrame (row-based format)
            load_cases: List of load case names
            stories: List of story names (top-down order)
            beams: List of unique beam identifiers (Frame/Wall)

        Returns:
            Processed DataFrame with columns: [Story, Beam, Element, Hinge, GeneratedHinge, RelDist, LoadCase, R3Plastic, MaxR3Plastic, MinR3Plastic]

        Note:
            R3 Plastic rotations are stored in radians. They will be converted to percentage (× 100) in the cache.
        """
        results = []

        for story in stories:
            for beam in beams:
                for case in load_cases:
                    # Filter data for this story, beam, and case
                    filtered = df.loc[
                        (df["Story"] == story)
                        & (df["Frame/Wall"] == beam)
                        & (df["Output Case"] == case)
                    ].copy()

                    if not filtered.empty and "R3 Plastic" in filtered.columns:
                        # Get unique element names (Unique Name column)
                        elements = filtered["Unique Name"].unique().tolist()

                        # Process each element
                        for element in elements:
                            filtered_element = filtered[filtered["Unique Name"] == element]

                            # Get R3 Plastic values
                            r3_values = pd.to_numeric(filtered_element["R3 Plastic"], errors="coerce").dropna()

                            if not r3_values.empty:
                                # Use absolute max rotation (similar to column rotations)
                                abs_max_r3 = r3_values.abs().max()
                                max_r3 = r3_values.max()
                                min_r3 = r3_values.min()

                                # Get hinge info from first row
                                first_row = filtered_element.iloc[0]
                                hinge = first_row.get("Hinge", "")
                                generated_hinge = first_row.get("Generated Hinge", "")
                                rel_dist = first_row.get("Rel Dist", 0.0)

                                results.append({
                                    "Story": story,
                                    "Beam": beam,
                                    "Element": element,
                                    "Hinge": hinge,
                                    "GeneratedHinge": generated_hinge,
                                    "RelDist": rel_dist,
                                    "LoadCase": case,
                                    "R3Plastic": round(abs_max_r3, 8),  # Keep precision for radians
                                    "MaxR3Plastic": round(max_r3, 8),
                                    "MinR3Plastic": round(min_r3, 8),
                                })

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
