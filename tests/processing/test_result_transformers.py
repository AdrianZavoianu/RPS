"""Tests for result transformers - data transformation pipeline."""

import pytest
import pandas as pd

from processing.result_transformers import (
    ResultTransformer,
    GenericResultTransformer,
    QuadRotationTransformer,
    MinAxialTransformer,
    BeamRotationTransformer,
    SoilPressureTransformer,
    get_transformer,
    TRANSFORMERS,
)


class TestGenericResultTransformer:
    """Tests for GenericResultTransformer."""

    def test_filter_columns_by_direction_suffix(self):
        """Test that filter_columns keeps only columns with matching suffix."""
        transformer = GenericResultTransformer('Drifts')

        df = pd.DataFrame({
            'Story': ['L1', 'L2', 'L3'],
            'LoadCase1_X': [0.1, 0.2, 0.3],
            'LoadCase2_X': [0.15, 0.25, 0.35],
            'LoadCase1_Y': [0.05, 0.1, 0.15],  # Different suffix
        })

        result = transformer.filter_columns(df)

        # Should only keep _X columns (Drifts config has direction_suffix='_X')
        assert 'LoadCase1_X' in result.columns
        assert 'LoadCase2_X' in result.columns
        assert 'LoadCase1_Y' not in result.columns
        assert 'Story' not in result.columns

    def test_clean_column_names_extracts_load_case(self):
        """Test that clean_column_names extracts load case name."""
        transformer = GenericResultTransformer('Drifts')

        df = pd.DataFrame({
            '160Wil_DES_Global_TH01_X': [0.1, 0.2],
            '160Wil_DES_Global_TH02_X': [0.15, 0.25],
        })

        result = transformer.clean_column_names(df)

        assert list(result.columns) == ['TH01', 'TH02']

    def test_add_statistics_computes_avg_max_min(self):
        """Test that add_statistics adds computed columns."""
        transformer = GenericResultTransformer('Drifts')

        df = pd.DataFrame({
            'TH01': [0.1, 0.2, 0.3],
            'TH02': [0.15, 0.25, 0.35],
        })

        result = transformer.add_statistics(df)

        assert 'Avg' in result.columns
        assert 'Max' in result.columns
        assert 'Min' in result.columns

        # Check first row: avg of 0.1 and 0.15 = 0.125
        assert result.loc[0, 'Avg'] == pytest.approx(0.125)
        assert result.loc[0, 'Max'] == pytest.approx(0.15)
        assert result.loc[0, 'Min'] == pytest.approx(0.1)

    def test_transform_full_pipeline(self):
        """Test complete transformation pipeline."""
        transformer = GenericResultTransformer('Drifts')

        df = pd.DataFrame({
            '160Wil_DES_TH01_X': [0.1, 0.2, 0.3],
            '160Wil_DES_TH02_X': [0.15, 0.25, 0.35],
        })

        result = transformer.transform(df)

        # Should have cleaned names + statistics
        assert 'TH01' in result.columns
        assert 'TH02' in result.columns
        assert 'Avg' in result.columns
        assert 'Max' in result.columns
        assert 'Min' in result.columns


class TestQuadRotationTransformer:
    """Tests for QuadRotationTransformer."""

    def test_keeps_all_columns(self):
        """Test that filter_columns keeps all columns (no filtering)."""
        transformer = QuadRotationTransformer()

        df = pd.DataFrame({
            'Col1': [1, 2, 3],
            'Col2': [4, 5, 6],
            'Col3': [7, 8, 9],
        })

        result = transformer.filter_columns(df)

        assert len(result.columns) == 3
        assert list(result.columns) == ['Col1', 'Col2', 'Col3']

    def test_has_correct_result_type(self):
        """Test that transformer has correct result type."""
        transformer = QuadRotationTransformer()
        assert transformer.result_type == 'QuadRotations'


class TestMinAxialTransformer:
    """Tests for MinAxialTransformer."""

    def test_keeps_all_columns(self):
        """Test that filter_columns keeps all columns (no filtering)."""
        transformer = MinAxialTransformer()

        df = pd.DataFrame({
            'Col1': [1, 2, 3],
            'Col2': [4, 5, 6],
        })

        result = transformer.filter_columns(df)

        assert len(result.columns) == 2

    def test_has_correct_result_type(self):
        """Test that transformer has correct result type."""
        transformer = MinAxialTransformer()
        assert transformer.result_type == 'MinAxial'


