"""Tests for pushover utility functions."""

import pytest
import pandas as pd

from utils.pushover_utils import (
    detect_direction,
    preserve_order,
    restore_categorical_order,
    create_pushover_shorthand_mapping,
    get_reverse_mapping,
    is_pushover_result,
)


class TestDetectDirection:
    """Tests for detect_direction function."""

    def test_detects_x_direction(self):
        """Test detection of X direction."""
        assert detect_direction("Push Modal X") == "X"
        assert detect_direction("Push_Mod_X+Ecc+") == "X"
        assert detect_direction("Push-X") == "X"
        assert detect_direction("pushover x direction") == "X"

    def test_detects_y_direction(self):
        """Test detection of Y direction."""
        assert detect_direction("Push Modal Y") == "Y"
        assert detect_direction("Push_Mod_Y-Ecc-") == "Y"
        assert detect_direction("Push-Y") == "Y"
        assert detect_direction("pushover y direction") == "Y"

    def test_detects_xy_bidirectional(self):
        """Test detection of XY bi-directional."""
        assert detect_direction("Push_XY+") == "XY"
        assert detect_direction("Push Modal XY") == "XY"
        assert detect_direction("Pushover X and Y") == "XY"

    def test_returns_unknown_for_no_direction(self):
        """Test unknown direction when no X or Y present."""
        assert detect_direction("Push Modal") == "Unknown"
        assert detect_direction("Pushover") == "Unknown"
        assert detect_direction("Static Load") == "Unknown"
        assert detect_direction("") == "Unknown"

    def test_case_insensitive(self):
        """Test that detection is case insensitive."""
        assert detect_direction("push modal x") == "X"
        assert detect_direction("PUSH MODAL X") == "X"
        assert detect_direction("Push Modal X") == "X"


class TestPreserveOrder:
    """Tests for preserve_order function."""

    def test_preserves_first_occurrence_order(self):
        """Test that order is preserved based on first occurrence."""
        df = pd.DataFrame({
            'Story': ['L3', 'L2', 'L1', 'L3', 'L2', 'L1'],
            'Value': [1, 2, 3, 4, 5, 6]
        })
        result = preserve_order(df, 'Story')
        assert result == ['L3', 'L2', 'L1']

    def test_returns_unique_values(self):
        """Test that only unique values are returned."""
        df = pd.DataFrame({
            'Story': ['A', 'A', 'B', 'B', 'C', 'C'],
            'Value': [1, 2, 3, 4, 5, 6]
        })
        result = preserve_order(df, 'Story')
        assert len(result) == 3
        assert set(result) == {'A', 'B', 'C'}


class TestRestoreCategoricalOrder:
    """Tests for restore_categorical_order function."""

    def test_sorts_by_categorical_order(self):
        """Test sorting by specified categorical order."""
        df = pd.DataFrame({
            'Story': ['L1', 'L3', 'L2'],
            'Value': [1, 2, 3]
        })
        order = ['L3', 'L2', 'L1']
        result = restore_categorical_order(df, 'Story', order)

        assert result['Story'].tolist() == ['L3', 'L2', 'L1']
        assert result['Value'].tolist() == [2, 3, 1]

    def test_preserves_other_columns(self):
        """Test that other columns are preserved."""
        df = pd.DataFrame({
            'Story': ['A', 'B', 'C'],
            'X': [1, 2, 3],
            'Y': ['a', 'b', 'c']
        })
        order = ['C', 'B', 'A']
        result = restore_categorical_order(df, 'Story', order)

        assert 'X' in result.columns
        assert 'Y' in result.columns
        assert result['X'].tolist() == [3, 2, 1]


