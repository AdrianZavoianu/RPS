"""Configuration for different result types (Drifts, Accelerations, Forces)."""

from dataclasses import dataclass


@dataclass
class ResultTypeConfig:
    """Configuration for a result type."""

    name: str
    """Result type name (e.g., 'Drifts', 'Accelerations', 'Forces')"""

    direction_suffix: str
    """Column suffix for filtering (e.g., '_X', '_UX', '_VX')"""

    unit: str
    """Display unit (e.g., '%', 'g', 'kN')"""

    decimal_places: int
    """Number of decimal places for formatting"""

    multiplier: float
    """Multiplier for unit conversion (100 for %, 1 for others)"""

    y_label: str
    """Y-axis label for plots"""

    plot_mode: str
    """Plot display mode: 'building_profile' or 'tabs'"""

    color_scheme: str
    """Color scheme identifier for table gradient"""


# Configuration registry
RESULT_CONFIGS = {
    'Drifts': ResultTypeConfig(
        name='Drifts',
        direction_suffix='_X',
        unit='%',
        decimal_places=2,
        multiplier=100.0,
        y_label='Drift (%)',
        plot_mode='building_profile',
        color_scheme='blue_orange',
    ),
    'Drifts_X': ResultTypeConfig(
        name='Drifts_X',
        direction_suffix='_X',
        unit='%',
        decimal_places=2,
        multiplier=100.0,
        y_label='Drift X (%)',
        plot_mode='building_profile',
        color_scheme='blue_orange',
    ),
    'Drifts_Y': ResultTypeConfig(
        name='Drifts_Y',
        direction_suffix='_Y',
        unit='%',
        decimal_places=2,
        multiplier=100.0,
        y_label='Drift Y (%)',
        plot_mode='building_profile',
        color_scheme='blue_orange',
    ),
    'Accelerations': ResultTypeConfig(
        name='Accelerations',
        direction_suffix='_UX',
        unit='g',
        decimal_places=2,
        multiplier=1.0,
        y_label='Acceleration (g)',
        plot_mode='building_profile',
        color_scheme='blue_orange',
    ),
    'Accelerations_X': ResultTypeConfig(
        name='Accelerations_X',
        direction_suffix='_UX',
        unit='g',
        decimal_places=2,
        multiplier=1.0,
        y_label='Acceleration UX (g)',
        plot_mode='building_profile',
        color_scheme='blue_orange',
    ),
    'Accelerations_Y': ResultTypeConfig(
        name='Accelerations_Y',
        direction_suffix='_UY',
        unit='g',
        decimal_places=2,
        multiplier=1.0,
        y_label='Acceleration UY (g)',
        plot_mode='building_profile',
        color_scheme='blue_orange',
    ),
    'Forces': ResultTypeConfig(
        name='Forces',
        direction_suffix='_VX',
        unit='kN',
        decimal_places=0,
        multiplier=1.0,
        y_label='Story Shear (kN)',
        plot_mode='building_profile',
        color_scheme='blue_orange',
    ),
    'Forces_X': ResultTypeConfig(
        name='Forces_X',
        direction_suffix='_VX',
        unit='kN',
        decimal_places=0,
        multiplier=1.0,
        y_label='Story Shear VX (kN)',
        plot_mode='building_profile',
        color_scheme='blue_orange',
    ),
    'Forces_Y': ResultTypeConfig(
        name='Forces_Y',
        direction_suffix='_VY',
        unit='kN',
        decimal_places=0,
        multiplier=1.0,
        y_label='Story Shear VY (kN)',
        plot_mode='building_profile',
        color_scheme='blue_orange',
    ),
    'Displacements': ResultTypeConfig(
        name='Displacements',
        direction_suffix='_UX',
        unit='mm',
        decimal_places=0,
        multiplier=1.0,
        y_label='Floor Displacement (mm)',
        plot_mode='building_profile',
        color_scheme='blue_orange',
    ),
    'Displacements_X': ResultTypeConfig(
        name='Displacements_X',
        direction_suffix='_UX',
        unit='mm',
        decimal_places=0,
        multiplier=1.0,
        y_label='Floor Displacement UX (mm)',
        plot_mode='building_profile',
        color_scheme='blue_orange',
    ),
    'Displacements_Y': ResultTypeConfig(
        name='Displacements_Y',
        direction_suffix='_UY',
        unit='mm',
        decimal_places=0,
        multiplier=1.0,
        y_label='Floor Displacement UY (mm)',
        plot_mode='building_profile',
        color_scheme='blue_orange',
    ),
}


def get_config(result_type: str) -> ResultTypeConfig:
    """Get configuration for a result type."""
    return RESULT_CONFIGS.get(result_type, RESULT_CONFIGS['Drifts'])
