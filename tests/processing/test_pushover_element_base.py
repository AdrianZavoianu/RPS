"""Tests for PushoverElementBaseImporter and v2 importers."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from processing.pushover_element_base import (
    PushoverElementBaseImporter,
    ResultTypeConfig,
)


class TestResultTypeConfig:
    """Tests for ResultTypeConfig dataclass."""

    def test_config_creation(self):
        """Test creating a ResultTypeConfig."""
        config = ResultTypeConfig(
            name='R2',
            attr_name='rotations_r2',
            cache_suffix='_R2',
            model_field='rotation',
            model_class=MagicMock,
        )
        assert config.name == 'R2'
        assert config.attr_name == 'rotations_r2'
        assert config.cache_suffix == '_R2'
        assert config.model_field == 'rotation'


class TestPushoverElementBaseImporter:
    """Tests for PushoverElementBaseImporter base class."""

    def test_init_sets_attributes(self):
        """Test that __init__ correctly sets all attributes."""
        mock_session = MagicMock()

        # Create a concrete subclass for testing
        class TestImporter(PushoverElementBaseImporter):
            def _get_element_type(self): return 'Test'
            def _create_parser(self): return MagicMock()
            def _get_story_mapping_sheet(self): return 'Sheet1'
            def _get_result_types(self): return []
            def _create_result_record(self, *args): return MagicMock()

        importer = TestImporter(
            project_id=1,
            session=mock_session,
            result_set_id=2,
            file_path=Path('test.xlsx'),
            selected_load_cases_x=['LC1', 'LC2'],
            selected_load_cases_y=['LC3'],
        )

        assert importer.project_id == 1
        assert importer.result_set_id == 2
        assert importer.file_path == Path('test.xlsx')
        assert importer.selected_load_cases_x == {'LC1', 'LC2'}
        assert importer.selected_load_cases_y == {'LC3'}
        assert importer.unique_name_story_map == {}

    def test_create_stats_dict_includes_result_types(self):
        """Test that _create_stats_dict includes all result types."""
        mock_session = MagicMock()

        class TestImporter(PushoverElementBaseImporter):
            def _get_element_type(self): return 'Test'
            def _create_parser(self): return MagicMock()
            def _get_story_mapping_sheet(self): return 'Sheet1'
            def _get_result_types(self):
                return [
                    ResultTypeConfig('R2', 'rotations_r2', '_R2', 'rotation', MagicMock),
                    ResultTypeConfig('R3', 'rotations_r3', '_R3', 'rotation', MagicMock),
                ]
            def _create_result_record(self, *args): return MagicMock()

        importer = TestImporter(
            project_id=1,
            session=mock_session,
            result_set_id=2,
            file_path=Path('test.xlsx'),
            selected_load_cases_x=['LC1'],
            selected_load_cases_y=['LC2'],
        )

        stats = importer._create_stats_dict()

        assert 'errors' in stats
        assert 'result_set_id' in stats
        assert 'x_r2' in stats
        assert 'y_r2' in stats
        assert 'x_r3' in stats
        assert 'y_r3' in stats


class TestPushoverBeamImporterV2:
    """Tests for the refactored beam importer."""

    def test_import(self):
        """Test that beam importer can be imported."""
        from processing.pushover_beam_importer_v2 import PushoverBeamImporterV2
        assert PushoverBeamImporterV2 is not None

    def test_get_element_type(self):
        """Test that element type is 'Beam'."""
        from processing.pushover_beam_importer_v2 import PushoverBeamImporterV2

        mock_session = MagicMock()
        importer = PushoverBeamImporterV2(
            project_id=1,
            session=mock_session,
            result_set_id=1,
            file_path=Path('test.xlsx'),
            selected_load_cases_x=['LC1'],
            selected_load_cases_y=[],
        )

        assert importer._get_element_type() == 'Beam'

    def test_get_cache_base_name(self):
        """Test cache base name is 'BeamRotations'."""
        from processing.pushover_beam_importer_v2 import PushoverBeamImporterV2

        mock_session = MagicMock()
        importer = PushoverBeamImporterV2(
            project_id=1,
            session=mock_session,
            result_set_id=1,
            file_path=Path('test.xlsx'),
            selected_load_cases_x=['LC1'],
            selected_load_cases_y=[],
        )

        assert importer._get_cache_base_name() == 'BeamRotations'

    def test_result_types_config(self):
        """Test that result types are configured correctly."""
        from processing.pushover_beam_importer_v2 import PushoverBeamImporterV2
        from database.models import BeamRotation

        mock_session = MagicMock()
        importer = PushoverBeamImporterV2(
            project_id=1,
            session=mock_session,
            result_set_id=1,
            file_path=Path('test.xlsx'),
            selected_load_cases_x=['LC1'],
            selected_load_cases_y=[],
        )

        result_types = importer._get_result_types()
        assert len(result_types) == 1

        config = result_types[0]
        assert config.name == 'rotations'
        assert config.attr_name == 'rotations'
        assert config.cache_suffix == ''
        assert config.model_field == 'r3_plastic'
        assert config.model_class == BeamRotation


class TestPushoverColumnImporterV2:
    """Tests for the refactored column importer."""

    def test_import(self):
        """Test that column importer can be imported."""
        from processing.pushover_column_importer_v2 import PushoverColumnImporterV2
        assert PushoverColumnImporterV2 is not None

    def test_get_element_type(self):
        """Test that element type is 'Column'."""
        from processing.pushover_column_importer_v2 import PushoverColumnImporterV2

        mock_session = MagicMock()
        importer = PushoverColumnImporterV2(
            project_id=1,
            session=mock_session,
            result_set_id=1,
            file_path=Path('test.xlsx'),
            selected_load_cases_x=['LC1'],
            selected_load_cases_y=[],
        )

        assert importer._get_element_type() == 'Column'

    def test_get_cache_base_name(self):
        """Test cache base name is 'ColumnRotations'."""
        from processing.pushover_column_importer_v2 import PushoverColumnImporterV2

        mock_session = MagicMock()
        importer = PushoverColumnImporterV2(
            project_id=1,
            session=mock_session,
            result_set_id=1,
            file_path=Path('test.xlsx'),
            selected_load_cases_x=['LC1'],
            selected_load_cases_y=[],
        )

        assert importer._get_cache_base_name() == 'ColumnRotations'

    def test_result_types_config(self):
        """Test that result types are configured correctly for R2 and R3."""
        from processing.pushover_column_importer_v2 import PushoverColumnImporterV2
        from database.models import ColumnRotation

        mock_session = MagicMock()
        importer = PushoverColumnImporterV2(
            project_id=1,
            session=mock_session,
            result_set_id=1,
            file_path=Path('test.xlsx'),
            selected_load_cases_x=['LC1'],
            selected_load_cases_y=[],
        )

        result_types = importer._get_result_types()
        assert len(result_types) == 2

        r2_config = result_types[0]
        assert r2_config.name == 'R2'
        assert r2_config.attr_name == 'rotations_r2'
        assert r2_config.cache_suffix == '_R2'
        assert r2_config.model_class == ColumnRotation

        r3_config = result_types[1]
        assert r3_config.name == 'R3'
        assert r3_config.attr_name == 'rotations_r3'
        assert r3_config.cache_suffix == '_R3'
        assert r3_config.model_class == ColumnRotation

    def test_cache_query_filters(self):
        """Test that cache query filters by direction."""
        from processing.pushover_column_importer_v2 import PushoverColumnImporterV2
        from database.models import ColumnRotation

        mock_session = MagicMock()
        importer = PushoverColumnImporterV2(
            project_id=1,
            session=mock_session,
            result_set_id=1,
            file_path=Path('test.xlsx'),
            selected_load_cases_x=['LC1'],
            selected_load_cases_y=[],
        )

        r2_config = importer._get_result_types()[0]
        filters = importer._get_cache_query_filters(r2_config, ColumnRotation)

        # Should return a filter condition
        assert len(filters) == 1


class TestBackwardCompatibility:
    """Tests for backward compatibility between v1 and v2 importers."""

    def test_beam_importer_alias_exists(self):
        """Test that v2 module exports PushoverBeamImporter alias."""
        from processing.pushover_beam_importer_v2 import PushoverBeamImporter
        from processing.pushover_beam_importer_v2 import PushoverBeamImporterV2
        assert PushoverBeamImporter is PushoverBeamImporterV2

    def test_column_importer_alias_exists(self):
        """Test that v2 module exports PushoverColumnImporter alias."""
        from processing.pushover_column_importer_v2 import PushoverColumnImporter
        from processing.pushover_column_importer_v2 import PushoverColumnImporterV2
        assert PushoverColumnImporter is PushoverColumnImporterV2

    def test_original_importers_still_work(self):
        """Test that original importers still exist and can be imported."""
        from processing.pushover_beam_importer import PushoverBeamImporter
        from processing.pushover_column_importer import PushoverColumnImporter

        assert PushoverBeamImporter is not None
        assert PushoverColumnImporter is not None
