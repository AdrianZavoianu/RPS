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
    'Accelerations': ResultTypeConfig(
        name='Accelerations',
        direction_suffix='_UX',
        unit='g',
        decimal_places=3,
        multiplier=1.0,
        y_label='Acceleration (g)',
        plot_mode='building_profile',
        color_scheme='blue_orange',
    ),
    'Forces': ResultTypeConfig(
        name='Forces',
        direction_suffix='_VX',
        unit='kN',
        decimal_places=2,
        multiplier=1.0,
        y_label='Shear Force (kN)',
        plot_mode='building_profile',
        color_scheme='blue_orange',
    ),
}


def get_config(result_type: str) -> ResultTypeConfig:
    """Get configuration for a result type."""
    return RESULT_CONFIGS.get(result_type, RESULT_CONFIGS['Drifts'])
