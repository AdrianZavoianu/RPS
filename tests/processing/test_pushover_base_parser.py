"""Tests for BasePushoverParser base class."""

import pytest
import pandas as pd
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass
from typing import List, Optional

from processing.pushover_base_parser import BasePushoverParser


@dataclass
class MockResults:
    """Mock results container for testing."""
    data: Optional[pd.DataFrame] = None
    direction: str = ""


class ConcretePushoverParser(BasePushoverParser):
    """Concrete implementation for testing abstract base class."""

    def _get_primary_sheet(self) -> str:
        return "Test Sheet"

    def parse(self, direction: str) -> MockResults:
        direction = self._validate_direction(direction)
        return MockResults(direction=direction)


class TestBasePushoverParserInit:
    """Test parser initialization."""

    def test_init_stores_file_path(self, tmp_path):
        """Parser stores file path."""
        # Create a minimal Excel file for ExcelFile to load
        excel_path = tmp_path / "test.xlsx"
        pd.DataFrame({"A": [1]}).to_excel(excel_path, index=False)

        parser = ConcretePushoverParser(excel_path)

        assert parser.file_path == excel_path

    def test_init_loads_excel_data(self, tmp_path):
        """Parser loads Excel file."""
        excel_path = tmp_path / "test.xlsx"
        pd.DataFrame({"A": [1]}).to_excel(excel_path, index=False)

        parser = ConcretePushoverParser(excel_path)

        assert parser.excel_data is not None
        assert hasattr(parser.excel_data, 'sheet_names')


class TestValidateDirection:
    """Test direction validation."""

    @pytest.fixture
    def parser(self, tmp_path):
        excel_path = tmp_path / "test.xlsx"
        pd.DataFrame({"A": [1]}).to_excel(excel_path, index=False)
        return ConcretePushoverParser(excel_path)

    def test_validates_x_direction(self, parser):
        """X direction is valid."""
        assert parser._validate_direction('X') == 'X'
        assert parser._validate_direction('x') == 'X'

    def test_validates_y_direction(self, parser):
        """Y direction is valid."""
        assert parser._validate_direction('Y') == 'Y'
        assert parser._validate_direction('y') == 'Y'

    def test_validates_xy_direction(self, parser):
        """XY direction is valid."""
        assert parser._validate_direction('XY') == 'XY'
        assert parser._validate_direction('xy') == 'XY'

    def test_rejects_invalid_direction(self, parser):
        """Invalid direction raises error."""
        with pytest.raises(ValueError, match="Invalid direction"):
            parser._validate_direction('Z')

        with pytest.raises(ValueError, match="Invalid direction"):
            parser._validate_direction('')


class TestReadSheet:
    """Test sheet reading functionality."""

    @pytest.fixture
    def excel_file(self, tmp_path):
        """Create test Excel file with multiple sheets."""
        excel_path = tmp_path / "test.xlsx"

        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            # Sheet with header and units row
            df = pd.DataFrame({
                'Story': ['Units', 'Level 1', 'Level 2'],
                'Value': ['kN', 100, 200]
            })
            df.to_excel(writer, sheet_name='Test Sheet', index=False)

            # Another sheet
            pd.DataFrame({'A': [1, 2, 3]}).to_excel(
                writer, sheet_name='Other Sheet', index=False
            )

        return excel_path

    def test_read_sheet_drops_units_row(self, excel_file):
        """Reading sheet drops units row by default."""
        parser = ConcretePushoverParser(excel_file)

        # Note: read_sheet uses header=1, so row 0 is the data header
        # and row 1 in the file becomes row 0 in the DataFrame (units row)
        # which is then dropped
        df = parser._read_sheet('Test Sheet')

        # After dropping units, should have the data rows
        assert len(df) == 1  # Only data rows remain after drop(0)

    def test_read_sheet_keeps_units_row_when_disabled(self, excel_file):
        """Reading sheet can keep units row."""
        parser = ConcretePushoverParser(excel_file)

        df = parser._read_sheet('Test Sheet', drop_units=False)

        assert len(df) == 2  # All rows including units

    def test_read_sheet_raises_for_missing_sheet(self, excel_file):
        """Reading missing sheet raises error."""
        parser = ConcretePushoverParser(excel_file)

        with pytest.raises(ValueError, match="Sheet 'Missing' not found"):
            parser._read_sheet('Missing')


