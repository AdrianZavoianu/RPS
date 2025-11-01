from __future__ import annotations

from typing import Optional

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
    """Return display label for a dataset."""
    base_label = DISPLAY_NAME_OVERRIDES.get(result_type, result_type)
    if direction:
        return f"{base_label} - {direction} Direction"
    return base_label
