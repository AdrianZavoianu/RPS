"""Tests for time_history_importer.py"""

import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session

from processing.time_history_importer import (
    TimeHistoryImporter,
    TimeSeriesRepository,
)
from processing.time_history_parser import TimeSeriesData, TimeHistoryParseResult
from database.models import (
    Project,
    ResultSet,
    Story,
    TimeSeriesGlobalCache,
)


class TestTimeHistoryImporterInit:
    """Tests for TimeHistoryImporter initialization."""

    def test_stores_session_and_ids(self, db_session, sample_project, sample_result_set):
        """Importer should store session and IDs."""
        importer = TimeHistoryImporter(
            session=db_session,
            project_id=sample_project.id,
            result_set_id=sample_result_set.id,
        )

        assert importer.session == db_session
        assert importer.project_id == sample_project.id
        assert importer.result_set_id == sample_result_set.id
        assert importer.progress_callback is None

    def test_stores_progress_callback(self, db_session, sample_project, sample_result_set):
        """Importer should store optional progress callback."""
        callback = MagicMock()
        importer = TimeHistoryImporter(
            session=db_session,
            project_id=sample_project.id,
            result_set_id=sample_result_set.id,
            progress_callback=callback,
        )

        assert importer.progress_callback == callback

    def test_initializes_empty_story_lookup(self, db_session, sample_project, sample_result_set):
        """Importer should initialize empty story lookup."""
        importer = TimeHistoryImporter(
            session=db_session,
            project_id=sample_project.id,
            result_set_id=sample_result_set.id,
        )

        assert importer._story_lookup == {}


class TestEnsureStories:
    """Tests for _ensure_stories method."""

    def test_creates_new_stories(self, db_session, sample_project, sample_result_set):
        """Should create stories that don't exist."""
        importer = TimeHistoryImporter(
            session=db_session,
            project_id=sample_project.id,
            result_set_id=sample_result_set.id,
        )

        importer._ensure_stories(["Ground", "Level 1", "Roof"])

        # Should have created stories
        assert "Ground" in importer._story_lookup
        assert "Level 1" in importer._story_lookup
        assert "Roof" in importer._story_lookup

        # Verify stories exist in database
        stories = db_session.query(Story).filter_by(project_id=sample_project.id).all()
        assert len(stories) == 3

    def test_reuses_existing_stories(self, db_session, sample_project, sample_result_set, sample_stories):
        """Should reuse stories that already exist."""
        importer = TimeHistoryImporter(
            session=db_session,
            project_id=sample_project.id,
            result_set_id=sample_result_set.id,
        )

        # sample_stories creates 5 stories
        importer._ensure_stories(["Ground", "Level 1"])

        # Should have mapped to existing story IDs
        assert importer._story_lookup["Ground"] == sample_stories[0].id
        assert importer._story_lookup["Level 1"] == sample_stories[1].id

    def test_creates_only_missing_stories(self, db_session, sample_project, sample_result_set, sample_stories):
        """Should only create stories that don't exist."""
        importer = TimeHistoryImporter(
            session=db_session,
            project_id=sample_project.id,
            result_set_id=sample_result_set.id,
        )

        # sample_stories has Ground, Level 1, Level 2, Level 3, Roof
        # New story is "Basement"
        importer._ensure_stories(["Ground", "Basement"])

        # Should have 6 stories now (5 original + 1 new)
        stories = db_session.query(Story).filter_by(project_id=sample_project.id).all()
        assert len(stories) == 6


