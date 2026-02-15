"""Tests for PushoverImporter - imports pushover curve data from Excel files."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

from processing.pushover.pushover_curve_importer import PushoverImporter
from processing.pushover.pushover_curve_parser import PushoverCurveData


class MockSession:
    """Mock SQLAlchemy session for testing."""
    def __init__(self):
        self.committed = False

    def commit(self):
        self.committed = True


class MockResultSet:
    """Mock ResultSet model for testing."""
    def __init__(self, id: int = 1, name: str = "Push_Test", analysis_type: str = None):
        self.id = id
        self.name = name
        self.analysis_type = analysis_type
        self.description = None


class TestPushoverImporterInit:
    """Tests for PushoverImporter initialization."""

    def test_creates_repositories(self):
        """Test that importer creates necessary repositories."""
        session = MockSession()

        with patch('processing.pushover.pushover_curve_importer.ProjectRepository'):
            with patch('processing.pushover.pushover_curve_importer.ResultSetRepository'):
                importer = PushoverImporter(session)

                assert importer.session == session
                assert importer.project_repo is not None
                assert importer.result_set_repo is not None


class TestGetOrCreateResultSet:
    """Tests for _get_or_create_result_set method."""

    def test_creates_new_result_set(self):
        """Test creating a new result set."""
        session = MockSession()
        mock_result_set = MockResultSet()

        with patch('processing.pushover.pushover_curve_importer.ProjectRepository'):
            with patch('processing.pushover.pushover_curve_importer.ResultSetRepository') as MockRepo:
                mock_repo = MockRepo.return_value
                mock_repo.check_duplicate.return_value = False
                mock_repo.get_or_create.return_value = mock_result_set

                importer = PushoverImporter(session)
                result = importer._get_or_create_result_set(
                    project_id=1,
                    result_set_name="Push_Test",
                    overwrite=False
                )

                assert result == mock_result_set
                assert result.analysis_type == 'Pushover'
                assert result.description == "Pushover analysis results"
                assert session.committed

    def test_raises_error_when_exists_and_no_overwrite(self):
        """Test that error is raised when result set exists and overwrite is False."""
        session = MockSession()

        with patch('processing.pushover.pushover_curve_importer.ProjectRepository'):
            with patch('processing.pushover.pushover_curve_importer.ResultSetRepository') as MockRepo:
                mock_repo = MockRepo.return_value
                mock_repo.check_duplicate.return_value = True

                importer = PushoverImporter(session)

                with pytest.raises(ValueError) as exc_info:
                    importer._get_or_create_result_set(
                        project_id=1,
                        result_set_name="Push_Existing",
                        overwrite=False
                    )

                assert "already exists" in str(exc_info.value)
                assert "overwrite=True" in str(exc_info.value)

    def test_overwrites_existing_result_set(self):
        """Test that existing result set is overwritten when overwrite=True."""
        session = MockSession()
        mock_result_set = MockResultSet()

        with patch('processing.pushover.pushover_curve_importer.ProjectRepository'):
            with patch('processing.pushover.pushover_curve_importer.ResultSetRepository') as MockRepo:
                mock_repo = MockRepo.return_value
                mock_repo.check_duplicate.return_value = True
                mock_repo.get_or_create.return_value = mock_result_set

                importer = PushoverImporter(session)
                result = importer._get_or_create_result_set(
                    project_id=1,
                    result_set_name="Push_Existing",
                    overwrite=True
                )

                # Should succeed without raising error
                assert result == mock_result_set


class TestImportPushoverFile:
    """Tests for import_pushover_file method."""

    def test_raises_file_not_found(self):
        """Test that FileNotFoundError is raised for missing file."""
        session = MockSession()

        with patch('processing.pushover.pushover_curve_importer.ProjectRepository'):
            with patch('processing.pushover.pushover_curve_importer.ResultSetRepository'):
                importer = PushoverImporter(session)

                with pytest.raises(FileNotFoundError) as exc_info:
                    importer.import_pushover_file(
                        file_path="nonexistent.xlsx",
                        project_id=1,
                        result_set_name="Push_Test",
                        base_story="Base"
                    )

                assert "nonexistent.xlsx" in str(exc_info.value)

    def test_filters_by_direction(self):
        """Test that curves are filtered by direction when specified."""
        session = MockSession()
        mock_result_set = MockResultSet()

        # Create mock curves with different directions
        curve_x = PushoverCurveData("Push_X+", "X")
        curve_x.add_point(0, 0.0, 0.0)
        curve_x.add_point(1, 10.0, 500.0)

        curve_y = PushoverCurveData("Push_Y+", "Y")
        curve_y.add_point(0, 0.0, 0.0)
        curve_y.add_point(1, 15.0, 600.0)

        all_curves = {"Push_X+": curve_x, "Push_Y+": curve_y}

        with patch('processing.pushover.pushover_curve_importer.ProjectRepository'):
            with patch('processing.pushover.pushover_curve_importer.ResultSetRepository') as MockRepo:
                mock_repo = MockRepo.return_value
                mock_repo.check_duplicate.return_value = False
                mock_repo.get_or_create.return_value = mock_result_set

                with patch('processing.pushover.pushover_curve_importer.PushoverParser') as MockParser:
                    mock_parser = MockParser.return_value
                    mock_parser.parse_curves.return_value = all_curves

                    with patch('processing.pushover.pushover_curve_importer.PushoverTransformer') as MockTransformer:
                        mock_transformer = MockTransformer.return_value
                        mock_transformer.transform_curves.return_value = []

                        with patch.object(Path, 'exists', return_value=True):
                            importer = PushoverImporter(session)
                            stats = importer.import_pushover_file(
                                file_path="test.xlsx",
                                project_id=1,
                                result_set_name="Push_Test",
                                base_story="Base",
                                direction="X"  # Filter to X only
                            )

                            # Verify only X direction curves were transformed
                            transform_call_args = mock_transformer.transform_curves.call_args[0]
                            filtered_curves = transform_call_args[0]
                            assert len(filtered_curves) == 1
                            assert "Push_X+" in filtered_curves

    def test_raises_error_when_no_curves_for_direction(self):
        """Test that ValueError is raised when no curves match direction."""
        session = MockSession()
        mock_result_set = MockResultSet()

        # Create mock curves only for X direction
        curve_x = PushoverCurveData("Push_X+", "X")
        all_curves = {"Push_X+": curve_x}

        with patch('processing.pushover.pushover_curve_importer.ProjectRepository'):
            with patch('processing.pushover.pushover_curve_importer.ResultSetRepository') as MockRepo:
                mock_repo = MockRepo.return_value
                mock_repo.check_duplicate.return_value = False
                mock_repo.get_or_create.return_value = mock_result_set

                with patch('processing.pushover.pushover_curve_importer.PushoverParser') as MockParser:
                    mock_parser = MockParser.return_value
                    mock_parser.parse_curves.return_value = all_curves

                    with patch.object(Path, 'exists', return_value=True):
                        importer = PushoverImporter(session)

                        with pytest.raises(ValueError) as exc_info:
                            importer.import_pushover_file(
                                file_path="test.xlsx",
                                project_id=1,
                                result_set_name="Push_Test",
                                base_story="Base",
                                direction="Y"  # Request Y but only X exists
                            )

                        assert "No curves found for direction 'Y'" in str(exc_info.value)

    def test_returns_correct_stats(self):
        """Test that import returns correct statistics."""
        session = MockSession()
        mock_result_set = MockResultSet(id=5, name="Push_Test")

        # Create mock curves
        curve_x = PushoverCurveData("Push_X+", "X")
        curve_x.add_point(0, 0.0, 0.0)
        curve_x.add_point(1, 10.0, 500.0)
        curve_x.add_point(2, 20.0, 1000.0)

        all_curves = {"Push_X+": curve_x}

        # Create mock pushover case with curve points
        mock_case = MagicMock()
        mock_case.curve_points = [MagicMock(), MagicMock(), MagicMock()]  # 3 points

        with patch('processing.pushover.pushover_curve_importer.ProjectRepository'):
            with patch('processing.pushover.pushover_curve_importer.ResultSetRepository') as MockRepo:
                mock_repo = MockRepo.return_value
                mock_repo.check_duplicate.return_value = False
                mock_repo.get_or_create.return_value = mock_result_set

                with patch('processing.pushover.pushover_curve_importer.PushoverParser') as MockParser:
                    mock_parser = MockParser.return_value
                    mock_parser.parse_curves.return_value = all_curves

                    with patch('processing.pushover.pushover_curve_importer.PushoverTransformer') as MockTransformer:
                        mock_transformer = MockTransformer.return_value
                        mock_transformer.transform_curves.return_value = [mock_case]

                        with patch.object(Path, 'exists', return_value=True):
                            importer = PushoverImporter(session)
                            stats = importer.import_pushover_file(
                                file_path="test.xlsx",
                                project_id=1,
                                result_set_name="Push_Test",
                                base_story="Base"
                            )

                            assert stats['result_set_id'] == 5
                            assert stats['result_set_name'] == "Push_Test"
                            assert stats['curves_imported'] == 1
                            assert stats['total_points'] == 3


class TestGetAvailableStories:
    """Tests for get_available_stories method."""

    def test_delegates_to_parser(self):
        """Test that get_available_stories delegates to parser."""
        session = MockSession()

        with patch('processing.pushover.pushover_curve_importer.ProjectRepository'):
            with patch('processing.pushover.pushover_curve_importer.ResultSetRepository'):
                with patch('processing.pushover.pushover_curve_importer.PushoverParser') as MockParser:
                    mock_parser = MockParser.return_value
                    mock_parser.get_available_stories.return_value = ['Base', 'L1', 'L2']

                    importer = PushoverImporter(session)
                    stories = importer.get_available_stories("test.xlsx")

                    assert stories == ['Base', 'L1', 'L2']
                    MockParser.assert_called_with("test.xlsx")
