"""Tests for result type configuration helpers."""

import pytest

from config.result_config import (
    RESULT_CONFIGS,
    ResultTypeConfig,
    format_result_type_with_unit,
    get_config,
)


@pytest.mark.parametrize(
    ("config_key", "expected_suffix"),
    [
        ("Drifts_X", "_X"),
        ("Drifts_Y", "_Y"),
        ("Accelerations_X", "_UX"),
        ("Accelerations_Y", "_UY"),
        ("WallShears_V2", "_V2"),
        ("WallShears_V3", "_V3"),
    ],
)
def test_directional_variants_inherit_suffix(config_key: str, expected_suffix: str) -> None:
    """Variant configs should be generated with the correct suffix and metadata."""
    config = RESULT_CONFIGS[config_key]
    assert isinstance(config, ResultTypeConfig)
    assert config.direction_suffix == expected_suffix
    # Units and color schemes should come from the base spec.
    assert config.unit == RESULT_CONFIGS[config_key.split("_")[0]].unit
    assert config.color_scheme == "blue_orange"


def test_get_config_returns_default_for_unknown_key() -> None:
    """Unknown result types should fall back to the Drifts config."""
    default_config = RESULT_CONFIGS["Drifts"]
    assert get_config("TotallyUnknownType") == default_config


@pytest.mark.parametrize(
    ("result_type", "direction", "expected"),
    [
        ("Forces", None, "Story Forces [kN]"),
        ("Forces", "X", "Story Forces [kN] - X Direction"),
        ("Displacements", "Y", "Floor Displacements [mm] - Y Direction"),
        ("Drifts", "X", "Story Drifts [%] - X Direction"),
        ("Drifts", None, "Story Drifts [%]"),
        ("ColumnRotations", None, "Column Rotations [%]"),
        ("BeamRotations", None, "Beam Rotations [%]"),
        ("QuadRotations", None, "Quad Rotations [%]"),
    ],
)
def test_format_result_type_with_unit(result_type: str, direction: str, expected: str) -> None:
    """format_result_type_with_unit should include units for all result types."""
    assert format_result_type_with_unit(result_type, direction) == expected