class TestImportSeries:
    """Tests for _import_series method."""

    def test_imports_time_series_to_cache(
        self, db_session, sample_project, sample_result_set, sample_stories
    ):
        """Should import time series data to TimeSeriesGlobalCache."""
        importer = TimeHistoryImporter(
            session=db_session,
            project_id=sample_project.id,
            result_set_id=sample_result_set.id,
        )

        # Setup story lookup
        importer._story_lookup = {s.name: s.id for s in sample_stories}

        # Create test data
        series_list = [
            TimeSeriesData(
                story="Ground",
                direction="X",
                time_steps=[0.0, 0.01, 0.02],
                values=[0.0, 0.5, 1.0],
                story_sort_order=0,
            )
        ]

        count = importer._import_series(series_list, "TH01", "Drifts", "X")

        assert count == 1

        # Verify data in database
        cache_entry = db_session.query(TimeSeriesGlobalCache).first()
        assert cache_entry is not None
        assert cache_entry.load_case_name == "TH01"
        assert cache_entry.result_type == "Drifts"
        assert cache_entry.direction == "X"
        assert cache_entry.time_steps == [0.0, 0.01, 0.02]
        assert cache_entry.values == [0.0, 0.5, 1.0]

    def test_updates_existing_entry(
        self, db_session, sample_project, sample_result_set, sample_stories
    ):
        """Should update existing cache entry if duplicate."""
        importer = TimeHistoryImporter(
            session=db_session,
            project_id=sample_project.id,
            result_set_id=sample_result_set.id,
        )
        importer._story_lookup = {s.name: s.id for s in sample_stories}

        # Import initial data
        series_list = [
            TimeSeriesData(
                story="Ground",
                direction="X",
                time_steps=[0.0, 0.01],
                values=[0.0, 0.5],
                story_sort_order=0,
            )
        ]
        importer._import_series(series_list, "TH01", "Drifts", "X")
        db_session.flush()

        # Import updated data
        updated_series = [
            TimeSeriesData(
                story="Ground",
                direction="X",
                time_steps=[0.0, 0.01, 0.02],
                values=[0.0, 0.6, 1.2],
                story_sort_order=0,
            )
        ]
        count = importer._import_series(updated_series, "TH01", "Drifts", "X")

        assert count == 1

        # Should still have only 1 entry
        entries = db_session.query(TimeSeriesGlobalCache).all()
        assert len(entries) == 1

        # Values should be updated
        assert entries[0].values == [0.0, 0.6, 1.2]

    def test_skips_unknown_stories(
        self, db_session, sample_project, sample_result_set, sample_stories
    ):
        """Should skip series with unknown story names."""
        importer = TimeHistoryImporter(
            session=db_session,
            project_id=sample_project.id,
            result_set_id=sample_result_set.id,
        )
        # Only map Ground
        importer._story_lookup = {"Ground": sample_stories[0].id}

        series_list = [
            TimeSeriesData("Ground", "X", [0.0], [0.1], 0),
            TimeSeriesData("Unknown Story", "X", [0.0], [0.2], 1),
        ]

        count = importer._import_series(series_list, "TH01", "Drifts", "X")

        assert count == 1  # Only Ground was imported


class TestImportFile:
    """Tests for import_file method."""

    def test_imports_all_result_types(
        self, db_session, sample_project, sample_result_set, sample_stories
    ):
        """Should import all result types from parsed data."""
        importer = TimeHistoryImporter(
            session=db_session,
            project_id=sample_project.id,
            result_set_id=sample_result_set.id,
        )

        # Create mock parse result
        mock_result = TimeHistoryParseResult(
            load_case_name="TH01",
            drifts_x=[TimeSeriesData("Ground", "X", [0.0], [0.1], 0)],
            drifts_y=[TimeSeriesData("Ground", "Y", [0.0], [0.05], 0)],
            forces_x=[TimeSeriesData("Ground", "X", [0.0], [100], 0)],
            forces_y=[TimeSeriesData("Ground", "Y", [0.0], [50], 0)],
            displacements_x=[TimeSeriesData("Ground", "X", [0.0], [10], 0)],
            displacements_y=[TimeSeriesData("Ground", "Y", [0.0], [5], 0)],
            accelerations_x=[TimeSeriesData("Ground", "X", [0.0], [1000], 0)],
            accelerations_y=[TimeSeriesData("Ground", "Y", [0.0], [500], 0)],
            stories=["Ground"],
        )

        with patch("processing.time_history_importer.TimeHistoryParser") as MockParser:
            MockParser.return_value.parse.return_value = mock_result

            count = importer.import_file("test.xlsx")

        # Should import 8 series (4 result types × 2 directions)
        assert count == 8

    def test_skips_unselected_load_cases(
        self, db_session, sample_project, sample_result_set
    ):
        """Should skip load cases not in selected_load_cases."""
        importer = TimeHistoryImporter(
            session=db_session,
            project_id=sample_project.id,
            result_set_id=sample_result_set.id,
        )

        mock_result = TimeHistoryParseResult(
            load_case_name="TH02",
            drifts_x=[TimeSeriesData("Ground", "X", [0.0], [0.1], 0)],
            stories=["Ground"],
        )

        with patch("processing.time_history_importer.TimeHistoryParser") as MockParser:
            MockParser.return_value.parse.return_value = mock_result

            # Only select TH01, not TH02
            count = importer.import_file("test.xlsx", selected_load_cases={"TH01"})

        assert count == 0

    def test_calls_progress_callback(
        self, db_session, sample_project, sample_result_set
    ):
        """Should call progress callback during import."""
        callback = MagicMock()
        importer = TimeHistoryImporter(
            session=db_session,
            project_id=sample_project.id,
            result_set_id=sample_result_set.id,
            progress_callback=callback,
        )

        mock_result = TimeHistoryParseResult(
            load_case_name="TH01",
            stories=["Ground"],
        )

        with patch("processing.time_history_importer.TimeHistoryParser") as MockParser:
            MockParser.return_value.parse.return_value = mock_result

            importer.import_file("test.xlsx")

        # Should have called progress callback
        assert callback.call_count > 0


