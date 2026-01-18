"""Tests for PushoverParser - pushover curve extraction."""

import pytest
import pandas as pd
from io import BytesIO
from unittest.mock import patch, MagicMock

from processing.pushover_curve_parser import PushoverParser, PushoverCurveData


class TestPushoverCurveData:
    """Tests for PushoverCurveData container class."""

    def test_initialization(self):
        """Test PushoverCurveData initialization."""
        curve = PushoverCurveData("Push_X+", "X")

        assert curve.case_name == "Push_X+"
        assert curve.direction == "X"
        assert curve.step_numbers == []
        assert curve.displacements == []
        assert curve.base_shears == []

    def test_add_point(self):
        """Test adding points to curve."""
        curve = PushoverCurveData("Push_X+", "X")

        curve.add_point(step=0, displacement=0.0, shear=0.0)
        curve.add_point(step=1, displacement=10.5, shear=500.0)
        curve.add_point(step=2, displacement=25.3, shear=1200.0)

        assert len(curve.step_numbers) == 3
        assert curve.step_numbers == [0, 1, 2]
        assert curve.displacements == [0.0, 10.5, 25.3]
        assert curve.base_shears == [0.0, 500.0, 1200.0]

    def test_repr(self):
        """Test string representation."""
        curve = PushoverCurveData("Push_X+", "X")
        curve.add_point(0, 0.0, 0.0)
        curve.add_point(1, 10.0, 500.0)

        repr_str = repr(curve)
        assert "Push_X+" in repr_str
        assert "X" in repr_str
        assert "2" in repr_str  # 2 points


class TestPushoverParserMocked:
    """Tests for PushoverParser with mocked Excel data."""

    @pytest.fixture
    def mock_displacement_df(self):
        """Create mock Joint Displacements DataFrame."""
        return pd.DataFrame({
            'Output Case': ['Push_X+', 'Push_X+', 'Push_X+', 'Push_Y+', 'Push_Y+', 'Push_Y+'],
            'Step Number': [0, 1, 2, 0, 1, 2],
            'Ux': [0.0, 10.0, 25.0, 0.0, 2.0, 5.0],
            'Uy': [0.0, 1.0, 2.0, 0.0, 15.0, 35.0],
        })

    @pytest.fixture
    def mock_forces_df(self):
        """Create mock Story Forces DataFrame."""
        return pd.DataFrame({
            'Story': ['Base', 'Base', 'Base', 'Base', 'Base', 'Base'],
            'Output Case': ['Push_X+', 'Push_X+', 'Push_X+', 'Push_Y+', 'Push_Y+', 'Push_Y+'],
            'Location': ['Bottom', 'Bottom', 'Bottom', 'Bottom', 'Bottom', 'Bottom'],
            'Step Number': [0, 1, 2, 0, 1, 2],
            'VX': [0.0, 500.0, 1200.0, 0.0, 100.0, 250.0],
            'VY': [0.0, 50.0, 100.0, 0.0, 600.0, 1500.0],
        })

    def test_parse_displacements_x_direction(self, mock_displacement_df):
        """Test displacement parsing for X direction cases."""
        with patch.object(PushoverParser, '__init__', lambda self, fp: None):
            parser = PushoverParser.__new__(PushoverParser)
            parser.file_path = "test.xlsx"
            parser.excel_file = MagicMock()  # Mock the ExcelFile object

            with patch.object(pd, 'read_excel', return_value=mock_displacement_df):
                # Mock the drop method to return same df (skip units row logic)
                mock_displacement_df.drop = MagicMock(return_value=mock_displacement_df)

                result = parser._parse_displacements()

                # Should have Push_X+ with X direction
                assert 'Push_X+' in result
                steps, displacements, direction = result['Push_X+']
                assert direction == 'X'
                assert len(steps) == 3
                # Displacements should be normalized (subtract initial, take absolute)
                # Initial Ux=0.0, so normalized = [0, 10, 25]
                assert displacements[0] == 0.0
                assert displacements[1] == 10.0
                assert displacements[2] == 25.0

    def test_parse_displacements_y_direction(self, mock_displacement_df):
        """Test displacement parsing for Y direction cases."""
        with patch.object(PushoverParser, '__init__', lambda self, fp: None):
            parser = PushoverParser.__new__(PushoverParser)
            parser.file_path = "test.xlsx"
            parser.excel_file = MagicMock()

            with patch.object(pd, 'read_excel', return_value=mock_displacement_df):
                mock_displacement_df.drop = MagicMock(return_value=mock_displacement_df)

                result = parser._parse_displacements()

                # Should have Push_Y+ with Y direction
                assert 'Push_Y+' in result
                steps, displacements, direction = result['Push_Y+']
                assert direction == 'Y'
                # Uses Uy column: [0, 15, 35], normalized = [0, 15, 35]
                assert displacements[0] == 0.0
                assert displacements[1] == 15.0
                assert displacements[2] == 35.0

    def test_parse_base_shears_x_direction(self, mock_forces_df):
        """Test base shear parsing for X direction cases."""
        with patch.object(PushoverParser, '__init__', lambda self, fp: None):
            parser = PushoverParser.__new__(PushoverParser)
            parser.file_path = "test.xlsx"
            parser.excel_file = MagicMock()

            with patch.object(pd, 'read_excel', return_value=mock_forces_df):
                mock_forces_df.drop = MagicMock(return_value=mock_forces_df)

                result = parser._parse_base_shears("Base")

                assert 'Push_X+' in result
                steps, shears = result['Push_X+']
                # Uses VX column (absolute): [0, 500, 1200]
                assert shears[0] == 0.0
                assert shears[1] == 500.0
                assert shears[2] == 1200.0

    def test_parse_base_shears_y_direction(self, mock_forces_df):
        """Test base shear parsing for Y direction cases."""
        with patch.object(PushoverParser, '__init__', lambda self, fp: None):
            parser = PushoverParser.__new__(PushoverParser)
            parser.file_path = "test.xlsx"
            parser.excel_file = MagicMock()

            with patch.object(pd, 'read_excel', return_value=mock_forces_df):
                mock_forces_df.drop = MagicMock(return_value=mock_forces_df)

                result = parser._parse_base_shears("Base")

                assert 'Push_Y+' in result
                steps, shears = result['Push_Y+']
                # Uses VY column (absolute): [0, 600, 1500]
                assert shears[0] == 0.0
                assert shears[1] == 600.0
                assert shears[2] == 1500.0

    def test_merge_data(self):
        """Test merging displacement and shear data."""
        with patch.object(PushoverParser, '__init__', lambda self, fp: None):
            parser = PushoverParser.__new__(PushoverParser)

            displacement_data = {
                'Push_X+': ([0, 1, 2], [0.0, 10.0, 25.0], 'X'),
                'Push_Y+': ([0, 1, 2], [0.0, 15.0, 35.0], 'Y'),
            }
            shear_data = {
                'Push_X+': ([0, 1, 2], [0.0, 500.0, 1200.0]),
                'Push_Y+': ([0, 1, 2], [0.0, 600.0, 1500.0]),
            }

            result = parser._merge_data(displacement_data, shear_data)

            # Should have both curves
            assert 'Push_X+' in result
            assert 'Push_Y+' in result

            # Check X curve data
            x_curve = result['Push_X+']
            assert isinstance(x_curve, PushoverCurveData)
            assert x_curve.direction == 'X'
            assert len(x_curve.step_numbers) == 3
            assert x_curve.displacements == [0.0, 10.0, 25.0]
            assert x_curve.base_shears == [0.0, 500.0, 1200.0]

    def test_merge_data_skips_unmatched_cases(self):
        """Test that merge skips cases without matching shear data."""
        with patch.object(PushoverParser, '__init__', lambda self, fp: None):
            parser = PushoverParser.__new__(PushoverParser)

            displacement_data = {
                'Push_X+': ([0, 1], [0.0, 10.0], 'X'),
                'Push_NoMatch': ([0, 1], [0.0, 5.0], 'X'),
            }
            shear_data = {
                'Push_X+': ([0, 1], [0.0, 500.0]),
                # Push_NoMatch not present in shear data
            }

            result = parser._merge_data(displacement_data, shear_data)

            assert 'Push_X+' in result
            assert 'Push_NoMatch' not in result


