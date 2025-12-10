"""Configuration for different result types (Drifts, Accelerations, Forces)."""

from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(frozen=True)
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


@dataclass(frozen=True)
class ResultTypeVariantSpec:
    """Variant overrides for a base result type."""

    key_suffix: str
    direction_suffix: Optional[str] = None
    unit: Optional[str] = None
    decimal_places: Optional[int] = None
    multiplier: Optional[float] = None
    y_label: Optional[str] = None
    plot_mode: Optional[str] = None
    color_scheme: Optional[str] = None


@dataclass(frozen=True)
class ResultTypeSpec:
    """Specification for generating ResultTypeConfig entries."""

    key: str
    direction_suffix: str
    unit: str
    decimal_places: int
    multiplier: float
    y_label: str
    plot_mode: str
    color_scheme: str
    variants: Tuple[ResultTypeVariantSpec, ...] = tuple()


def _resolve_attr(spec: ResultTypeSpec, variant: Optional[ResultTypeVariantSpec], attr: str):
    if variant is None:
        return getattr(spec, attr)
    value = getattr(variant, attr)
    return value if value is not None else getattr(spec, attr)


def _create_config(
    spec: ResultTypeSpec,
    key: str,
    variant: Optional[ResultTypeVariantSpec] = None,
) -> ResultTypeConfig:
    return ResultTypeConfig(
        name=key,
        direction_suffix=_resolve_attr(spec, variant, "direction_suffix"),
        unit=_resolve_attr(spec, variant, "unit"),
        decimal_places=_resolve_attr(spec, variant, "decimal_places"),
        multiplier=_resolve_attr(spec, variant, "multiplier"),
        y_label=_resolve_attr(spec, variant, "y_label"),
        plot_mode=_resolve_attr(spec, variant, "plot_mode"),
        color_scheme=_resolve_attr(spec, variant, "color_scheme"),
    )


def _build_configs(specs: Tuple[ResultTypeSpec, ...]) -> dict:
    configs = {}
    for spec in specs:
        configs[spec.key] = _create_config(spec, spec.key)
        for variant in spec.variants:
            variant_key = f"{spec.key}_{variant.key_suffix}"
            configs[variant_key] = _create_config(spec, variant_key, variant)
    return configs


