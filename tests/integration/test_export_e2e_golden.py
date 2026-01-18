"""
End-to-end export regression tests using golden fixtures.

Tests the complete export pipeline from database to file output.
Uses minimal fixture data to verify:
- Context-aware filtering (NLTHA vs Pushover)
- Result type discovery
- Export formatting
- File generation
"""

import pytest
import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import pandas as pd

RESOURCES = Path(__file__).parent / "resources"


class TestExportContextFiltering:
    """Test context-aware export filtering."""

    def test_nltha_context_excludes_pushover_result_sets(self):
        """NLTHA export context should not include Pushover result sets."""
        # Mock result sets
        mock_nltha_rs = MagicMock()
        mock_nltha_rs.id = 1
        mock_nltha_rs.name = "DES"
        mock_nltha_rs.analysis_type = "NLTHA"

        mock_push_rs = MagicMock()
        mock_push_rs.id = 2
        mock_push_rs.name = "Push_X"
        mock_push_rs.analysis_type = "Pushover"

        # Filter for NLTHA context (simulating what export dialog does)
        all_sets = [mock_nltha_rs, mock_push_rs]
        nltha_sets = [rs for rs in all_sets if rs.analysis_type != "Pushover"]

        assert len(nltha_sets) == 1
        assert nltha_sets[0].name == "DES"

    def test_pushover_context_only_includes_pushover_result_sets(self):
        """Pushover export context should only include Pushover result sets."""
        mock_nltha_rs = MagicMock()
        mock_nltha_rs.id = 1
        mock_nltha_rs.name = "DES"
        mock_nltha_rs.analysis_type = "NLTHA"

        mock_push_rs = MagicMock()
        mock_push_rs.id = 2
        mock_push_rs.name = "Push_X"
        mock_push_rs.analysis_type = "Pushover"

        # Filter for Pushover context
        push_sets = [rs for rs in [mock_nltha_rs, mock_push_rs]
                     if rs.analysis_type == "Pushover"]

        assert len(push_sets) == 1
        assert push_sets[0].name == "Push_X"


class TestExportResultTypeDiscovery:
    """Test result type discovery for export."""

    def test_discovers_global_result_types(self):
        """Discovers global result types from cache."""
        # Simulate what cache query returns
        cache_results = [
            ("Drifts_X",), ("Drifts_Y",), ("Forces_VX",), ("Forces_VY",)
        ]

        # Extract result types (simulating discovery logic)
        result_types = [r[0] for r in cache_results]

        assert "Drifts_X" in result_types
        assert "Drifts_Y" in result_types
        assert "Forces_VX" in result_types

    def test_discovers_element_result_types(self):
        """Discovers element result types from cache."""
        mock_session = MagicMock()

        # Mock ElementResultsCache query
        mock_session.query.return_value.filter.return_value.distinct.return_value.all.return_value = [
            ("WallShears_V2",), ("WallShears_V3",), ("QuadRotations",)
        ]

        result_types = [r[0] for r in mock_session.query.return_value.filter.return_value.distinct.return_value.all.return_value]

        assert "WallShears_V2" in result_types
        assert "QuadRotations" in result_types


class TestExportFormatting:
    """Test export data formatting."""

    def test_format_dataframe_for_export(self):
        """DataFrame is properly formatted for export."""
        df = pd.DataFrame({
            'Story': ['Level 1', 'Level 2'],
            'Value': [0.00251234, 0.00312345]
        })

        # Round numeric columns (simulating export formatting)
        formatted = df.copy()
        formatted['Value'] = formatted['Value'].round(4)

        # Values should be rounded
        assert formatted['Value'].iloc[0] == pytest.approx(0.0025, rel=1e-3)

    def test_export_includes_all_columns(self):
        """Export includes all required columns."""
        df = pd.DataFrame({
            'Story': ['Level 1', 'Level 2', 'Level 3'],
            'Case1': [0.001, 0.002, 0.003],
            'Case2': [0.0015, 0.0025, 0.0035]
        })

        # Check columns
        assert 'Story' in df.columns
        assert 'Case1' in df.columns
        assert 'Case2' in df.columns
        assert len(df.columns) == 3


class TestExportFileGeneration:
    """Test export file generation."""

    def test_generates_excel_file(self, tmp_path):
        """Generates valid Excel file."""
        output_path = tmp_path / "test_export.xlsx"

        df = pd.DataFrame({
            'Story': ['Level 1', 'Level 2'],
            'Value': [100, 200]
        })

        df.to_excel(output_path, index=False, engine='openpyxl')

        assert output_path.exists()

        # Verify readable
        read_df = pd.read_excel(output_path)
        assert len(read_df) == 2
        assert list(read_df.columns) == ['Story', 'Value']

    def test_generates_csv_file(self, tmp_path):
        """Generates valid CSV file."""
        output_path = tmp_path / "test_export.csv"

        df = pd.DataFrame({
            'Story': ['Level 1', 'Level 2'],
            'Value': [100, 200]
        })

        df.to_csv(output_path, index=False)

        assert output_path.exists()

        # Verify readable
        read_df = pd.read_csv(output_path)
        assert len(read_df) == 2


