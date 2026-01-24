"""View loader function facade for ProjectDetailWindow."""

from .loaders.standard import (
    load_standard_dataset,
    load_element_dataset,
    load_joint_dataset,
    load_maxmin_dataset,
    load_element_maxmin_dataset,
)
from .loaders.rotations import (
    load_all_rotations,
    load_all_column_rotations,
    load_all_beam_rotations,
    load_beam_rotations_table,
)
from .loaders.comparisons import (
    load_comparison_all_rotations,
    load_comparison_all_column_rotations,
    load_comparison_all_beam_rotations,
    load_comparison_joint_scatter,
)
from .loaders.foundation import (
    load_all_soil_pressures,
    load_soil_pressures_table,
    load_all_vertical_displacements,
    load_vertical_displacements_table,
)
from .loaders.pushover import (
    load_pushover_curve,
    load_all_pushover_curves,
)
from .loaders.time_series import load_time_series_global

__all__ = [
    "load_standard_dataset",
    "load_element_dataset",
    "load_joint_dataset",
    "load_maxmin_dataset",
    "load_element_maxmin_dataset",
    "load_all_rotations",
    "load_all_column_rotations",
    "load_all_beam_rotations",
    "load_beam_rotations_table",
    "load_comparison_all_rotations",
    "load_comparison_all_column_rotations",
    "load_comparison_all_beam_rotations",
    "load_comparison_joint_scatter",
    "load_all_soil_pressures",
    "load_soil_pressures_table",
    "load_all_vertical_displacements",
    "load_vertical_displacements_table",
    "load_pushover_curve",
    "load_all_pushover_curves",
    "load_time_series_global",
]