class TestFilterByDirection:
    """Test direction filtering functionality."""

    @pytest.fixture
    def parser(self, tmp_path):
        excel_path = tmp_path / "test.xlsx"
        pd.DataFrame({"A": [1]}).to_excel(excel_path, index=False)
        return ConcretePushoverParser(excel_path)

    def test_filters_x_direction(self, parser):
        """Filters X direction cases."""
        df = pd.DataFrame({
            'Output Case': ['Push_X+', 'Push_Y+', 'Push_X-', 'Other'],
            'Value': [1, 2, 3, 4]
        })

        result = parser._filter_by_direction(df, 'X')

        assert len(result) == 2
        assert all('X' in case for case in result['Output Case'])

    def test_filters_y_direction(self, parser):
        """Filters Y direction cases."""
        df = pd.DataFrame({
            'Output Case': ['Push_X+', 'Push_Y+', 'Push_Y-'],
            'Value': [1, 2, 3]
        })

        result = parser._filter_by_direction(df, 'Y')

        assert len(result) == 2
        assert all('Y' in case for case in result['Output Case'])

    def test_filters_xy_direction(self, parser):
        """Filters XY (bi-directional) cases."""
        df = pd.DataFrame({
            'Output Case': ['Push_X+', 'Push_Y+', 'Push_XY+', 'Push_XY-'],
            'Value': [1, 2, 3, 4]
        })

        result = parser._filter_by_direction(df, 'XY')

        # XY filter requires BOTH X and Y in name
        assert len(result) == 2
        assert all('X' in case and 'Y' in case for case in result['Output Case'])

    def test_filter_is_case_insensitive(self, parser):
        """Direction filter is case insensitive."""
        df = pd.DataFrame({
            'Output Case': ['push_x+', 'PUSH_X-', 'Push_X'],
            'Value': [1, 2, 3]
        })

        result = parser._filter_by_direction(df, 'x')

        assert len(result) == 3


class TestAggregateMaxAbs:
    """Test max absolute aggregation."""

    @pytest.fixture
    def parser(self, tmp_path):
        excel_path = tmp_path / "test.xlsx"
        pd.DataFrame({"A": [1]}).to_excel(excel_path, index=False)
        return ConcretePushoverParser(excel_path)

    def test_aggregates_max_absolute_value(self, parser):
        """Takes absolute maximum across groups."""
        df = pd.DataFrame({
            'Element': ['P1', 'P1', 'P1', 'P1'],
            'Story': ['L1', 'L1', 'L1', 'L1'],
            'Output Case': ['Case1', 'Case1', 'Case2', 'Case2'],
            'Value': [10, -15, 5, -8]  # Max abs: Case1=15, Case2=8
        })

        result = parser._aggregate_max_abs(
            df,
            group_cols=['Element', 'Story', 'Output Case'],
            value_col='Value'
        )

        assert 'Case1' in result.columns
        assert 'Case2' in result.columns
        assert result['Case1'].iloc[0] == 15  # abs(-15)
        assert result['Case2'].iloc[0] == 8   # abs(-8)


class TestPreserveOrder:
    """Test order preservation utilities."""

    @pytest.fixture
    def parser(self, tmp_path):
        excel_path = tmp_path / "test.xlsx"
        pd.DataFrame({"A": [1]}).to_excel(excel_path, index=False)
        return ConcretePushoverParser(excel_path)

    def test_preserve_order_maintains_first_occurrence(self, parser):
        """Preserves first-occurrence order."""
        df = pd.DataFrame({
            'Story': ['L3', 'L1', 'L2', 'L1', 'L3']
        })

        order = parser._preserve_order(df, 'Story')

        assert order == ['L3', 'L1', 'L2']  # First occurrence order

    def test_restore_order_sorts_by_categorical(self, parser):
        """Restores categorical order."""
        df = pd.DataFrame({
            'Story': ['L2', 'L1', 'L3'],
            'Value': [2, 1, 3]
        })
        order = ['L1', 'L2', 'L3']

        result = parser._restore_order(df, 'Story', order)

        assert result['Story'].tolist() == ['L1', 'L2', 'L3']
        assert result['Value'].tolist() == [1, 2, 3]


class TestValidateSheetExists:
    """Test sheet existence validation."""

    def test_returns_true_for_existing_sheet(self, tmp_path):
        """Returns True for existing sheet."""
        excel_path = tmp_path / "test.xlsx"
        pd.DataFrame({"A": [1]}).to_excel(excel_path, sheet_name='MySheet', index=False)

        parser = ConcretePushoverParser(excel_path)

        assert parser.validate_sheet_exists('MySheet') is True

    def test_returns_false_for_missing_sheet(self, tmp_path):
        """Returns False for missing sheet."""
        excel_path = tmp_path / "test.xlsx"
        pd.DataFrame({"A": [1]}).to_excel(excel_path, index=False)

        parser = ConcretePushoverParser(excel_path)

        assert parser.validate_sheet_exists('NonExistent') is False


