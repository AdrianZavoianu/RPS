"""
Script to create minimal golden fixtures for testing.

Run this script to regenerate test fixtures:
    pipenv run python tests/resources/create_fixtures.py

Creates minimal Excel files that mimic ETABS/SAP2000 output structure.
"""

import pandas as pd
from pathlib import Path

RESOURCES = Path(__file__).parent


def create_nltha_fixture():
    """Create minimal NLTHA result file."""
    output_path = RESOURCES / "nltha"
    output_path.mkdir(exist_ok=True)

    with pd.ExcelWriter(output_path / "sample_des.xlsx", engine='openpyxl') as writer:
        # Story Drifts sheet
        story_drifts = pd.DataFrame({
            'Story': ['Text', 'Level 3', 'Level 2', 'Level 1', 'Level 3', 'Level 2', 'Level 1'],
            'Output Case': ['Text', 'DES_X1', 'DES_X1', 'DES_X1', 'DES_X2', 'DES_X2', 'DES_X2'],
            'Case Type': ['Text', 'LinRespSpec', 'LinRespSpec', 'LinRespSpec', 'LinRespSpec', 'LinRespSpec', 'LinRespSpec'],
            'Step Type': ['Text', 'Max', 'Max', 'Max', 'Max', 'Max', 'Max'],
            'Direction': ['Text', 'X', 'X', 'X', 'X', 'X', 'X'],
            'Drift': ['Unitless', 0.0025, 0.0030, 0.0020, 0.0028, 0.0032, 0.0022],
        })
        story_drifts.to_excel(writer, sheet_name='Story Drifts', index=False)

        # Story Forces sheet
        story_forces = pd.DataFrame({
            'Story': ['Text', 'Level 3', 'Level 2', 'Level 1', 'Level 3', 'Level 2', 'Level 1'],
            'Output Case': ['Text', 'DES_X1', 'DES_X1', 'DES_X1', 'DES_X2', 'DES_X2', 'DES_X2'],
            'Case Type': ['Text', 'LinRespSpec', 'LinRespSpec', 'LinRespSpec', 'LinRespSpec', 'LinRespSpec', 'LinRespSpec'],
            'Step Type': ['Text', 'Max', 'Max', 'Max', 'Max', 'Max', 'Max'],
            'Location': ['Text', 'Bottom', 'Bottom', 'Bottom', 'Bottom', 'Bottom', 'Bottom'],
            'VX': ['kN', 500, 800, 1000, 520, 830, 1050],
            'VY': ['kN', 100, 150, 200, 110, 160, 210],
        })
        story_forces.to_excel(writer, sheet_name='Story Forces', index=False)

        # Pier Forces sheet
        pier_forces = pd.DataFrame({
            'Story': ['Text', 'Level 2', 'Level 1', 'Level 2', 'Level 1'],
            'Pier': ['Text', 'P1', 'P1', 'P2', 'P2'],
            'Output Case': ['Text', 'DES_X1', 'DES_X1', 'DES_X1', 'DES_X1'],
            'Step Type': ['Text', 'Max', 'Max', 'Max', 'Max'],
            'Location': ['Text', 'Bottom', 'Bottom', 'Bottom', 'Bottom'],
            'V2': ['kN', 250, 300, 180, 220],
            'V3': ['kN', 50, 60, 40, 45],
        })
        pier_forces.to_excel(writer, sheet_name='Pier Forces', index=False)

    print(f"Created: {output_path / 'sample_des.xlsx'}")


