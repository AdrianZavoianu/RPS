import pandas as pd
import pytest

from processing.pushover.pushover_wall_parser import PushoverWallParser


def _parser_with_quad_sheet(df: pd.DataFrame) -> PushoverWallParser:
    parser = PushoverWallParser.__new__(PushoverWallParser)
    parser._sheet_cache = {("Quad Strain Gauge - Rotation", 1, True): df}
    parser._results_cache = {}
    return parser


def test_quad_rotations_use_property_name_as_quad_label_when_available():
    parser = _parser_with_quad_sheet(
        pd.DataFrame(
            {
                "Story": ["L1", "L1", "L2", "L2"],
                "Name": [101.0, 101.0, 102.0, 102.0],
                "PropertyName": ["Q-A", "Q-A", "Q-B", "Q-B"],
                "Output Case": ["PUSH_X", "PUSH_X", "PUSH_X", "PUSH_X"],
                "StepType": ["Max", "Min", "Max", "Min"],
                "Rotation": [0.001, -0.003, 0.002, -0.004],
            }
        )
    )

    rotations = parser._extract_quad_rotations("X")

    assert list(rotations["Quad"]) == ["Q-A", "Q-B"]
    assert "Name" not in rotations.columns
    assert pytest.approx(rotations.loc[0, "PUSH_X"]) == 0.003
    assert pytest.approx(rotations.loc[1, "PUSH_X"]) == 0.004


def test_get_quads_falls_back_to_numeric_name_when_property_name_missing():
    parser = _parser_with_quad_sheet(
        pd.DataFrame(
            {
                "Story": ["L1", "L2"],
                "Name": [101.0, 102.0],
                "Output Case": ["PUSH_X", "PUSH_X"],
                "StepType": ["Max", "Max"],
                "Rotation": [0.001, 0.002],
            }
        )
    )

    assert parser.get_quads() == ["101", "102"]