class TestCreatePushoverShorthandMapping:
    """Tests for create_pushover_shorthand_mapping function."""

    def test_creates_x_direction_mapping(self):
        """Test mapping for X direction cases."""
        cases = ["Push_Mod_X+Ecc+", "Push_Mod_X-Ecc-"]
        mapping = create_pushover_shorthand_mapping(cases)

        assert "Push_Mod_X+Ecc+" in mapping
        assert "Push_Mod_X-Ecc-" in mapping
        assert mapping["Push_Mod_X+Ecc+"].startswith("Px")
        assert mapping["Push_Mod_X-Ecc-"].startswith("Px")

    def test_creates_y_direction_mapping(self):
        """Test mapping for Y direction cases."""
        cases = ["Push_Mod_Y+Ecc+", "Push_Mod_Y-Ecc-"]
        mapping = create_pushover_shorthand_mapping(cases)

        assert "Push_Mod_Y+Ecc+" in mapping
        assert "Push_Mod_Y-Ecc-" in mapping
        assert mapping["Push_Mod_Y+Ecc+"].startswith("Py")

    def test_separates_x_and_y_cases(self):
        """Test that X and Y cases are mapped separately."""
        cases = [
            "Push_Mod_X+Ecc+",
            "Push_Mod_Y+Ecc+",
            "Push_Mod_X-Ecc-",
            "Push_Mod_Y-Ecc-",
        ]
        mapping = create_pushover_shorthand_mapping(cases)

        x_mappings = [v for k, v in mapping.items() if v.startswith("Px")]
        y_mappings = [v for k, v in mapping.items() if v.startswith("Py")]

        assert len(x_mappings) == 2
        assert len(y_mappings) == 2

    def test_handles_xy_bidirectional_cases(self):
        """Test mapping for XY bi-directional cases."""
        cases = ["Push_XY+Ecc+", "Push_XY-Ecc-"]
        mapping = create_pushover_shorthand_mapping(cases)

        assert all(v.startswith("Pxy") for v in mapping.values())

    def test_sorts_cases_before_numbering(self):
        """Test that cases are sorted before numbering."""
        cases = ["Push_Z_X+", "Push_A_X+", "Push_M_X+"]
        mapping = create_pushover_shorthand_mapping(cases)

        # Sorted order should be A, M, Z -> Px1, Px2, Px3
        assert mapping["Push_A_X+"] == "Px1"
        assert mapping["Push_M_X+"] == "Px2"
        assert mapping["Push_Z_X+"] == "Px3"

    def test_uses_specified_direction(self):
        """Test mapping with explicit direction specified."""
        cases = ["Case1", "Case2", "Case3"]
        mapping = create_pushover_shorthand_mapping(cases, direction="X")

        assert all(v.startswith("Px") for v in mapping.values())

    def test_empty_input(self):
        """Test with empty input."""
        mapping = create_pushover_shorthand_mapping([])
        assert mapping == {}


class TestGetReverseMapping:
    """Tests for get_reverse_mapping function."""

    def test_reverses_mapping(self):
        """Test that mapping is correctly reversed."""
        original = {"Push_X+": "Px1", "Push_X-": "Px2"}
        reversed_map = get_reverse_mapping(original)

        assert reversed_map["Px1"] == "Push_X+"
        assert reversed_map["Px2"] == "Push_X-"

    def test_preserves_all_entries(self):
        """Test that all entries are preserved in reverse."""
        original = {"A": "1", "B": "2", "C": "3"}
        reversed_map = get_reverse_mapping(original)

        assert len(reversed_map) == len(original)


class TestIsPushoverResult:
    """Tests for is_pushover_result function."""

    def test_returns_true_for_pushover_category(self):
        """Test that Pushover category is detected."""
        assert is_pushover_result("Drifts", category="Pushover") is True
        assert is_pushover_result("Forces", category="Pushover") is True
        assert is_pushover_result("Anything", category="Pushover") is True

    def test_returns_false_for_nltha_category(self):
        """Test that NLTHA category is not detected as pushover."""
        assert is_pushover_result("Drifts", category="NLTHA") is False
        assert is_pushover_result("Forces", category="NLTHA") is False

    def test_detects_pushover_result_types(self):
        """Test detection of pushover-specific result types."""
        assert is_pushover_result("Curves") is True
        assert is_pushover_result("AllCurves") is True

    def test_returns_false_for_non_pushover_types(self):
        """Test that non-pushover types return False."""
        assert is_pushover_result("Drifts") is False
        assert is_pushover_result("Forces") is False
        assert is_pushover_result("WallShears") is False