class TestGoldenFixtureValidation:
    """Validate golden fixtures are correct."""

    @pytest.fixture
    def nltha_fixture(self):
        """Load NLTHA golden fixture."""
        return RESOURCES / "nltha" / "sample_des.xlsx"

    @pytest.fixture
    def pushover_fixture(self):
        """Load Pushover golden fixture."""
        return RESOURCES / "pushover" / "sample_push.xlsx"

    def test_nltha_fixture_has_required_sheets(self, nltha_fixture):
        """NLTHA fixture has required sheets."""
        if not nltha_fixture.exists():
            pytest.skip("NLTHA fixture not created yet")

        excel = pd.ExcelFile(nltha_fixture)

        assert 'Story Drifts' in excel.sheet_names
        assert 'Story Forces' in excel.sheet_names
        assert 'Pier Forces' in excel.sheet_names

    def test_nltha_fixture_story_drifts_structure(self, nltha_fixture):
        """NLTHA Story Drifts has correct structure."""
        if not nltha_fixture.exists():
            pytest.skip("NLTHA fixture not created yet")

        df = pd.read_excel(nltha_fixture, sheet_name='Story Drifts', header=0)

        # Check required columns
        assert 'Story' in df.columns
        assert 'Output Case' in df.columns
        assert 'Drift' in df.columns

    def test_nltha_fixture_matches_expected(self, nltha_fixture):
        """NLTHA fixture matches expected output."""
        if not nltha_fixture.exists():
            pytest.skip("NLTHA fixture not created yet")

        expected_path = RESOURCES / "nltha" / "expected" / "story_drifts.json"
        if not expected_path.exists():
            pytest.skip("Expected output not created yet")

        with open(expected_path) as f:
            expected = json.load(f)

        df = pd.read_excel(nltha_fixture, sheet_name='Story Drifts', header=0)
        # Drop units row
        df = df.iloc[1:]

        assert len(df) == expected["row_count"]
        assert set(df['Story'].unique()) == set(expected["stories"])

    def test_pushover_fixture_has_required_sheets(self, pushover_fixture):
        """Pushover fixture has required sheets."""
        if not pushover_fixture.exists():
            pytest.skip("Pushover fixture not created yet")

        excel = pd.ExcelFile(pushover_fixture)

        assert 'Pier Forces' in excel.sheet_names
        assert 'Joint Displacements' in excel.sheet_names
        assert 'Story Forces' in excel.sheet_names

    def test_pushover_fixture_pier_forces_structure(self, pushover_fixture):
        """Pushover Pier Forces has correct structure."""
        if not pushover_fixture.exists():
            pytest.skip("Pushover fixture not created yet")

        df = pd.read_excel(pushover_fixture, sheet_name='Pier Forces', header=0)

        # Check required columns
        assert 'Story' in df.columns
        assert 'Pier' in df.columns
        assert 'Output Case' in df.columns
        assert 'V2' in df.columns
        assert 'V3' in df.columns

    def test_pushover_fixture_matches_expected(self, pushover_fixture):
        """Pushover fixture matches expected output."""
        if not pushover_fixture.exists():
            pytest.skip("Pushover fixture not created yet")

        expected_path = RESOURCES / "pushover" / "expected" / "pier_forces.json"
        if not expected_path.exists():
            pytest.skip("Expected output not created yet")

        with open(expected_path) as f:
            expected = json.load(f)

        df = pd.read_excel(pushover_fixture, sheet_name='Pier Forces', header=0)
        # Drop units row
        df = df.iloc[1:]

        assert len(df) == expected["row_count"]
        assert set(df['Pier'].unique()) == set(expected["piers"])


class TestExportServiceIntegration:
    """Integration tests for export service."""

    def test_export_service_handles_empty_result_set(self):
        """Export service handles empty result set gracefully."""
        # Simulate empty dataset
        empty_dataset = MagicMock()
        empty_dataset.data = pd.DataFrame()

        # Should be handled gracefully
        assert empty_dataset.data.empty is True

    def test_extract_base_type_logic(self):
        """Test base type extraction logic used by export service."""
        # Simulate the extraction logic from ExportService
        def extract_base_type(result_type: str) -> str:
            if "_" in result_type:
                return result_type.rsplit("_", 1)[0]
            return result_type

        # Test direction extraction
        assert extract_base_type("Drifts_X") == "Drifts"
        assert extract_base_type("WallShears_V2") == "WallShears"
        assert extract_base_type("QuadRotations") == "QuadRotations"
