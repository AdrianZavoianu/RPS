"""Shared helpers for export workflows (direction parsing, filenames, configs)."""

from __future__ import annotations

from typing import Mapping

from config.result_config import RESULT_CONFIGS


def extract_direction(result_type: str, config) -> str:
    """Extract direction suffix from a result type name."""
    direction_suffix = getattr(config, "direction_suffix", "")
    if not direction_suffix:
        return ""

    if "_" in result_type:
        return result_type.split("_")[-1]
    return direction_suffix


def extract_base_type(result_type: str) -> str:
    """Return the base result type without the trailing direction."""
    if "_" in result_type:
        return result_type.rsplit("_", 1)[0]
    return result_type


def build_filename(result_type: str, format: str) -> str:
    """Build an export filename for the given format."""
    ext = "xlsx" if format == "excel" else "csv"
    return f"{result_type}.{ext}"


def get_result_config(result_type: str, configs: Mapping[str, object] = RESULT_CONFIGS):
    """Lookup a ResultConfig by name or raise ValueError."""
    config = configs.get(result_type)
    if not config:
        raise ValueError(f"Unknown result type: {result_type}")
    return config
