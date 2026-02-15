"""Configuration for pushover importers.

This module defines the configuration for all pushover result types,
enabling a path toward consolidation into a single generic importer.

Current State:
    There are 9 separate pushover importers with ~80% duplicated code:
    - PushoverWallImporter (wall shears V2/V3 + rotations)
    - PushoverColumnImporter (column rotations R2/R3)
    - PushoverColumnShearImporter (column shears V2/V3)
    - PushoverBeamImporter (beam rotations R3)
    - PushoverJointImporter (joint displacements Ux/Uy/Uz)
    - PushoverSoilPressureImporter (soil pressures)
    - PushoverVertDisplacementImporter (vertical displacements)
    - PushoverGlobalImporter (story-level drifts/forces)
    - PushoverCurveImporter (capacity curves)

Consolidation Plan:
    1. All element importers (wall, column, beam) should inherit from BasePushoverImporter
    2. Use this config to drive a GenericPushoverElementImporter
    3. Keep specialized importers only where logic is significantly different

Usage:
    config = PUSHOVER_IMPORTER_CONFIGS["wall_shear"]
    # config contains parser_class, model_class, cache_table, field_mapping, etc.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Type, Any


@dataclass
class PushoverImporterConfig:
    """Configuration for a pushover importer type."""
    
    # Identity
    name: str
    description: str
    
    # Parser configuration
    parser_module: str  # e.g., "processing.pushover.pushover_wall_parser"
    parser_class: str   # e.g., "PushoverWallParser"
    
    # Model configuration
    model_module: str   # e.g., "database.models"
    model_class: str    # e.g., "WallShear"
    
    # Element configuration (for element-based importers)
    element_type: Optional[str] = None  # "Wall", "Column", "Beam", "Quad", None
    
    # Field mappings: parser field -> model field
    field_mapping: Dict[str, str] = field(default_factory=dict)
    
    # Statistics keys to track
    stats_keys: List[str] = field(default_factory=list)
    
    # Cache configuration
    cache_table: Optional[str] = None  # e.g., "element_results_cache"
    cache_result_type: Optional[str] = None  # e.g., "Wall Shear V2"
    
    # Whether this importer uses story-level or element-level data
    is_story_based: bool = False
    is_element_based: bool = True
    
    # Directions supported
    directions: List[str] = field(default_factory=lambda: ["X", "Y"])


# =============================================================================
# Importer Configurations
# =============================================================================

PUSHOVER_IMPORTER_CONFIGS: Dict[str, PushoverImporterConfig] = {
    
    # ----- Wall Importers -----
    "wall_shear_v2": PushoverImporterConfig(
        name="wall_shear_v2",
        description="Wall (Pier) V2 Shear Forces",
        parser_module="processing.pushover.pushover_wall_parser",
        parser_class="PushoverWallParser",
        model_module="database.models",
        model_class="WallShear",
        element_type="Wall",
        field_mapping={
            "pier": "element_name",
            "story": "story_name",
            "unique_name": "unique_name",
            "output_case": "load_case_name",
            "v2": "shear",
        },
        stats_keys=["v2_shears"],
        cache_table="element_results_cache",
        cache_result_type="Wall Shear V2",
    ),
    
    "wall_shear_v3": PushoverImporterConfig(
        name="wall_shear_v3",
        description="Wall (Pier) V3 Shear Forces",
        parser_module="processing.pushover.pushover_wall_parser",
        parser_class="PushoverWallParser",
        model_module="database.models",
        model_class="WallShear",
        element_type="Wall",
        field_mapping={
            "pier": "element_name",
            "story": "story_name",
            "unique_name": "unique_name",
            "output_case": "load_case_name",
            "v3": "shear",
        },
        stats_keys=["v3_shears"],
        cache_table="element_results_cache",
        cache_result_type="Wall Shear V3",
    ),
    
    "wall_rotation": PushoverImporterConfig(
        name="wall_rotation",
        description="Wall (Quad) Rotations",
        parser_module="processing.pushover.pushover_wall_parser",
        parser_class="PushoverWallParser",
        model_module="database.models",
        model_class="QuadRotation",
        element_type="Quad",
        field_mapping={
            "quad": "element_name",
            "story": "story_name",
            "unique_name": "unique_name",
            "output_case": "load_case_name",
            "rotation": "rotation",
        },
        stats_keys=["rotations"],
        cache_table="element_results_cache",
        cache_result_type="Wall Rotation",
    ),
    
    # ----- Column Importers -----
    "column_rotation_r2": PushoverImporterConfig(
        name="column_rotation_r2",
        description="Column R2 Plastic Rotations",
        parser_module="processing.pushover.pushover_column_parser",
        parser_class="PushoverColumnParser",
        model_module="database.models",
        model_class="ColumnRotation",
        element_type="Column",
        field_mapping={
            "column": "element_name",
            "story": "story_name",
            "unique_name": "unique_name",
            "output_case": "load_case_name",
            "r2_plastic": "rotation",
            "location": "location",
        },
        stats_keys=["r2_rotations"],
        cache_table="element_results_cache",
        cache_result_type="Column Rotation R2",
    ),
    
    "column_rotation_r3": PushoverImporterConfig(
        name="column_rotation_r3",
        description="Column R3 Plastic Rotations",
        parser_module="processing.pushover.pushover_column_parser",
        parser_class="PushoverColumnParser",
        model_module="database.models",
        model_class="ColumnRotation",
        element_type="Column",
        field_mapping={
            "column": "element_name",
            "story": "story_name",
            "unique_name": "unique_name",
            "output_case": "load_case_name",
            "r3_plastic": "rotation",
            "location": "location",
        },
        stats_keys=["r3_rotations"],
        cache_table="element_results_cache",
        cache_result_type="Column Rotation R3",
    ),
    
    "column_shear_v2": PushoverImporterConfig(
        name="column_shear_v2",
        description="Column V2 Shear Forces",
        parser_module="processing.pushover.pushover_column_parser",
        parser_class="PushoverColumnParser",
        model_module="database.models",
        model_class="ColumnShear",
        element_type="Column",
        field_mapping={
            "column": "element_name",
            "story": "story_name",
            "unique_name": "unique_name",
            "output_case": "load_case_name",
            "v2": "shear",
            "location": "location",
        },
        stats_keys=["v2_shears"],
        cache_table="element_results_cache",
        cache_result_type="Column Shear V2",
    ),
    
    # ----- Beam Importers -----
    "beam_rotation": PushoverImporterConfig(
        name="beam_rotation",
        description="Beam R3 Plastic Rotations",
        parser_module="processing.pushover.pushover_beam_parser",
        parser_class="PushoverBeamParser",
        model_module="database.models",
        model_class="BeamRotation",
        element_type="Beam",
        field_mapping={
            "beam": "element_name",
            "story": "story_name",
            "unique_name": "unique_name",
            "output_case": "load_case_name",
            "r3_plastic": "rotation",
            "location": "location",
        },
        stats_keys=["rotations"],
        cache_table="element_results_cache",
        cache_result_type="Beam Rotation",
    ),
    
    # ----- Joint Importers -----
    "joint_displacement": PushoverImporterConfig(
        name="joint_displacement",
        description="Joint Displacements (Ux, Uy, Uz)",
        parser_module="processing.pushover.pushover_joint_parser",
        parser_class="PushoverJointParser",
        model_module="database.models",
        model_class="JointResultsCache",  # Direct to cache
        element_type=None,  # Joints, not elements
        field_mapping={
            "story": "story",
            "label": "label",
            "unique_name": "unique_name",
            "output_case": "load_case",
            "ux": "ux",
            "uy": "uy",
            "uz": "uz",
        },
        stats_keys=["ux_displacements", "uy_displacements", "uz_displacements"],
        cache_table="joint_results_cache",
        is_element_based=False,
    ),
    
    # ----- Other Importers -----
    "soil_pressure": PushoverImporterConfig(
        name="soil_pressure",
        description="Soil Pressures",
        parser_module="processing.pushover.pushover_soil_pressure_parser",
        parser_class="PushoverSoilPressureParser",
        model_module="database.models",
        model_class="SoilPressure",
        element_type=None,
        field_mapping={
            "joint": "joint_name",
            "output_case": "load_case_name",
            "pressure": "pressure",
        },
        stats_keys=["pressures"],
        cache_table="joint_results_cache",
        is_element_based=False,
    ),
    
    "vertical_displacement": PushoverImporterConfig(
        name="vertical_displacement",
        description="Vertical Displacements",
        parser_module="processing.pushover.pushover_vert_displacement_parser",
        parser_class="PushoverVertDisplacementParser",
        model_module="database.models",
        model_class="VerticalDisplacement",
        element_type=None,
        field_mapping={
            "joint": "unique_name",
            "output_case": "load_case_name",
            "uz": "displacement",
        },
        stats_keys=["displacements"],
        is_element_based=False,
    ),
}


# =============================================================================
# Helper Functions
# =============================================================================

def get_importer_config(importer_type: str) -> PushoverImporterConfig:
    """Get configuration for a pushover importer type.
    
    Args:
        importer_type: Type key (e.g., "wall_shear_v2", "column_rotation_r2")
        
    Returns:
        PushoverImporterConfig for the type
        
    Raises:
        KeyError: If importer_type not found
    """
    if importer_type not in PUSHOVER_IMPORTER_CONFIGS:
        raise KeyError(
            f"Unknown importer type: {importer_type}. "
            f"Available: {list(PUSHOVER_IMPORTER_CONFIGS.keys())}"
        )
    return PUSHOVER_IMPORTER_CONFIGS[importer_type]


def get_element_importer_types() -> List[str]:
    """Get list of element-based importer types."""
    return [
        key for key, config in PUSHOVER_IMPORTER_CONFIGS.items()
        if config.is_element_based
    ]


def get_story_importer_types() -> List[str]:
    """Get list of story-based importer types."""
    return [
        key for key, config in PUSHOVER_IMPORTER_CONFIGS.items()
        if config.is_story_based
    ]


def get_importers_by_element_type(element_type: str) -> List[str]:
    """Get importer types for a specific element type.
    
    Args:
        element_type: "Wall", "Column", "Beam", "Quad"
        
    Returns:
        List of importer type keys
    """
    return [
        key for key, config in PUSHOVER_IMPORTER_CONFIGS.items()
        if config.element_type == element_type
    ]