class TestBeamRotationTransformer:
    """Tests for BeamRotationTransformer."""

    def test_keeps_all_columns(self):
        """Test that filter_columns keeps all columns."""
        transformer = BeamRotationTransformer()

        df = pd.DataFrame({
            'LC1': [0.01, 0.02],
            'LC2': [0.015, 0.025],
        })

        result = transformer.filter_columns(df)

        assert len(result.columns) == 2

    def test_has_correct_result_type(self):
        """Test that transformer has correct result type."""
        transformer = BeamRotationTransformer()
        assert transformer.result_type == 'BeamRotations_R3Plastic'


class TestSoilPressureTransformer:
    """Tests for SoilPressureTransformer."""

    def test_keeps_all_columns(self):
        """Test that filter_columns keeps all columns."""
        transformer = SoilPressureTransformer()

        df = pd.DataFrame({
            'Foundation1': [-100, -150],
            'Foundation2': [-120, -180],
        })

        result = transformer.filter_columns(df)

        assert len(result.columns) == 2

    def test_has_correct_result_type(self):
        """Test that transformer has correct result type."""
        transformer = SoilPressureTransformer()
        assert transformer.result_type == 'SoilPressures_Min'


class TestTransformerRegistry:
    """Tests for transformer registry and get_transformer function."""

    def test_registry_contains_common_types(self):
        """Test that registry contains common result types."""
        assert 'Drifts' in TRANSFORMERS
        assert 'Forces' in TRANSFORMERS
        assert 'QuadRotations' in TRANSFORMERS
        assert 'MinAxial' in TRANSFORMERS
        assert 'BeamRotations_R3Plastic' in TRANSFORMERS
        assert 'SoilPressures_Min' in TRANSFORMERS

    def test_get_transformer_returns_correct_type(self):
        """Test that get_transformer returns appropriate transformer."""
        drifts_transformer = get_transformer('Drifts')
        assert isinstance(drifts_transformer, GenericResultTransformer)
        assert drifts_transformer.result_type == 'Drifts'

        quad_transformer = get_transformer('QuadRotations')
        assert isinstance(quad_transformer, QuadRotationTransformer)

    def test_get_transformer_returns_default_for_unknown(self):
        """Test that get_transformer returns default for unknown type."""
        unknown_transformer = get_transformer('UnknownType')
        # Should return Drifts transformer as default
        assert unknown_transformer.result_type == 'Drifts'


class TestTransformerEdgeCases:
    """Edge case tests for transformers."""

    def test_handles_empty_dataframe(self):
        """Test that transformer handles empty DataFrame."""
        transformer = GenericResultTransformer('Drifts')

        df = pd.DataFrame()

        # Should not raise error
        result = transformer.filter_columns(df)
        assert len(result.columns) == 0

    def test_handles_non_numeric_values(self):
        """Test that add_statistics handles non-numeric values gracefully."""
        transformer = GenericResultTransformer('Drifts')

        df = pd.DataFrame({
            'TH01': [0.1, 0.2, 'N/A'],  # Contains non-numeric
            'TH02': [0.15, 0.25, 0.35],
        })

        result = transformer.add_statistics(df)

        # Should still have statistics columns
        assert 'Avg' in result.columns
        assert 'Max' in result.columns
        assert 'Min' in result.columns

        # First two rows should have valid statistics
        assert result.loc[0, 'Avg'] == pytest.approx(0.125)

    def test_handles_single_column(self):
        """Test that transformer handles single column DataFrame."""
        transformer = GenericResultTransformer('Drifts')

        df = pd.DataFrame({
            'TH01': [0.1, 0.2, 0.3],
        })

        result = transformer.add_statistics(df)

        # Avg, Max, Min should all equal the single column
        assert result.loc[0, 'Avg'] == pytest.approx(0.1)
        assert result.loc[0, 'Max'] == pytest.approx(0.1)
        assert result.loc[0, 'Min'] == pytest.approx(0.1)

    def test_clean_column_names_handles_no_underscores(self):
        """Test that clean_column_names handles columns without underscores."""
        transformer = GenericResultTransformer('Drifts')

        df = pd.DataFrame({
            'SimpleColumn_X': [0.1, 0.2],
        })

        result = transformer.clean_column_names(df)

        # Should extract 'SimpleColumn' as the load case name
        assert 'SimpleColumn' in result.columns