def create_pushover_fixture():
    """Create minimal Pushover result file."""
    output_path = RESOURCES / "pushover"
    output_path.mkdir(exist_ok=True)

    with pd.ExcelWriter(output_path / "sample_push.xlsx", engine='openpyxl') as writer:
        # Pier Forces sheet (pushover)
        pier_forces = pd.DataFrame({
            'Story': ['Text', 'Level 2', 'Level 1', 'Level 2', 'Level 1', 'Level 2', 'Level 1'],
            'Pier': ['Text', 'P1', 'P1', 'P1', 'P1', 'P2', 'P2'],
            'Output Case': ['Text', 'Push_X+', 'Push_X+', 'Push_X-', 'Push_X-', 'Push_X+', 'Push_X+'],
            'Step Type': ['Text', 'Max', 'Max', 'Min', 'Min', 'Max', 'Max'],
            'Location': ['Text', 'Bottom', 'Bottom', 'Bottom', 'Bottom', 'Bottom', 'Bottom'],
            'V2': ['kN', 350, 420, -340, -410, 280, 330],
            'V3': ['kN', 70, 85, -65, -80, 55, 65],
        })
        pier_forces.to_excel(writer, sheet_name='Pier Forces', index=False)

        # Joint Displacements sheet (for capacity curves)
        joint_displacements = pd.DataFrame({
            'Joint': ['Text', '1', '1', '1', '1', '1'],
            'Output Case': ['Text', 'Push_X+', 'Push_X+', 'Push_X+', 'Push_X+', 'Push_X+'],
            'Step Type': ['Text', 'Step 0', 'Step 1', 'Step 2', 'Step 3', 'Step 4'],
            'Step Num': ['', 0, 1, 2, 3, 4],
            'U1': ['mm', 0, 10, 25, 45, 70],
            'U2': ['mm', 0, 0.5, 1.2, 2.1, 3.5],
            'U3': ['mm', 0, 0, 0, 0, 0],
        })
        joint_displacements.to_excel(writer, sheet_name='Joint Displacements', index=False)

        # Story Forces sheet (for base shear)
        story_forces = pd.DataFrame({
            'Story': ['Text', 'Base', 'Base', 'Base', 'Base', 'Base'],
            'Output Case': ['Text', 'Push_X+', 'Push_X+', 'Push_X+', 'Push_X+', 'Push_X+'],
            'Step Type': ['Text', 'Step 0', 'Step 1', 'Step 2', 'Step 3', 'Step 4'],
            'Step Num': ['', 0, 1, 2, 3, 4],
            'Location': ['Text', 'Bottom', 'Bottom', 'Bottom', 'Bottom', 'Bottom'],
            'VX': ['kN', 0, 500, 1200, 2100, 2800],
            'VY': ['kN', 0, 10, 25, 45, 60],
        })
        story_forces.to_excel(writer, sheet_name='Story Forces', index=False)

    print(f"Created: {output_path / 'sample_push.xlsx'}")


def create_expected_outputs():
    """Create expected output JSON files."""
    import json

    # NLTHA expected
    nltha_expected = RESOURCES / "nltha" / "expected"
    nltha_expected.mkdir(exist_ok=True)

    story_drifts_expected = {
        "shape": [6, 6],
        "columns": ["Story", "Output Case", "Case Type", "Step Type", "Direction", "Drift"],
        "stories": ["Level 3", "Level 2", "Level 1"],
        "load_cases": ["DES_X1", "DES_X2"],
        "row_count": 6
    }
    with open(nltha_expected / "story_drifts.json", "w") as f:
        json.dump(story_drifts_expected, f, indent=2)

    # Pushover expected
    push_expected = RESOURCES / "pushover" / "expected"
    push_expected.mkdir(exist_ok=True)

    pier_forces_expected = {
        "shape": [6, 7],
        "columns": ["Story", "Pier", "Output Case", "Step Type", "Location", "V2", "V3"],
        "piers": ["P1", "P2"],
        "load_cases": ["Push_X+", "Push_X-"],
        "row_count": 6
    }
    with open(push_expected / "pier_forces.json", "w") as f:
        json.dump(pier_forces_expected, f, indent=2)

    print(f"Created expected outputs in {nltha_expected} and {push_expected}")


if __name__ == "__main__":
    create_nltha_fixture()
    create_pushover_fixture()
    create_expected_outputs()
    print("\nAll fixtures created successfully!")
