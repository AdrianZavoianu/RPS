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
    'WallShears': ResultTypeConfig(
        name='WallShears',
        direction_suffix='',
        unit='kN',
        decimal_places=0,
        multiplier=1.0,
        y_label='Wall Shear (kN)',
        plot_mode='building_profile',
        color_scheme='blue_orange',
    ),
    'WallShears_V2': ResultTypeConfig(
        name='WallShears_V2',
        direction_suffix='_V2',
        unit='kN',
        decimal_places=0,
        multiplier=1.0,
        y_label='Wall Shear V2 (kN)',
        plot_mode='building_profile',
        color_scheme='blue_orange',
    ),
    'WallShears_V3': ResultTypeConfig(
        name='WallShears_V3',
        direction_suffix='_V3',
        unit='kN',
        decimal_places=0,
        multiplier=1.0,
        y_label='Wall Shear V3 (kN)',
        plot_mode='building_profile',
        color_scheme='blue_orange',
    ),
    'QuadRotations': ResultTypeConfig(
        name='QuadRotations',
        direction_suffix='',  # No direction suffix for rotations
        unit='%',
        decimal_places=2,
        multiplier=1.0,  # Already converted to percentage in cache (rad * 100)
        y_label='Rotation (%)',
        plot_mode='building_profile',
        color_scheme='blue_orange',
    ),
    'ColumnShears': ResultTypeConfig(
        name='ColumnShears',
        direction_suffix='',
        unit='kN',
        decimal_places=0,
        multiplier=1.0,
        y_label='Column Shear (kN)',
        plot_mode='building_profile',
        color_scheme='blue_orange',
    ),
    'ColumnShears_V2': ResultTypeConfig(
        name='ColumnShears_V2',
        direction_suffix='_V2',
        unit='kN',
        decimal_places=0,
        multiplier=1.0,
        y_label='Column Shear V2 (kN)',
        plot_mode='building_profile',
        color_scheme='blue_orange',
    ),
    'ColumnShears_V3': ResultTypeConfig(
        name='ColumnShears_V3',
        direction_suffix='_V3',
        unit='kN',
        decimal_places=0,
        multiplier=1.0,
        y_label='Column Shear V3 (kN)',
        plot_mode='building_profile',
        color_scheme='blue_orange',
    ),
    'MinAxial': ResultTypeConfig(
        name='MinAxial',
        direction_suffix='',  # No direction suffix for axial forces
        unit='kN',
        decimal_places=0,
        multiplier=1.0,
        y_label='Min Axial Force (kN)',
        plot_mode='building_profile',
        color_scheme='blue_orange',
    ),
    'ColumnAxials': ResultTypeConfig(
        name='ColumnAxials',
        direction_suffix='',  # No direction suffix for axial forces
        unit='kN',
        decimal_places=0,
        multiplier=1.0,
        y_label='Column Axial Force (kN)',
        plot_mode='building_profile',
        color_scheme='blue_orange',
    ),
    'ColumnRotations': ResultTypeConfig(
        name='ColumnRotations',
        direction_suffix='',
        unit='%',
        decimal_places=2,
        multiplier=1.0,  # Already converted to percentage in cache (rad * 100)
        y_label='Column Rotation (%)',
        plot_mode='building_profile',
        color_scheme='blue_orange',
    ),
    'ColumnRotations_R2': ResultTypeConfig(
        name='ColumnRotations_R2',
        direction_suffix='_R2',
        unit='%',
        decimal_places=2,
        multiplier=1.0,  # Already converted to percentage in cache (rad * 100)
        y_label='Column Rotation R2 (%)',
        plot_mode='building_profile',
        color_scheme='blue_orange',
    ),
    'ColumnRotations_R3': ResultTypeConfig(
        name='ColumnRotations_R3',
        direction_suffix='_R3',
        unit='%',
        decimal_places=2,
        multiplier=1.0,  # Already converted to percentage in cache (rad * 100)
        y_label='Column Rotation R3 (%)',
        plot_mode='building_profile',
        color_scheme='blue_orange',
    ),
    'BeamRotations': ResultTypeConfig(
        name='BeamRotations',
        direction_suffix='',  # No direction suffix for beam rotations
        unit='%',
        decimal_places=2,
        multiplier=1.0,  # Already converted to percentage in cache (rad * 100)
        y_label='Beam Rotation (%)',
        plot_mode='building_profile',
        color_scheme='blue_orange',
    ),
    'BeamRotations_R3Plastic': ResultTypeConfig(
        name='BeamRotations_R3Plastic',
        direction_suffix='_R3Plastic',
        unit='%',
        decimal_places=2,
        multiplier=1.0,  # Already converted to percentage in cache (rad * 100)
        y_label='Beam R3 Plastic Rotation (%)',
        plot_mode='building_profile',
        color_scheme='blue_orange',
    ),
    'SoilPressures_Min': ResultTypeConfig(
        name='SoilPressures_Min',
        direction_suffix='',  # No direction suffix for soil pressures
        unit='kN/m²',
        decimal_places=1,
        multiplier=1.0,
        y_label='Min Soil Pressure (kN/m²)',
        plot_mode='tabs',  # Use tabs since there's no building profile for foundation elements
        color_scheme='orange_blue',  # Orange for lower (more negative) values, blue for higher
    ),
    'VerticalDisplacements_Min': ResultTypeConfig(
        name='VerticalDisplacements_Min',
        direction_suffix='',  # No direction suffix for vertical displacements
        unit='mm',
        decimal_places=2,
        multiplier=1.0,
        y_label='Min Vertical Displacement (mm)',
        plot_mode='tabs',  # Use tabs since there's no building profile for foundation joints
        color_scheme='orange_blue',  # Orange for lower (more negative) values, blue for higher
    ),
}