def _create_etabs_style_excel(path, sheet_name, data_rows):
    """Helper to create ETABS-style Excel file.

    ETABS format when read with header=1:
    - Row 0 in Excel: Table title (skipped by header=1)
    - Row 1 in Excel: Column names (becomes DataFrame headers)
    - Row 2 in Excel: Units row (becomes df[0], then dropped by parser)
    - Row 3+ in Excel: Actual data

    data_rows should be a list of dicts where:
    - data_rows[0] = units row values
    - data_rows[1:] = actual data rows
    """
    with pd.ExcelWriter(path, engine='openpyxl') as writer:
        headers = list(data_rows[0].keys())

        # Row 0: Table title (placeholder, skipped by header=1)
        # Row 1: Column names (becomes DataFrame headers)
        # Row 2+: Units row + data rows
        all_rows = []
        all_rows.append(headers)  # Row 0: title row (skipped)
        all_rows.append(headers)  # Row 1: column names (becomes headers)
        for row in data_rows:
            all_rows.append([row[h] for h in headers])  # Row 2+: units + data

        df = pd.DataFrame(all_rows)
        df.to_excel(writer, sheet_name=sheet_name, index=False, header=False)


class TestGetAvailableDirections:
    """Test direction detection from output cases."""

    def test_detects_x_direction(self, tmp_path):
        """Detects X direction from output cases."""
        excel_path = tmp_path / "test.xlsx"

        # ETABS format: row 0 = headers, row 1 = units, row 2+ = data
        _create_etabs_style_excel(excel_path, 'Test Sheet', [
            {'Column1': 'Text', 'Output Case': 'Text'},  # Units row
            {'Column1': 'Data', 'Output Case': 'Push_X+'},  # Data row
        ])

        parser = ConcretePushoverParser(excel_path)
        directions = parser.get_available_directions()

        assert 'X' in directions

    def test_detects_y_direction(self, tmp_path):
        """Detects Y direction from output cases."""
        excel_path = tmp_path / "test.xlsx"

        _create_etabs_style_excel(excel_path, 'Test Sheet', [
            {'Column1': 'Text', 'Output Case': 'Text'},
            {'Column1': 'Data', 'Output Case': 'Push_Y-'},
        ])

        parser = ConcretePushoverParser(excel_path)
        directions = parser.get_available_directions()

        assert 'Y' in directions

    def test_detects_both_directions(self, tmp_path):
        """Detects both X and Y directions."""
        excel_path = tmp_path / "test.xlsx"

        _create_etabs_style_excel(excel_path, 'Test Sheet', [
            {'Column1': 'Text', 'Output Case': 'Text'},
            {'Column1': 'Data', 'Output Case': 'Push_X+'},
            {'Column1': 'Data', 'Output Case': 'Push_Y+'},
        ])

        parser = ConcretePushoverParser(excel_path)
        directions = parser.get_available_directions()

        assert 'X' in directions
        assert 'Y' in directions

    def test_returns_empty_for_missing_sheet(self, tmp_path):
        """Returns empty list if primary sheet doesn't exist."""
        excel_path = tmp_path / "test.xlsx"
        pd.DataFrame({"A": [1]}).to_excel(excel_path, sheet_name='Other', index=False)

        parser = ConcretePushoverParser(excel_path)
        directions = parser.get_available_directions()

        assert directions == []


class TestGetOutputCases:
    """Test output case retrieval."""

    def test_gets_x_direction_cases(self, tmp_path):
        """Gets output cases for X direction."""
        excel_path = tmp_path / "test.xlsx"

        _create_etabs_style_excel(excel_path, 'Test Sheet', [
            {'Column1': 'Text', 'Output Case': 'Text'},
            {'Column1': 'D1', 'Output Case': 'Push_X+'},
            {'Column1': 'D2', 'Output Case': 'Push_X-'},
            {'Column1': 'D3', 'Output Case': 'Push_Y+'},
        ])

        parser = ConcretePushoverParser(excel_path)
        cases = parser.get_output_cases('X')

        assert len(cases) == 2
        assert 'Push_X+' in cases
        assert 'Push_X-' in cases
        assert 'Push_Y+' not in cases

    def test_returns_sorted_cases(self, tmp_path):
        """Returns cases in sorted order."""
        excel_path = tmp_path / "test.xlsx"

        _create_etabs_style_excel(excel_path, 'Test Sheet', [
            {'Column1': 'Text', 'Output Case': 'Text'},
            {'Column1': 'D1', 'Output Case': 'Push_X_B'},
            {'Column1': 'D2', 'Output Case': 'Push_X_A'},
        ])

        parser = ConcretePushoverParser(excel_path)
        cases = parser.get_output_cases('X')

        assert cases == ['Push_X_A', 'Push_X_B']
