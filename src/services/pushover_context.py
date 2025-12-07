"""Shared helpers for pushover load-case normalization and shorthand mapping."""

from __future__ import annotations

import re
from typing import Dict, Iterable, List

from utils.pushover_utils import create_pushover_shorthand_mapping


def strip_direction_suffixes(load_case_keys: Iterable[str]) -> List[str]:
    """Remove direction suffixes from cache load-case keys (e.g., _UX/_UY/_VX/_VY)."""
    stripped = []
    seen = set()
    for name in load_case_keys:
        base = re.sub(r"_(UX|UY|UZ|VX|VY|VZ)$", "", str(name))
        if base not in seen:
            seen.add(base)
            stripped.append(base)
    return stripped


def extend_with_underscore_variants(mapping: Dict[str, str]) -> Dict[str, str]:
    """Add underscore variants (Push_Mod_X+Ecc+) for hyphenated load case names."""
    extended = dict(mapping)
    for full_name, shorthand in list(mapping.items()):
        underscore_variant = re.sub(r"(?<!Ecc)-(?!Ecc)", "_", full_name)
        if underscore_variant != full_name:
            extended[underscore_variant] = shorthand
    return extended


def build_pushover_mapping(load_case_keys: Iterable[str]) -> Dict[str, str]:
    """
    Build a mapping of full load case name -> shorthand (Px1, Py1), including underscore variants.

    Args:
        load_case_keys: Cache keys that may contain direction suffixes (_UX/_UY/_VX/_VY).
    """
    cleaned = strip_direction_suffixes(load_case_keys)
    base_mapping = create_pushover_shorthand_mapping(cleaned, direction=None)
    return extend_with_underscore_variants(base_mapping)
