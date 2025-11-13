from __future__ import annotations

from typing import Optional
from config.result_config import format_result_type_with_unit

DISPLAY_NAME_OVERRIDES = {
    "Drifts": "Story Drifts",
    "Accelerations": "Story Accelerations",
    "Forces": "Story Shears",
    "Displacements": "Floors Displacements",
    "WallShears": "Wall Shears",
    "ColumnShears": "Column Shears",
    "MinAxial": "Min Axial Force",
    "QuadRotations": "Quad Rotations",
    "MaxMinDrifts": "Max/Min Drifts",
    "MaxMinAccelerations": "Max/Min Accelerations",
    "MaxMinForces": "Max/Min Story Shears",
    "MaxMinDisplacements": "Max/Min Floors Displacements",
    "MaxMinColumnShears": "Max/Min Column Shears",
    "MaxMinColumnRotations": "Max/Min Column Rotations",
    "MaxMinQuadRotations": "Max/Min Quad Rotations",
}


def build_display_label(result_type: str, direction: Optional[str]) -> str:
    """Return display label for a dataset with units.

    Examples:
        - "Story Drifts - X Direction" (unitless)
        - "Floor Displacements [mm] - X Direction"
        - "Story Forces [kN] - Y Direction"
    """
    # Handle MaxMin types specially
    if result_type.startswith("MaxMin"):
        # Extract base type from MaxMin prefix
        base_type = result_type[6:]  # Remove "MaxMin" prefix
        base_label = DISPLAY_NAME_OVERRIDES.get(result_type, f"Max/Min {base_type}")

        # MaxMin views don't have direction, but may have unit
        from config.result_config import RESULT_CONFIGS
        config = RESULT_CONFIGS.get(base_type)
        if config and config.unit:
            # Check if unitless (drifts/rotations)
            is_unitless = 'Drift' in result_type or 'Rotation' in result_type
            if not is_unitless:
                return f"{base_label} [{config.unit}]"
        return base_label

    # Use the new format_result_type_with_unit function for standard types
    return format_result_type_with_unit(result_type, direction)