RESULT_TYPE_SPECS: Tuple[ResultTypeSpec, ...] = (
    ResultTypeSpec(
        key="Drifts",
        direction_suffix="_X",
        unit="%",
        decimal_places=2,
        multiplier=100.0,  # Display as percentage (0.025 -> 2.5)
        y_label="Drift [%]",
        plot_mode="building_profile",
        color_scheme="blue_orange",
        variants=(
            ResultTypeVariantSpec(
                key_suffix="X",
                direction_suffix="_X",
                y_label="Drift X [%]",
            ),
            ResultTypeVariantSpec(
                key_suffix="Y",
                direction_suffix="_Y",
                y_label="Drift Y [%]",
            ),
        ),
    ),
    ResultTypeSpec(
        key="Accelerations",
        direction_suffix="_UX",
        unit="g",
        decimal_places=2,
        multiplier=1.0,
        y_label="Acceleration (g)",
        plot_mode="building_profile",
        color_scheme="blue_orange",
        variants=(
            ResultTypeVariantSpec(
                key_suffix="X",
                direction_suffix="_UX",
                y_label="Acceleration UX (g)",
            ),
            ResultTypeVariantSpec(
                key_suffix="Y",
                direction_suffix="_UY",
                y_label="Acceleration UY (g)",
            ),
        ),
    ),
    ResultTypeSpec(
        key="Forces",
        direction_suffix="_VX",
        unit="kN",
        decimal_places=0,
        multiplier=1.0,
        y_label="Story Shear (kN)",
        plot_mode="building_profile",
        color_scheme="blue_orange",
        variants=(
            ResultTypeVariantSpec(
                key_suffix="X",
                direction_suffix="_VX",
                y_label="Story Shear VX (kN)",
            ),
            ResultTypeVariantSpec(
                key_suffix="Y",
                direction_suffix="_VY",
                y_label="Story Shear VY (kN)",
            ),
        ),
    ),
    ResultTypeSpec(
        key="Displacements",
        direction_suffix="_UX",
        unit="mm",
        decimal_places=0,
        multiplier=1.0,
        y_label="Floor Displacement (mm)",
        plot_mode="building_profile",
        color_scheme="blue_orange",
        variants=(
            ResultTypeVariantSpec(
                key_suffix="X",
                direction_suffix="_UX",
                y_label="Floor Displacement UX (mm)",
            ),
            ResultTypeVariantSpec(
                key_suffix="Y",
                direction_suffix="_UY",
                y_label="Floor Displacement UY (mm)",
            ),
        ),
    ),
    ResultTypeSpec(
        key="WallShears",
        direction_suffix="",
        unit="kN",
        decimal_places=0,
        multiplier=1.0,
        y_label="Wall Shear (kN)",
        plot_mode="building_profile",
        color_scheme="blue_orange",
        variants=(
            ResultTypeVariantSpec(
                key_suffix="V2",
                direction_suffix="_V2",
                y_label="Wall Shear V2 (kN)",
            ),
            ResultTypeVariantSpec(
                key_suffix="V3",
                direction_suffix="_V3",
                y_label="Wall Shear V3 (kN)",
            ),
        ),
    ),
    ResultTypeSpec(
        key="QuadRotations",
        direction_suffix="",
        unit="%",
        decimal_places=2,
        multiplier=100.0,  # Display as percentage
        y_label="Rotation [%]",
        plot_mode="building_profile",
        color_scheme="blue_orange",
    ),
    ResultTypeSpec(
        key="ColumnShears",
        direction_suffix="",
        unit="kN",
        decimal_places=0,
        multiplier=1.0,
        y_label="Column Shear (kN)",
        plot_mode="building_profile",
        color_scheme="blue_orange",
        variants=(
            ResultTypeVariantSpec(
                key_suffix="V2",
                direction_suffix="_V2",
                y_label="Column Shear V2 (kN)",
            ),
            ResultTypeVariantSpec(
                key_suffix="V3",
                direction_suffix="_V3",
                y_label="Column Shear V3 (kN)",
            ),
        ),
    ),
    ResultTypeSpec(
        key="MinAxial",
        direction_suffix="",
        unit="kN",
        decimal_places=0,
        multiplier=1.0,
        y_label="Min Axial Force (kN)",
        plot_mode="building_profile",
        color_scheme="blue_orange",
    ),
    ResultTypeSpec(
        key="ColumnAxials",
        direction_suffix="",
        unit="kN",
        decimal_places=0,
        multiplier=1.0,
        y_label="Column Axial Force (kN)",
        plot_mode="building_profile",
        color_scheme="blue_orange",
    ),
    ResultTypeSpec(
        key="ColumnRotations",
        direction_suffix="",
        unit="%",
        decimal_places=2,
        multiplier=100.0,  # Display as percentage
        y_label="Column Rotation [%]",
        plot_mode="building_profile",
        color_scheme="blue_orange",
        variants=(
            ResultTypeVariantSpec(
                key_suffix="R2",
                direction_suffix="_R2",
                y_label="Column Rotation R2 [%]",
            ),
            ResultTypeVariantSpec(
                key_suffix="R3",
                direction_suffix="_R3",
                y_label="Column Rotation R3 [%]",
            ),
        ),
    ),
    ResultTypeSpec(
        key="BeamRotations",
        direction_suffix="",
        unit="%",
        decimal_places=2,
        multiplier=100.0,  # Display as percentage
        y_label="Beam Rotation [%]",
        plot_mode="building_profile",
        color_scheme="blue_orange",
        variants=(
            ResultTypeVariantSpec(
                key_suffix="R3Plastic",
                direction_suffix="_R3Plastic",
                y_label="Beam R3 Plastic Rotation [%]",
            ),
        ),
    ),
    ResultTypeSpec(
        key="SoilPressures_Min",
        direction_suffix="",
        unit="kN/m²",
        decimal_places=1,
        multiplier=1.0,
        y_label="Min Soil Pressure (kN/m²)",
        plot_mode="tabs",
        color_scheme="orange_blue",
    ),
    ResultTypeSpec(
        key="VerticalDisplacements_Min",
        direction_suffix="",
        unit="mm",
        decimal_places=2,
        multiplier=1.0,
        y_label="Min Vertical Displacement (mm)",
        plot_mode="tabs",
        color_scheme="orange_blue",
    ),
)


RESULT_CONFIGS = _build_configs(RESULT_TYPE_SPECS)


def get_config(result_type: str) -> ResultTypeConfig:
    """Get configuration for a result type."""
    return RESULT_CONFIGS.get(result_type, RESULT_CONFIGS['Drifts'])


def format_result_type_with_unit(result_type: str, direction: str = None) -> str:
    """Format result type name with unit in brackets.

    Args:
        result_type: Base result type (e.g., 'Drifts', 'Forces', 'Displacements')
        direction: Direction suffix (e.g., 'X', 'Y') - optional

    Returns:
        Formatted string like "Floor Displacements [mm]" or "Story Drifts [%]"
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
