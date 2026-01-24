"""Tests for DataAccessService - facade for UI data access."""

import pytest
from unittest.mock import MagicMock, patch

from services.data_access import (
    DataAccessService,
    ResultSetInfo,
    ComparisonSetInfo,
    PushoverCaseInfo,
    PushoverCurvePointInfo,
    ElementInfo,
    StoryInfo,
    LoadCaseInfo,
)


class TestDTOs:
    """Tests for Data Transfer Objects."""

    def test_result_set_info_from_model(self):
        """Test ResultSetInfo.from_model conversion."""
        mock_model = MagicMock()
        mock_model.id = 1
        mock_model.name = "DES"
        mock_model.description = "Design earthquake"
        mock_model.analysis_type = "NLTHA"

        info = ResultSetInfo.from_model(mock_model)

        assert info.id == 1
        assert info.name == "DES"
        assert info.description == "Design earthquake"
        assert info.analysis_type == "NLTHA"

    def test_result_set_info_handles_missing_attributes(self):
        """Test ResultSetInfo handles models without optional attributes."""
        mock_model = MagicMock(spec=["id", "name"])
        mock_model.id = 1
        mock_model.name = "DES"

        info = ResultSetInfo.from_model(mock_model)

        assert info.id == 1
        assert info.name == "DES"
        assert info.description is None
        assert info.analysis_type is None

    def test_comparison_set_info_from_model(self):
        """Test ComparisonSetInfo.from_model conversion."""
        mock_rs1 = MagicMock()
        mock_rs1.id = 1
        mock_rs2 = MagicMock()
        mock_rs2.id = 2

        mock_model = MagicMock()
        mock_model.id = 10
        mock_model.name = "COM1"
        mock_model.result_sets = [mock_rs1, mock_rs2]
        mock_model.result_types = ["Drifts", "Forces"]

        info = ComparisonSetInfo.from_model(mock_model)

        assert info.id == 10
        assert info.name == "COM1"
        assert info.result_set_ids == [1, 2]
        assert info.result_types == ["Drifts", "Forces"]

    def test_pushover_case_info_from_model(self):
        """Test PushoverCaseInfo.from_model conversion."""
        mock_model = MagicMock()
        mock_model.id = 5
        mock_model.name = "Push_X+"
        mock_model.direction = "X"
        mock_model.result_set_id = 3

        info = PushoverCaseInfo.from_model(mock_model)

        assert info.id == 5
        assert info.name == "Push_X+"
        assert info.direction == "X"
        assert info.result_set_id == 3

    def test_pushover_curve_point_info_from_model(self):
        """Test PushoverCurvePointInfo.from_model conversion."""
        mock_model = MagicMock()
        mock_model.step_number = 5
        mock_model.base_shear = 1500.0
        mock_model.displacement = 25.5

        info = PushoverCurvePointInfo.from_model(mock_model)

        assert info.step_number == 5
        assert info.base_shear == 1500.0
        assert info.displacement == 25.5

    def test_element_info_from_model(self):
        """Test ElementInfo.from_model conversion."""
        mock_model = MagicMock()
        mock_model.id = 7
        mock_model.name = "P1"
        mock_model.element_type = "Wall"

        info = ElementInfo.from_model(mock_model)

        assert info.id == 7
        assert info.name == "P1"
        assert info.element_type == "Wall"

    def test_story_info_from_model(self):
        """Test StoryInfo.from_model conversion."""
        mock_model = MagicMock()
        mock_model.id = 3
        mock_model.name = "Level 5"
        mock_model.sort_order = 5

        info = StoryInfo.from_model(mock_model)

        assert info.id == 3
        assert info.name == "Level 5"
        assert info.sort_order == 5

    def test_load_case_info_from_model(self):
        """Test LoadCaseInfo.from_model conversion."""
        mock_model = MagicMock()
        mock_model.id = 12
        mock_model.name = "TH01"
        mock_model.case_type = "TimeHistory"

        info = LoadCaseInfo.from_model(mock_model)

        assert info.id == 12
        assert info.name == "TH01"
        assert info.case_type == "TimeHistory"