class TestPushoverParserEdgeCases:
    """Edge case tests for PushoverParser."""

    def test_handles_empty_displacement_data(self):
        """Test handling of empty displacement results."""
        with patch.object(PushoverParser, '__init__', lambda self, fp: None):
            parser = PushoverParser.__new__(PushoverParser)

            displacement_data = {}
            shear_data = {'Push_X+': ([0, 1], [0.0, 500.0])}

            result = parser._merge_data(displacement_data, shear_data)
            assert result == {}

    def test_handles_empty_shear_data(self):
        """Test handling of empty shear results."""
        with patch.object(PushoverParser, '__init__', lambda self, fp: None):
            parser = PushoverParser.__new__(PushoverParser)

            displacement_data = {'Push_X+': ([0, 1], [0.0, 10.0], 'X')}
            shear_data = {}

            result = parser._merge_data(displacement_data, shear_data)
            assert result == {}

    def test_handles_mismatched_step_counts(self):
        """Test handling when step counts don't match."""
        with patch.object(PushoverParser, '__init__', lambda self, fp: None):
            parser = PushoverParser.__new__(PushoverParser)

            # Displacement has 3 steps, shear has 2
            displacement_data = {
                'Push_X+': ([0, 1, 2], [0.0, 10.0, 25.0], 'X'),
            }
            shear_data = {
                'Push_X+': ([0, 1], [0.0, 500.0]),
            }

            result = parser._merge_data(displacement_data, shear_data)

            # Should only include matching steps
            x_curve = result['Push_X+']
            assert len(x_curve.step_numbers) == 2
            assert x_curve.step_numbers == [0, 1]

    def test_normalize_displacements_with_nonzero_initial(self):
        """Test displacement normalization when initial value is non-zero."""
        with patch.object(PushoverParser, '__init__', lambda self, fp: None):
            parser = PushoverParser.__new__(PushoverParser)
            parser.file_path = "test.xlsx"
            parser.excel_file = MagicMock()

            # Create DataFrame with non-zero initial displacement
            df = pd.DataFrame({
                'Output Case': ['Push_X+', 'Push_X+', 'Push_X+'],
                'Step Number': [0, 1, 2],
                'Ux': [5.0, 15.0, 30.0],  # Initial is 5.0
                'Uy': [0.0, 1.0, 2.0],
            })

            with patch.object(pd, 'read_excel', return_value=df):
                df.drop = MagicMock(return_value=df)

                result = parser._parse_displacements()

                steps, displacements, direction = result['Push_X+']
                # Normalized: [5-5, 15-5, 30-5] = [0, 10, 25]
                assert displacements[0] == 0.0
                assert displacements[1] == 10.0
                assert displacements[2] == 25.0
