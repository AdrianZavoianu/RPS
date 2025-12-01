"""Declarative task definitions for DataImporter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class ImportTask:
    """Describe a single sheet import operation."""

    label: str
    handler: str
    phase: str
    sheets: Sequence[str]
    require_all_sheets: bool = True


DEFAULT_IMPORT_TASKS: tuple[ImportTask, ...] = (
    ImportTask(
        label="Story Drifts",
        handler="_import_story_drifts",
        phase="story_drifts",
        sheets=("Story Drifts",),
    ),
    ImportTask(
        label="Story Accelerations",
        handler="_import_story_accelerations",
        phase="story_accelerations",
        sheets=("Diaphragm Accelerations",),
    ),
    ImportTask(
        label="Story Forces",
        handler="_import_story_forces",
        phase="story_forces",
        sheets=("Story Forces",),
    ),
    ImportTask(
        label="Floors Displacements",
        handler="_import_joint_displacements",
        phase="floor_displacements",
        sheets=("Joint Displacements",),
    ),
    ImportTask(
        label="Pier Forces",
        handler="_import_pier_forces",
        phase="pier_forces",
        sheets=("Pier Forces",),
    ),
    ImportTask(
        label="Column Forces",
        handler="_import_column_forces",
        phase="column_forces",
        sheets=("Element Forces - Columns",),
    ),
    ImportTask(
        label="Column Axials",
        handler="_import_column_axials",
        phase="column_axials",
        sheets=("Element Forces - Columns",),
    ),
    ImportTask(
        label="Column Rotations",
        handler="_import_column_rotations",
        phase="column_rotations",
        sheets=("Fiber Hinge States",),
    ),
    ImportTask(
        label="Beam Rotations",
        handler="_import_beam_rotations",
        phase="beam_rotations",
        sheets=("Hinge States",),
    ),
    ImportTask(
        label="Quad Rotations",
        handler="_import_quad_rotations",
        phase="quad_rotations",
        sheets=("Quad Strain Gauge - Rotation",),
    ),
    ImportTask(
        label="Soil Pressures",
        handler="_import_soil_pressures",
        phase="soil_pressures",
        sheets=("Soil Pressures",),
    ),
    ImportTask(
        label="Vertical Displacements",
        handler="_import_vertical_displacements",
        phase="vertical_displacements",
        sheets=("Joint Displacements", "Fou"),
    ),
)