class TestReportProgress:
    """Tests for _report_progress method."""

    def test_calls_callback_when_present(
        self, db_session, sample_project, sample_result_set
    ):
        """Should call callback when it's set."""
        callback = MagicMock()
        importer = TimeHistoryImporter(
            session=db_session,
            project_id=sample_project.id,
            result_set_id=sample_result_set.id,
            progress_callback=callback,
        )

        importer._report_progress(50, "Halfway done")

        callback.assert_called_once_with(50, "Halfway done")

    def test_does_not_fail_without_callback(
        self, db_session, sample_project, sample_result_set
    ):
        """Should not fail when callback is None."""
        importer = TimeHistoryImporter(
            session=db_session,
            project_id=sample_project.id,
            result_set_id=sample_result_set.id,
        )

        # Should not raise
        importer._report_progress(50, "Test message")


class TestTimeSeriesRepository:
    """Tests for TimeSeriesRepository class."""

    def test_get_available_load_cases(
        self, db_session, sample_project, sample_result_set, sample_time_series_cache
    ):
        """Should return distinct load case names."""
        repo = TimeSeriesRepository(db_session)

        load_cases = repo.get_available_load_cases(
            sample_project.id, sample_result_set.id
        )

        assert load_cases == ["TH01"]

    def test_get_available_load_cases_returns_empty_when_none(
        self, db_session, sample_project, sample_result_set
    ):
        """Should return empty list when no time series data."""
        repo = TimeSeriesRepository(db_session)

        load_cases = repo.get_available_load_cases(
            sample_project.id, sample_result_set.id
        )

        assert load_cases == []

    def test_get_available_result_types(
        self, db_session, sample_project, sample_result_set, sample_time_series_cache
    ):
        """Should return distinct result types for a load case."""
        repo = TimeSeriesRepository(db_session)

        result_types = repo.get_available_result_types(
            sample_project.id, sample_result_set.id, "TH01"
        )

        assert "Drifts" in result_types

    def test_get_time_series(
        self, db_session, sample_project, sample_result_set, sample_time_series_cache
    ):
        """Should return time series for all stories."""
        repo = TimeSeriesRepository(db_session)

        time_series = repo.get_time_series(
            sample_project.id, sample_result_set.id, "TH01", "Drifts", "X"
        )

        # Should return 5 entries (one per story)
        assert len(time_series) == 5

    def test_get_time_series_orders_by_sort_order_desc(
        self, db_session, sample_project, sample_result_set, sample_time_series_cache
    ):
        """Should return entries sorted by story_sort_order descending."""
        repo = TimeSeriesRepository(db_session)

        time_series = repo.get_time_series(
            sample_project.id, sample_result_set.id, "TH01", "Drifts", "X"
        )

        # First entry should have highest sort_order (lowest floor)
        sort_orders = [ts.story_sort_order for ts in time_series]
        assert sort_orders == sorted(sort_orders, reverse=True)

    def test_has_time_series_returns_true_when_present(
        self, db_session, sample_project, sample_result_set, sample_time_series_cache
    ):
        """Should return True when time series data exists."""
        repo = TimeSeriesRepository(db_session)

        result = repo.has_time_series(sample_project.id, sample_result_set.id)

        assert result is True

    def test_has_time_series_returns_false_when_missing(
        self, db_session, sample_project, sample_result_set
    ):
        """Should return False when no time series data."""
        repo = TimeSeriesRepository(db_session)

        result = repo.has_time_series(sample_project.id, sample_result_set.id)

        assert result is False

    def test_delete_time_series(
        self, db_session, sample_project, sample_result_set, sample_time_series_cache
    ):
        """Should delete all time series for a result set."""
        repo = TimeSeriesRepository(db_session)

        count = repo.delete_time_series(sample_project.id, sample_result_set.id)

        assert count == 5  # 5 entries deleted

        # Verify deletion
        remaining = db_session.query(TimeSeriesGlobalCache).filter_by(
            result_set_id=sample_result_set.id
        ).count()
        assert remaining == 0
