"""Registry for pushover importers and parsers.

Provides centralized lookup and instantiation of pushover processing classes.
This eliminates the need for explicit imports in calling code and makes it
easy to add new result types.

Usage:
    from processing.pushover_registry import PushoverRegistry
    
    # Get an importer class by type
    importer_class = PushoverRegistry.get_importer("wall")
    importer = importer_class(project_id, session, ...)
    
    # Get a parser class by type
    parser_class = PushoverRegistry.get_parser("beam")
    parser = parser_class(file_path)
    
    # Import all element results
    for result_type in PushoverRegistry.ELEMENT_TYPES:
        importer_class = PushoverRegistry.get_importer(result_type)
        ...
"""

from __future__ import annotations

from typing import Type, Dict, Optional, TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from pathlib import Path
    from .pushover_base_importer import BasePushoverImporter
    from .pushover_base_parser import BasePushoverParser

logger = logging.getLogger(__name__)


class PushoverRegistry:
    """Registry for pushover importer and parser classes.
    
    Provides lazy loading of classes to avoid circular imports and
    improve startup time.
    """
    
    # Result type categories
    GLOBAL_TYPES = frozenset({"global"})
    ELEMENT_TYPES = frozenset({"wall", "beam", "column", "column_shear"})
    JOINT_TYPES = frozenset({"soil_pressure", "vert_displacement", "joint"})
    CURVE_TYPES = frozenset({"curve"})
    
    ALL_TYPES = GLOBAL_TYPES | ELEMENT_TYPES | JOINT_TYPES | CURVE_TYPES
    
    # Maps result type to (module_name, class_name) for lazy loading
    _IMPORTER_MAP: Dict[str, tuple[str, str]] = {
        "global": ("pushover_global_importer", "PushoverGlobalImporter"),
        "wall": ("pushover_wall_importer", "PushoverWallImporter"),
        "beam": ("pushover_beam_importer", "PushoverBeamImporter"),
        "column": ("pushover_column_importer", "PushoverColumnImporter"),
        "column_shear": ("pushover_column_shear_importer", "PushoverColumnShearImporter"),
        "soil_pressure": ("pushover_soil_pressure_importer", "PushoverSoilPressureImporter"),
        "vert_displacement": ("pushover_vert_displacement_importer", "PushoverVertDisplacementImporter"),
        "joint": ("pushover_joint_importer", "PushoverJointImporter"),
        "curve": ("pushover_curve_importer", "PushoverImporter"),
    }
    
    _PARSER_MAP: Dict[str, tuple[str, str]] = {
        "global": ("pushover_global_parser", "PushoverGlobalParser"),
        "wall": ("pushover_wall_parser", "PushoverWallParser"),
        "beam": ("pushover_beam_parser", "PushoverBeamParser"),
        "column": ("pushover_column_parser", "PushoverColumnParser"),
        "column_shear": ("pushover_column_shear_parser", "PushoverColumnShearParser"),
        "soil_pressure": ("pushover_soil_pressure_parser", "PushoverSoilPressureParser"),
        "vert_displacement": ("pushover_vert_displacement_parser", "PushoverVertDisplacementParser"),
        "joint": ("pushover_joint_parser", "PushoverJointParser"),
        "curve": ("pushover_curve_parser", "PushoverParser"),
    }
    
    # Cache for loaded classes
    _importer_cache: Dict[str, Type] = {}
    _parser_cache: Dict[str, Type] = {}
    
    @classmethod
    def get_importer(cls, result_type: str) -> Optional[Type]:
        """Get importer class for a result type.
        
        Args:
            result_type: One of: global, wall, beam, column, column_shear,
                        soil_pressure, vert_displacement, joint, curve
        
        Returns:
            Importer class or None if not found
        """
        result_type = result_type.lower()
        
        if result_type in cls._importer_cache:
            return cls._importer_cache[result_type]
        
        if result_type not in cls._IMPORTER_MAP:
            logger.warning(f"Unknown importer type: {result_type}")
            return None
        
        module_name, class_name = cls._IMPORTER_MAP[result_type]
        
        try:
            module = __import__(f"processing.{module_name}", fromlist=[class_name])
            importer_class = getattr(module, class_name)
            cls._importer_cache[result_type] = importer_class
            return importer_class
        except (ImportError, AttributeError) as e:
            logger.error(f"Failed to load importer {class_name}: {e}")
            return None
    
    @classmethod
    def get_parser(cls, result_type: str) -> Optional[Type]:
        """Get parser class for a result type.
        
        Args:
            result_type: One of: global, wall, beam, column, column_shear,
                        soil_pressure, vert_displacement, joint, curve
        
        Returns:
            Parser class or None if not found
        """
        result_type = result_type.lower()
        
        if result_type in cls._parser_cache:
            return cls._parser_cache[result_type]
        
        if result_type not in cls._PARSER_MAP:
            logger.warning(f"Unknown parser type: {result_type}")
            return None
        
        module_name, class_name = cls._PARSER_MAP[result_type]
        
        try:
            module = __import__(f"processing.{module_name}", fromlist=[class_name])
            parser_class = getattr(module, class_name)
            cls._parser_cache[result_type] = parser_class
            return parser_class
        except (ImportError, AttributeError) as e:
            logger.error(f"Failed to load parser {class_name}: {e}")
            return None
    
    @classmethod
    def get_available_types(cls) -> list[str]:
        """Get list of all available result types."""
        return sorted(cls.ALL_TYPES)
    
    @classmethod
    def get_element_types(cls) -> list[str]:
        """Get list of element result types (wall, beam, column, etc.)."""
        return sorted(cls.ELEMENT_TYPES)
    
    @classmethod
    def get_joint_types(cls) -> list[str]:
        """Get list of joint result types (soil_pressure, vert_displacement, etc.)."""
        return sorted(cls.JOINT_TYPES)
    
    @classmethod
    def is_element_type(cls, result_type: str) -> bool:
        """Check if result type is an element type."""
        return result_type.lower() in cls.ELEMENT_TYPES
    
    @classmethod
    def is_joint_type(cls, result_type: str) -> bool:
        """Check if result type is a joint type."""
        return result_type.lower() in cls.JOINT_TYPES
    
    @classmethod
    def clear_cache(cls) -> None:
        """Clear the class cache (useful for testing)."""
        cls._importer_cache.clear()
        cls._parser_cache.clear()


# Convenience functions for common operations
def get_pushover_importer(result_type: str) -> Optional[Type]:
    """Get pushover importer class by type."""
    return PushoverRegistry.get_importer(result_type)


def get_pushover_parser(result_type: str) -> Optional[Type]:
    """Get pushover parser class by type."""
    return PushoverRegistry.get_parser(result_type)
