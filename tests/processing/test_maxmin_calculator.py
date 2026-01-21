"""Tests for processing.maxmin_calculator."""

import pandas as pd
import pytest

from processing.maxmin_calculator import (
    calculate_absolute_maxmin_drifts,
    extract_load_case_from_column,
)


def test_extract_load_case_from_column():
    assert extract_load_case_from_column("Max_TH01_X", "X") == "TH01"
    assert extract_load_case_from_column("Min_MCR1_Y", "Y") == "MCR1"


def test_calculate_absolute_maxmin_drifts_builds_expected_rows():
    df = pd.DataFrame(
        {
            "Max_TH01_X": [0.3, 0.2],
            "Min_TH01_X": [-0.1, -0.5],
            "Max_TH01_Y": [0.4, 0.2],
            "Min_TH01_Y": [-0.2, -0.6],
        }
    )

    result = calculate_absolute_maxmin_drifts(df)
    assert set(result.keys()) == {"X", "Y"}

    x_df = result["X"].sort_values("story_idx").reset_index(drop=True)
    assert x_df["load_case"].unique().tolist() == ["TH01"]
    assert x_df.loc[0, "absolute_max"] == pytest.approx(0.3)
    assert x_df.loc[0, "sign"] == "positive"
    assert x_df.loc[0, "original_max"] == pytest.approx(0.3)
    assert x_df.loc[0, "original_min"] == pytest.approx(-0.1)
    assert x_df.loc[1, "absolute_max"] == pytest.approx(0.5)
    assert x_df.loc[1, "sign"] == "negative"
    assert x_df.loc[1, "original_max"] == pytest.approx(0.2)
    assert x_df.loc[1, "original_min"] == pytest.approx(-0.5)

    y_df = result["Y"].sort_values("story_idx").reset_index(drop=True)
    assert y_df["load_case"].unique().tolist() == ["TH01"]
    assert y_df.loc[0, "absolute_max"] == pytest.approx(0.4)
    assert y_df.loc[0, "sign"] == "positive"
    assert y_df.loc[0, "original_max"] == pytest.approx(0.4)
    assert y_df.loc[0, "original_min"] == pytest.approx(-0.2)
    assert y_df.loc[1, "absolute_max"] == pytest.approx(0.6)
    assert y_df.loc[1, "sign"] == "negative"
    assert y_df.loc[1, "original_max"] == pytest.approx(0.2)
    assert y_df.loc[1, "original_min"] == pytest.approx(-0.6)