class TestDataAccessService:
    """Tests for DataAccessService methods."""

    @pytest.fixture
    def mock_session_factory(self):
        """Create a mock session factory."""
        mock_session = MagicMock()
        return MagicMock(return_value=mock_session)

    def test_init_stores_session_factory(self, mock_session_factory):
        """Test that service stores the session factory."""
        service = DataAccessService(mock_session_factory)
        assert service._session_factory is mock_session_factory

    def test_session_scope_creates_and_closes_session(self, mock_session_factory):
        """Test that session scope properly manages session lifecycle."""
        mock_session = mock_session_factory.return_value
        service = DataAccessService(mock_session_factory)

        with service._session_scope() as session:
            assert session is mock_session

        mock_session.close.assert_called_once()

    def test_get_result_set_names(self, mock_session_factory):
        """Test getting result set names by IDs."""
        mock_session = mock_session_factory.return_value

        mock_rs1 = MagicMock()
        mock_rs1.name = "DES"
        mock_rs2 = MagicMock()
        mock_rs2.name = "MCE"

        with patch("database.repository.ResultSetRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_id.side_effect = [mock_rs1, mock_rs2]

            service = DataAccessService(mock_session_factory)
            names = service.get_result_set_names([1, 2])

            assert names == {1: "DES", 2: "MCE"}

    def test_get_pushover_cases(self, mock_session_factory):
        """Test getting pushover cases for a result set."""
        mock_case1 = MagicMock()
        mock_case1.id = 1
        mock_case1.name = "Push_X+"
        mock_case1.direction = "X"
        mock_case1.result_set_id = 5

        mock_case2 = MagicMock()
        mock_case2.id = 2
        mock_case2.name = "Push_Y+"
        mock_case2.direction = "Y"
        mock_case2.result_set_id = 5

        with patch("database.repository.PushoverCaseRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_result_set.return_value = [mock_case1, mock_case2]

            service = DataAccessService(mock_session_factory)
            cases = service.get_pushover_cases(5)

            assert len(cases) == 2
            assert cases[0].name == "Push_X+"
            assert cases[1].name == "Push_Y+"
            assert all(isinstance(c, PushoverCaseInfo) for c in cases)

    def test_get_pushover_curve_data(self, mock_session_factory):
        """Test getting pushover curve data points."""
        mock_point1 = MagicMock()
        mock_point1.step_number = 0
        mock_point1.base_shear = 0.0
        mock_point1.displacement = 0.0

        mock_point2 = MagicMock()
        mock_point2.step_number = 1
        mock_point2.base_shear = 500.0
        mock_point2.displacement = 10.0

        with patch("database.repository.PushoverCaseRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_curve_data.return_value = [mock_point1, mock_point2]

            service = DataAccessService(mock_session_factory)
            points = service.get_pushover_curve_data(1)

            assert len(points) == 2
            assert points[0].step_number == 0
            assert points[1].base_shear == 500.0
            assert all(isinstance(p, PushoverCurvePointInfo) for p in points)

    def test_get_result_sets(self, mock_session_factory):
        """Test getting all result sets for a project."""
        mock_rs1 = MagicMock()
        mock_rs1.id = 1
        mock_rs1.name = "DES"
        mock_rs1.description = None
        mock_rs1.analysis_type = "NLTHA"

        with patch("database.repository.ResultSetRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_project.return_value = [mock_rs1]

            service = DataAccessService(mock_session_factory)
            result_sets = service.get_result_sets(project_id=1)

            assert len(result_sets) == 1
            assert result_sets[0].name == "DES"
            assert isinstance(result_sets[0], ResultSetInfo)


class TestDataAccessServiceIntegration:
    """Integration-style tests verifying service behavior patterns."""

    def test_multiple_calls_create_separate_sessions(self):
        """Test that each call creates a new session."""
        call_count = 0

        def session_factory():
            nonlocal call_count
            call_count += 1
            return MagicMock()

        service = DataAccessService(session_factory)

        # Make multiple calls
        with patch("database.repository.ResultSetRepository"):
            service.get_result_sets(1)
            service.get_result_sets(2)

        # Each call should create a new session
        assert call_count == 2

    def test_session_closed_even_on_exception(self):
        """Test that session is closed even if an exception occurs."""
        mock_session = MagicMock()
        mock_session_factory = MagicMock(return_value=mock_session)

        service = DataAccessService(mock_session_factory)

        with patch("database.repository.ResultSetRepository") as MockRepo:
            MockRepo.side_effect = Exception("Database error")

            with pytest.raises(Exception, match="Database error"):
                service.get_result_sets(1)

        # Session should still be closed
        mock_session.close.assert_called_once()
