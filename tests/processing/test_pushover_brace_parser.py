"""Tests for pushover brace force parsing."""

from pathlib import Path
from unittest.mock import patch

import pandas as pd

from processing.pushover.pushover_brace_parser import PushoverBraceParser


def _parser_with_sheet(df: pd.DataFrame) -> PushoverBraceParser:
    with patch("processing.pushover.pushover_brace_parser.pd.ExcelFile", return_value=object()):
        parser = PushoverBraceParser(Path("brace_results.xlsx"))
    parser._sheet_cache[("Element Forces - Braces", 1, True)] = df
    return parser


def test_parse_groups_min_and_max_axials_by_brace_story_and_case():
    df = pd.DataFrame(
        {
            "Story": ["Roof", "Roof", "Roof", "L1", "L1", "L1"],
            "Brace": ["B1", "B1", "B1", "B2", "B2", "B2"],
            "Output Case": ["Push_X+", "Push_X+", "Push_Y+", "Push_X+", "Push_X+", "Push_Y+"],
            "P": [10.0, -25.0, 7.0, 15.0, -5.0, -12.0],
        }
    )
    parser = _parser_with_sheet(df)

    results = parser.parse("X")

    assert results.axials is not None
    assert list(results.axials.columns) == ["Brace", "Story", "Output Case", "MinAxial", "MaxAxial"]

    b1 = results.axials[results.axials["Brace"] == "B1"].iloc[0]
    assert b1["Output Case"] == "Push_X+"
    assert b1["MinAxial"] == -25.0
    assert b1["MaxAxial"] == 10.0

    b2 = results.axials[results.axials["Brace"] == "B2"].iloc[0]
    assert b2["MinAxial"] == -5.0
    assert b2["MaxAxial"] == 15.0


def test_available_directions_and_output_cases_use_brace_sheet():
    df = pd.DataFrame(
        {
            "Story": ["Roof", "Roof", "Roof"],
            "Brace": ["B1", "B1", "B1"],
            "Output Case": ["Push_X+", "Push_Y+", "Push_XY"],
            "P": [1.0, 2.0, 3.0],
        }
    )
    parser = _parser_with_sheet(df)

    assert parser.get_available_directions() == ["XY", "X", "Y"]
    assert parser.get_output_cases("X") == ["Push_X+", "Push_XY"]
    assert parser.get_braces() == ["B1"]
