"""Tests for data parsing and conversion utilities."""

import pytest

from utils.data_utils import parse_percentage_value, parse_numeric_safe, format_value


class TestParsePercentageValue:
    """Tests for parse_percentage_value function."""

    def test_parses_percentage_string(self):
        """Should parse percentage strings correctly."""
        assert parse_percentage_value("1.23%") == 1.23
        assert parse_percentage_value("0.5%") == 0.5
        assert parse_percentage_value("100%") == 100.0

    def test_parses_percentage_string_with_spaces(self):
        """Should handle percentage strings with spaces."""
        assert parse_percentage_value("1.5 %") == 1.5

    def test_converts_decimal_to_percentage(self):
        """Should convert decimal values to percentage."""
        assert parse_percentage_value(0.0123) == 1.23
        assert parse_percentage_value(0.5) == 50.0
        assert parse_percentage_value(1.0) == 100.0

    def test_handles_zero(self):
        """Should handle zero values."""
        assert parse_percentage_value(0) == 0.0
        assert parse_percentage_value("0%") == 0.0

    def test_handles_negative_values(self):
        """Should handle negative values."""
        assert parse_percentage_value(-0.01) == -1.0
        assert parse_percentage_value("-1%") == -1.0

    def test_returns_zero_for_invalid_input(self):
        """Should return 0.0 for invalid input."""
        assert parse_percentage_value(None) == 0.0
        assert parse_percentage_value("invalid") == 0.0
        assert parse_percentage_value([1, 2, 3]) == 0.0


class TestParseNumericSafe:
    """Tests for parse_numeric_safe function."""

    def test_parses_valid_float(self):
        """Should parse valid float values."""
        assert parse_numeric_safe(1.5) == 1.5
        assert parse_numeric_safe(-3.14) == -3.14

    def test_parses_valid_int(self):
        """Should parse valid integer values."""
        assert parse_numeric_safe(42) == 42.0
        assert parse_numeric_safe(-10) == -10.0

    def test_parses_string_number(self):
        """Should parse numeric strings."""
        assert parse_numeric_safe("3.14") == 3.14
        assert parse_numeric_safe("-5") == -5.0

    def test_returns_default_for_none(self):
        """Should return default for None."""
        assert parse_numeric_safe(None) == 0.0
        assert parse_numeric_safe(None, default=99.0) == 99.0

    def test_returns_default_for_invalid_string(self):
        """Should return default for invalid strings."""
        assert parse_numeric_safe("not a number") == 0.0
        assert parse_numeric_safe("abc", default=-1.0) == -1.0

    def test_returns_default_for_invalid_type(self):
        """Should return default for invalid types."""
        assert parse_numeric_safe([1, 2, 3]) == 0.0
        assert parse_numeric_safe({"key": "value"}) == 0.0


class TestFormatValue:
    """Tests for format_value function."""

    def test_formats_with_decimal_places(self):
        """Should format with specified decimal places."""
        assert format_value(1.2345, 2) == "1.23"
        assert format_value(1.2345, 0) == "1"
        assert format_value(1.2345, 4) == "1.2345"

    def test_formats_with_unit(self):
        """Should append unit to formatted value."""
        assert format_value(1.5, 1, "%") == "1.5%"
        assert format_value(9.81, 2, " m/s²") == "9.81 m/s²"
        assert format_value(100, 0, " kN") == "100 kN"

    def test_formats_negative_values(self):
        """Should handle negative values."""
        assert format_value(-1.5, 1) == "-1.5"
        assert format_value(-100, 0, "%") == "-100%"

    def test_formats_zero(self):
        """Should handle zero values."""
        assert format_value(0, 2) == "0.00"
        assert format_value(0, 0, "%") == "0%"

    def test_empty_unit_by_default(self):
        """Should use empty unit by default."""
        assert format_value(1.0, 1) == "1.0"
