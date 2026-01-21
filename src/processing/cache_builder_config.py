"""Configuration for cache builders.

This module defines the configuration for all cache types,
documenting the patterns used in CacheBuilder and enabling future consolidation.

Current State:
    The CacheBuilder class has separate methods for each cache type:
    - _cache_drifts, _cache_accelerations, _cache_forces, _cache_displacements
    - _cache_pier_forces, _cache_column_shears, _cache_column_axials
    - _cache_column_rotations, _cache_beam_rotations, _cache_quad_rotations
    - _cache_soil_pressures, _cache_vertical_displacements

    Each method follows the same pattern:
    1. Query records with joins to LoadCase, Story, and optionally Element
    2. Group by story_id (or element_id + story_id for elements)
    3. Build results_matrix dict keyed by load_case name
    4. Create cache entries and call replace_cache_entries

Consolidation Plan:
    1. Use this config to drive a generic cache_result_type() method
    2. Reduce ~500 LOC to ~100 LOC
    3. Make adding new result types trivial (just add config)

Usage:
    config = CACHE_CONFIGS["drifts"]
    # config contains model_class, value_field, cache_type, grouping_strategy, etc.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Type


class CacheType(Enum):
    """Type of cache table to use."""
    GLOBAL = "global"      # Uses results_cache table
    ELEMENT = "element"    # Uses element_results_cache table
    JOINT = "joint"        # Uses joint_results_cache table


class GroupingStrategy(Enum):
    """How to group records into cache entries."""
    BY_STORY = "by_story"                     # One entry per story (global results)
    BY_ELEMENT_STORY = "by_element_story"     # One entry per element-story pair
    BY_ELEMENT_DIRECTION_STORY = "by_element_direction_story"  # element, direction, story
    BY_UNIQUE_NAME = "by_unique_name"         # One entry per unique_name (joints)


@dataclass
class CacheConfig:
    """Configuration for a cache type."""
    
    # Identity
    name: str
    description: str
    
    # Cache destination
    cache_type: CacheType
    result_type: str  # e.g., "Drifts", "WallShears_V2"
    
    # Source configuration
    model_module: str  # e.g., "database.models"
    model_class: str   # e.g., "StoryDrift"
    
    # Value field to extract
    value_field: str   # e.g., "drift", "force", "rotation"
    
    # For envelope data (NLTHA), use max_value_field if present
    max_value_field: Optional[str] = None  # e.g., "max_drift"
    
    # Grouping strategy
    grouping: GroupingStrategy = GroupingStrategy.BY_STORY
    
    # For direction-based results (V2/V3, R2/R3)
    direction_field: Optional[str] = None  # Field name for direction
    directions: List[str] = field(default_factory=list)  # Valid directions
    
    # For element-based caches
    element_type: Optional[str] = None  # "Wall", "Column", "Beam", "Quad"
    
    # Additional filters
    requires_result_category: bool = True
    requires_result_set: bool = False  # Some join on result_set_id


# =============================================================================
# Global Cache Configurations
# =============================================================================

GLOBAL_CACHE_CONFIGS: Dict[str, CacheConfig] = {
    
    "drifts": CacheConfig(
        name="drifts",
        description="Story drift results",
        cache_type=CacheType.GLOBAL,
        result_type="Drifts",
        model_module="database.models",
        model_class="StoryDrift",
        value_field="drift",
        direction_field="direction",
        grouping=GroupingStrategy.BY_STORY,
    ),
    
    "accelerations": CacheConfig(
        name="accelerations",
        description="Story acceleration results",
        cache_type=CacheType.GLOBAL,
        result_type="Accelerations",
        model_module="database.models",
        model_class="StoryAcceleration",
        value_field="acceleration",
        direction_field="direction",
        grouping=GroupingStrategy.BY_STORY,
    ),
    
    "forces": CacheConfig(
        name="forces",
        description="Story force (base shear) results",
        cache_type=CacheType.GLOBAL,
        result_type="Forces",
        model_module="database.models",
        model_class="StoryForce",
        value_field="force",
        direction_field="direction",
        grouping=GroupingStrategy.BY_STORY,
    ),
    
    "displacements": CacheConfig(
        name="displacements",
        description="Story displacement results",
        cache_type=CacheType.GLOBAL,
        result_type="Displacements",
        model_module="database.models",
        model_class="StoryDisplacement",
        value_field="displacement",
        direction_field="direction",
        grouping=GroupingStrategy.BY_STORY,
    ),
}


# =============================================================================
# Element Cache Configurations
# =============================================================================

ELEMENT_CACHE_CONFIGS: Dict[str, CacheConfig] = {
    
    # Wall shears
    "wall_shears_v2": CacheConfig(
        name="wall_shears_v2",
        description="Wall (pier) V2 shear forces",
        cache_type=CacheType.ELEMENT,
        result_type="WallShears_V2",
        model_module="database.models",
        model_class="WallShear",
        value_field="force",
        direction_field="direction",
        directions=["V2"],
        element_type="Wall",
        grouping=GroupingStrategy.BY_ELEMENT_DIRECTION_STORY,
    ),
    
    "wall_shears_v3": CacheConfig(
        name="wall_shears_v3",
        description="Wall (pier) V3 shear forces",
        cache_type=CacheType.ELEMENT,
        result_type="WallShears_V3",
        model_module="database.models",
        model_class="WallShear",
        value_field="force",
        direction_field="direction",
        directions=["V3"],
        element_type="Wall",
        grouping=GroupingStrategy.BY_ELEMENT_DIRECTION_STORY,
    ),
    
    # Column shears
    "column_shears_v2": CacheConfig(
        name="column_shears_v2",
        description="Column V2 shear forces",
        cache_type=CacheType.ELEMENT,
        result_type="ColumnShears_V2",
        model_module="database.models",
        model_class="ColumnShear",
        value_field="force",
        direction_field="direction",
        directions=["V2"],
        element_type="Column",
        grouping=GroupingStrategy.BY_ELEMENT_DIRECTION_STORY,
    ),
    
    "column_shears_v3": CacheConfig(
        name="column_shears_v3",
        description="Column V3 shear forces",
        cache_type=CacheType.ELEMENT,
        result_type="ColumnShears_V3",
        model_module="database.models",
        model_class="ColumnShear",
        value_field="force",
        direction_field="direction",
        directions=["V3"],
        element_type="Column",
        grouping=GroupingStrategy.BY_ELEMENT_DIRECTION_STORY,
    ),
    
    # Column rotations
    "column_rotations_r2": CacheConfig(
        name="column_rotations_r2",
        description="Column R2 plastic rotations",
        cache_type=CacheType.ELEMENT,
        result_type="ColumnRotations_R2",
        model_module="database.models",
        model_class="ColumnRotation",
        value_field="rotation",
        max_value_field="max_rotation",
        direction_field="direction",
        directions=["R2"],
        element_type="Column",
        grouping=GroupingStrategy.BY_ELEMENT_DIRECTION_STORY,
    ),
    
    "column_rotations_r3": CacheConfig(
        name="column_rotations_r3",
        description="Column R3 plastic rotations",
        cache_type=CacheType.ELEMENT,
        result_type="ColumnRotations_R3",
        model_module="database.models",
        model_class="ColumnRotation",
        value_field="rotation",
        max_value_field="max_rotation",
        direction_field="direction",
        directions=["R3"],
        element_type="Column",
        grouping=GroupingStrategy.BY_ELEMENT_DIRECTION_STORY,
    ),
    
    # Beam rotations
    "beam_rotations": CacheConfig(
        name="beam_rotations",
        description="Beam R3 plastic rotations",
        cache_type=CacheType.ELEMENT,
        result_type="BeamRotations_R3Plastic",
        model_module="database.models",
        model_class="BeamRotation",
        value_field="r3_plastic",
        max_value_field="max_r3_plastic",
        element_type="Beam",
        grouping=GroupingStrategy.BY_ELEMENT_STORY,
    ),
    
    # Quad rotations
    "quad_rotations": CacheConfig(
        name="quad_rotations",
        description="Quad (wall panel) rotations",
        cache_type=CacheType.ELEMENT,
        result_type="QuadRotations_Pier",
        model_module="database.models",
        model_class="QuadRotation",
        value_field="rotation",
        max_value_field="max_rotation",
        element_type="Quad",
        grouping=GroupingStrategy.BY_ELEMENT_STORY,
    ),
}


# =============================================================================
# Joint Cache Configurations
# =============================================================================

JOINT_CACHE_CONFIGS: Dict[str, CacheConfig] = {
    
    "soil_pressures": CacheConfig(
        name="soil_pressures",
        description="Foundation soil pressures (minimum envelope)",
        cache_type=CacheType.JOINT,
        result_type="SoilPressures_Min",
        model_module="database.models",
        model_class="SoilPressure",
        value_field="min_pressure",
        grouping=GroupingStrategy.BY_UNIQUE_NAME,
        requires_result_set=True,
    ),
    
    "vertical_displacements": CacheConfig(
        name="vertical_displacements",
        description="Vertical displacements (minimum envelope)",
        cache_type=CacheType.JOINT,
        result_type="VerticalDisplacements_Min",
        model_module="database.models",
        model_class="VerticalDisplacement",
        value_field="min_displacement",
        grouping=GroupingStrategy.BY_UNIQUE_NAME,
        requires_result_set=True,
    ),
}


# =============================================================================
# Combined Configuration
# =============================================================================

ALL_CACHE_CONFIGS: Dict[str, CacheConfig] = {
    **GLOBAL_CACHE_CONFIGS,
    **ELEMENT_CACHE_CONFIGS,
    **JOINT_CACHE_CONFIGS,
}


# =============================================================================
# Helper Functions
# =============================================================================

def get_cache_config(config_name: str) -> CacheConfig:
    """Get configuration for a cache type.
    
    Args:
        config_name: Name of the cache config (e.g., "drifts", "wall_shears_v2")
        
    Returns:
        CacheConfig for the type
        
    Raises:
        KeyError: If config_name not found
    """
    if config_name not in ALL_CACHE_CONFIGS:
        raise KeyError(
            f"Unknown cache config: {config_name}. "
            f"Available: {list(ALL_CACHE_CONFIGS.keys())}"
        )
    return ALL_CACHE_CONFIGS[config_name]


def get_configs_by_cache_type(cache_type: CacheType) -> Dict[str, CacheConfig]:
    """Get all configs for a specific cache type."""
    return {
        name: config for name, config in ALL_CACHE_CONFIGS.items()
        if config.cache_type == cache_type
    }


def get_configs_by_element_type(element_type: str) -> Dict[str, CacheConfig]:
    """Get all configs for a specific element type."""
    return {
        name: config for name, config in ALL_CACHE_CONFIGS.items()
        if config.element_type == element_type
    }
