"""Factory for pushover importers.

This module provides a centralized factory for creating pushover importers,
reducing the need to import individual importer classes throughout the codebase.

Usage:
    from processing.pushover.pushover_importer_factory import create_importer
    
    importer = create_importer(
        importer_type="beam_rotation",
        project_id=project_id,
        session=session,
        result_set_id=result_set_id,
        file_path=file_path,
        selected_load_cases_x=load_cases_x,
        selected_load_cases_y=load_cases_y,
        progress_callback=callback,
    )
    stats = importer.import_all()
"""

from __future__ import annotations

import importlib
import logging
from pathlib import Path
from typing import Callable, Dict, List, Optional, Type, TYPE_CHECKING

from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from processing.pushover.pushover_base_importer import BasePushoverImporter

logger = logging.getLogger(__name__)


# =============================================================================
# Importer Registry
# =============================================================================

# Maps importer type keys to (module_path, class_name) tuples
# Note: v2 importers use Template Method pattern for reduced duplication
IMPORTER_REGISTRY: Dict[str, tuple[str, str]] = {
    # Element importers (v2 - refactored)
    "wall": ("processing.pushover.pushover_wall_importer_v2", "PushoverWallImporter"),
    "column_rotation": ("processing.pushover.pushover_column_importer_v2", "PushoverColumnImporter"),
    "column_shear": ("processing.pushover.pushover_column_shear_importer_v2", "PushoverColumnShearImporter"),
    "beam_rotation": ("processing.pushover.pushover_beam_importer_v2", "PushoverBeamImporter"),
    
    # Joint importers
    "joint_displacement": ("processing.pushover.pushover_joint_importer", "PushoverJointImporter"),
    "soil_pressure": ("processing.pushover.pushover_soil_pressure_importer", "PushoverSoilPressureImporter"),
    "vertical_displacement": ("processing.pushover.pushover_vert_displacement_importer", "PushoverVertDisplacementImporter"),
    
    # Global/curve importers
    "global": ("processing.pushover.pushover_global_importer", "PushoverGlobalImporter"),
    "curve": ("processing.pushover.pushover_curve_importer", "PushoverImporter"),
}


# =============================================================================
# Factory Functions
# =============================================================================

def get_importer_class(importer_type: str) -> Type:
    """Get the importer class for a given type.
    
    Args:
        importer_type: Type key from IMPORTER_REGISTRY
        
    Returns:
        Importer class
        
    Raises:
        KeyError: If importer_type not found
        ImportError: If module cannot be imported
    """
    if importer_type not in IMPORTER_REGISTRY:
        available = ", ".join(sorted(IMPORTER_REGISTRY.keys()))
        raise KeyError(
            f"Unknown importer type: {importer_type}. "
            f"Available: {available}"
        )
    
    module_path, class_name = IMPORTER_REGISTRY[importer_type]
    
    try:
        module = importlib.import_module(module_path)
        return getattr(module, class_name)
    except (ImportError, AttributeError) as e:
        raise ImportError(
            f"Failed to load importer {class_name} from {module_path}: {e}"
        ) from e


def create_importer(
    importer_type: str,
    project_id: int,
    session: Session,
    result_set_id: int,
    file_path: Path,
    selected_load_cases_x: List[str],
    selected_load_cases_y: List[str],
    progress_callback: Optional[Callable[[str, int, int], None]] = None,
) -> "BasePushoverImporter":
    """Create a pushover importer instance.
    
    This is the primary factory function for creating importers.
    
    Args:
        importer_type: Type of importer (see IMPORTER_REGISTRY keys)
        project_id: ID of the project
        session: Database session
        result_set_id: ID of the result set to add results to
        file_path: Path to Excel file containing results
        selected_load_cases_x: List of selected load cases for X direction
        selected_load_cases_y: List of selected load cases for Y direction
        progress_callback: Optional callback for progress updates
        
    Returns:
        Configured importer instance
        
    Example:
        importer = create_importer(
            "beam_rotation",
            project_id=1,
            session=session,
            result_set_id=10,
            file_path=Path("results.xlsx"),
            selected_load_cases_x=["PX1", "PX2"],
            selected_load_cases_y=["PY1"],
        )
        stats = importer.import_all()
    """
    importer_class = get_importer_class(importer_type)
    
    return importer_class(
        project_id=project_id,
        session=session,
        result_set_id=result_set_id,
        file_path=file_path,
        selected_load_cases_x=selected_load_cases_x,
        selected_load_cases_y=selected_load_cases_y,
        progress_callback=progress_callback,
    )


def get_available_importers() -> List[str]:
    """Get list of available importer types.
    
    Returns:
        Sorted list of importer type keys
    """
    return sorted(IMPORTER_REGISTRY.keys())


def get_element_importers() -> List[str]:
    """Get list of element-based importer types."""
    return ["wall", "column_rotation", "column_shear", "beam_rotation"]


def get_joint_importers() -> List[str]:
    """Get list of joint-based importer types."""
    return ["joint_displacement", "soil_pressure", "vertical_displacement"]


def get_global_importers() -> List[str]:
    """Get list of global/story-based importer types."""
    return ["global", "curve"]


# =============================================================================
# Batch Import Support
# =============================================================================

def import_multiple(
    importer_types: List[str],
    project_id: int,
    session: Session,
    result_set_id: int,
    file_paths: Dict[str, Path],
    selected_load_cases_x: List[str],
    selected_load_cases_y: List[str],
    progress_callback: Optional[Callable[[str, int, int], None]] = None,
) -> Dict[str, Dict]:
    """Import multiple result types in sequence.
    
    Args:
        importer_types: List of importer types to run
        project_id: ID of the project
        session: Database session
        result_set_id: ID of the result set
        file_paths: Dict mapping importer_type to file path
        selected_load_cases_x: List of selected load cases for X direction
        selected_load_cases_y: List of selected load cases for Y direction
        progress_callback: Optional callback for progress updates
        
    Returns:
        Dict mapping importer_type to import statistics
        
    Example:
        stats = import_multiple(
            ["wall", "beam_rotation"],
            project_id=1,
            session=session,
            result_set_id=10,
            file_paths={
                "wall": Path("wall_results.xlsx"),
                "beam_rotation": Path("beam_results.xlsx"),
            },
            selected_load_cases_x=["PX1"],
            selected_load_cases_y=["PY1"],
        )
    """
    results = {}
    total = len(importer_types)
    
    for i, importer_type in enumerate(importer_types):
        if importer_type not in file_paths:
            logger.warning(f"No file path provided for {importer_type}, skipping")
            continue
        
        file_path = file_paths[importer_type]
        
        if progress_callback:
            progress_callback(
                f"Importing {importer_type}...",
                int((i / total) * 100),
                100
            )
        
        try:
            importer = create_importer(
                importer_type=importer_type,
                project_id=project_id,
                session=session,
                result_set_id=result_set_id,
                file_path=file_path,
                selected_load_cases_x=selected_load_cases_x,
                selected_load_cases_y=selected_load_cases_y,
                progress_callback=None,  # Don't forward to individual importers
            )
            results[importer_type] = importer.import_all()
            
        except Exception as e:
            logger.exception(f"Failed to import {importer_type}")
            results[importer_type] = {"error": str(e)}
    
    if progress_callback:
        progress_callback("Import complete", 100, 100)
    
    return results
