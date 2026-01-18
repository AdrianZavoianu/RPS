from types import SimpleNamespace

import pytest

from services.export_utils import (
    extract_direction,
    extract_base_type,
    build_filename,
    get_result_config,
)


def test_extract_direction_respects_config_suffix():
    cfg = SimpleNamespace(direction_suffix="X")
    assert extract_direction("Drifts_X", cfg) == "X"
    assert extract_direction("Drifts", cfg) == "X"


def test_extract_direction_directionless():
    cfg = SimpleNamespace(direction_suffix="")
    assert extract_direction("QuadRotations", cfg) == ""


def test_extract_base_type_splits_once():
    assert extract_base_type("Drifts_X") == "Drifts"
    assert extract_base_type("WallShears_V2") == "WallShears"
    assert extract_base_type("QuadRotations") == "QuadRotations"


def test_build_filename_handles_formats():
    assert build_filename("Foo", "excel") == "Foo.xlsx"
    assert build_filename("Foo", "csv") == "Foo.csv"


def test_get_result_config_known_type():
    # Drifts_X is defined in RESULT_CONFIGS
    cfg = get_result_config("Drifts_X")
    assert cfg is not None
    assert getattr(cfg, "name", None) == "Drifts_X"


def test_get_result_config_raises_for_unknown():
    with pytest.raises(ValueError):
        get_result_config("NotAResult")
