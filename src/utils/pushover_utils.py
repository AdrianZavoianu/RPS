"""Utilities for pushover analysis display and formatting."""

import logging
from typing import Dict

logger = logging.getLogger(__name__)


def create_pushover_shorthand_mapping(load_case_names: list, direction: str = None) -> Dict[str, str]:
    """
    Create shorthand mapping for pushover load case names.

    Uses permissive detection: any case containing 'X' or 'Y' (case-insensitive)
    Examples:
    - "Push Modal X" -> "Px1"
    - "Push-Mod-X+Ecc+" -> "Px1"
    - "Push Uniform Y" -> "Py1"

    Args:
        load_case_names: List of load case names
        direction: Direction ('X' or 'Y') - if None, will auto-detect from names

    Returns:
        Dictionary mapping full name to shorthand (e.g., "Push-Mod-X+Ecc+" -> "Px1")
    """
    logger.debug("create_pushover_shorthand_mapping called with %s load cases", len(load_case_names))
    logger.debug("Direction: %s", direction)
    logger.debug("Sample load cases: %s", load_case_names[:3] if len(load_case_names) > 3 else load_case_names)

    mapping = {}

    # Separate by direction if not specified
    if direction is None:
        # Permissive detection: check if X or Y is in the name
        # Exclude cases with BOTH X and Y (bi-directional cases handled separately)
        x_cases = []
        y_cases = []
        xy_cases = []

        for name in load_case_names:
            name_upper = str(name).upper()
            has_x = 'X' in name_upper
            has_y = 'Y' in name_upper

            if has_x and has_y:
                xy_cases.append(name)
            elif has_x:
                x_cases.append(name)
            elif has_y:
                y_cases.append(name)

        logger.debug("Found %s X cases, %s Y cases, %s XY cases", len(x_cases), len(y_cases), len(xy_cases))

        # Map X direction cases
        for idx, name in enumerate(sorted(x_cases), start=1):
            mapping[name] = f"Px{idx}"

        # Map Y direction cases
        for idx, name in enumerate(sorted(y_cases), start=1):
            mapping[name] = f"Py{idx}"

        # Map XY bi-directional cases
        for idx, name in enumerate(sorted(xy_cases), start=1):
            mapping[name] = f"Pxy{idx}"
    else:
        # Use specified direction
        prefix = f"P{direction.lower()}"
        for idx, name in enumerate(sorted(load_case_names), start=1):
            mapping[name] = f"{prefix}{idx}"

    logger.debug("Created mapping with %s entries", len(mapping))
    if mapping:
        logger.debug("Sample mapping: %s", list(mapping.items())[:2])

    return mapping


def get_reverse_mapping(mapping: Dict[str, str]) -> Dict[str, str]:
    """Get reverse mapping (shorthand -> full name)."""
    return {v: k for k, v in mapping.items()}


def is_pushover_result(result_type: str, category: str = None) -> bool:
    """
    Check if a result type is a pushover result.

    Args:
        result_type: Result type name
        category: Category name (e.g., "Pushover", "NLTHA")

    Returns:
        True if this is a pushover result
    """
    if category == "Pushover":
        return True

    # Fallback check based on result type name
    pushover_types = ["Curves", "AllCurves"]
    return result_type in pushover_types