def get_config(result_type: str) -> ResultTypeConfig:
    """Get configuration for a result type."""
    return RESULT_CONFIGS.get(result_type, RESULT_CONFIGS['Drifts'])


def format_result_type_with_unit(result_type: str, direction: str = None) -> str:
    """Format result type name with unit in brackets.

    Args:
        result_type: Base result type (e.g., 'Drifts', 'Forces', 'Displacements')
        direction: Direction suffix (e.g., 'X', 'Y') - optional

    Returns:
        Formatted string like "Floor Displacements [mm]" or "Story Forces [kN]"

    Note:
        - Drifts and rotations are unitless (shown as percentage in tables but conceptually unitless)
        - Returns display name without unit for drifts and rotations
    """
    # Map base result types to display names
    display_names = {
        'Drifts': 'Story Drifts',
        'Accelerations': 'Story Accelerations',
        'Forces': 'Story Forces',
        'Displacements': 'Floor Displacements',
        'WallShears': 'Wall Shears',
        'QuadRotations': 'Quad Rotations',
        'ColumnShears': 'Column Shears',
        'ColumnAxials': 'Column Axials',
        'MinAxial': 'Min Axial',
        'ColumnRotations': 'Column Rotations',
        'BeamRotations': 'Beam Rotations',
        'SoilPressures_Min': 'Min Soil Pressures',
        'VerticalDisplacements_Min': 'Min Vertical Displacements',
    }

    # Get display name
    display_name = display_names.get(result_type, result_type)

    # Check if result type is drift or rotation (unitless)
    is_unitless = 'Drift' in result_type or 'Rotation' in result_type

    if is_unitless:
        # No unit for drifts and rotations
        if direction:
            return f"{display_name} - {direction} Direction"
        return display_name

    # Get config to extract unit
    config_key = f"{result_type}_{direction}" if direction else result_type
    config = RESULT_CONFIGS.get(config_key)

    if not config:
        # Fallback: try base config
        config = RESULT_CONFIGS.get(result_type)

    if config and config.unit:
        unit_str = f" [{config.unit}]"
        if direction:
            return f"{display_name}{unit_str} - {direction} Direction"
        return f"{display_name}{unit_str}"

    # Fallback: no unit available
    if direction:
        return f"{display_name} - {direction} Direction"
    return display_name
