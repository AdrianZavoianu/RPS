"""Pushover curve Excel parser - extracts displacement vs base shear curves."""

from typing import Dict, List, Tuple
import pandas as pd
from pathlib import Path
import re

from utils.pushover_utils import detect_direction


class PushoverCurveData:
    """Container for extracted pushover curve data."""

    def __init__(self, case_name: str, direction: str):
        self.case_name = case_name
        self.direction = direction
        self.step_numbers: List[int] = []
        self.displacements: List[float] = []
        self.base_shears: List[float] = []

    def add_point(self, step: int, displacement: float, shear: float):
        """Add a data point to the curve."""
        self.step_numbers.append(step)
        self.displacements.append(displacement)
        self.base_shears.append(shear)

    def __repr__(self):
        return f"<PushoverCurveData(case='{self.case_name}', dir='{self.direction}', points={len(self.step_numbers)})>"


class PushoverParser:
    """Parses pushover analysis Excel files to extract capacity curves."""

    def __init__(self, file_path: str | Path):
        self.file_path = Path(file_path)
        self.excel_file = pd.ExcelFile(file_path)

    def parse_curves(self, base_story: str) -> Dict[str, PushoverCurveData]:
        """
        Extract pushover curves from Excel file.

        Args:
            base_story: Base story name for extracting shear forces

        Returns:
            Dictionary mapping case names to PushoverCurveData objects
        """
        # Extract displacement data
        displacement_data = self._parse_displacements()

        # Extract base shear data
        shear_data = self._parse_base_shears(base_story)

        # Merge displacement and shear data
        curves = self._merge_data(displacement_data, shear_data)

        return curves

    def _parse_displacements(self) -> Dict[str, Tuple[List[int], List[float], str]]:
        """
        Parse Joint Displacements sheet.

        Returns:
            Dict mapping case name to (step_numbers, displacements, direction)
        """
        df = pd.read_excel(self.excel_file, sheet_name='Joint Displacements', header=1)
        df = df.drop(0)  # Drop units row

        results = {}

        # Group by Output Case
        for case_name, group in df.groupby('Output Case'):
            # Determine direction from case name using regex pattern
            direction = detect_direction(case_name)

            if direction == 'Unknown':
                continue  # Skip if direction unclear

            # Extract step numbers
            steps = group['Step Number'].tolist()

            # Handle displacement based on direction
            if direction == 'XY':
                # Bi-directional: compute resultant displacement from Ux and Uy
                ux = pd.to_numeric(group['Ux'], errors='coerce').tolist()
                uy = pd.to_numeric(group['Uy'], errors='coerce').tolist()

                # Compute resultant displacement: sqrt(Ux^2 + Uy^2)
                displacements = [(ux_val**2 + uy_val**2)**0.5 for ux_val, uy_val in zip(ux, uy)]
            elif direction == 'X':
                displacements = pd.to_numeric(group['Ux'], errors='coerce').tolist()
            elif direction == 'Y':
                displacements = pd.to_numeric(group['Uy'], errors='coerce').tolist()

            # Normalize displacements (zero initial value, then absolute)
            if displacements and len(displacements) > 0:
                initial = displacements[0]
                displacements = [abs(val - initial) for val in displacements]

            results[case_name] = (steps, displacements, direction)

        return results

    def _parse_base_shears(self, base_story: str) -> Dict[str, Tuple[List[int], List[float]]]:
        """
        Parse Story Forces sheet for base shears.

        Args:
            base_story: Story name to extract (typically foundation or first floor)

        Returns:
            Dict mapping case name to (step_numbers, base_shears)
        """
        df = pd.read_excel(self.excel_file, sheet_name='Story Forces', header=1)
        df = df.drop(0)  # Drop units row

        # Filter for base story at bottom location
        df = df[(df['Story'] == base_story) & (df['Location'] == 'Bottom')]

        results = {}

        # Group by Output Case
        for case_name, group in df.groupby('Output Case'):
            # Determine direction using regex pattern
            direction = detect_direction(case_name)

            if direction == 'Unknown':
                continue  # Skip if direction unclear

            # Extract step numbers
            steps = group['Step Number'].tolist()

            # Handle shear based on direction
            if direction == 'XY':
                # Bi-directional: compute resultant shear from VX and VY
                vx = pd.to_numeric(group['VX'], errors='coerce').abs().tolist()
                vy = pd.to_numeric(group['VY'], errors='coerce').abs().tolist()

                # Compute resultant shear: sqrt(VX^2 + VY^2)
                shears = [(vx_val**2 + vy_val**2)**0.5 for vx_val, vy_val in zip(vx, vy)]
            elif direction == 'X':
                shears = pd.to_numeric(group['VX'], errors='coerce').abs().tolist()
            elif direction == 'Y':
                shears = pd.to_numeric(group['VY'], errors='coerce').abs().tolist()

            results[case_name] = (steps, shears)

        return results

    def _merge_data(
        self,
        displacement_data: Dict[str, Tuple[List[int], List[float], str]],
        shear_data: Dict[str, Tuple[List[int], List[float]]]
    ) -> Dict[str, PushoverCurveData]:
        """
        Merge displacement and shear data into PushoverCurveData objects.

        Args:
            displacement_data: Dict from _parse_displacements
            shear_data: Dict from _parse_base_shears

        Returns:
            Dict mapping case names to PushoverCurveData objects
        """
        curves = {}

        for case_name, (disp_steps, displacements, direction) in displacement_data.items():
            if case_name not in shear_data:
                continue  # Skip if no matching shear data

            shear_steps, shears = shear_data[case_name]

            # Create curve object
            curve = PushoverCurveData(case_name, direction)

            # Match steps and add points
            for i, step in enumerate(disp_steps):
                if i < len(shears) and disp_steps[i] == shear_steps[i]:
                    curve.add_point(
                        step=int(step),
                        displacement=displacements[i],
                        shear=shears[i]
                    )

            curves[case_name] = curve

        return curves

    def get_available_stories(self) -> List[str]:
        """Get list of available story names from Story Forces sheet."""
        df = pd.read_excel(self.excel_file, sheet_name='Story Forces', header=1)
        df = df.drop(0)  # Drop units row
        stories = df['Story'].unique().tolist()
        # Sort stories (reverse order to show from top to bottom)
        return sorted(stories, reverse=True)
