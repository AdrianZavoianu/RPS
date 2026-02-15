"""Tests for BasePushoverImporter base class."""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, Set

from processing.pushover.pushover_base_importer import BasePushoverImporter


class ConcretePushoverImporter(BasePushoverImporter):
    """Concrete implementation for testing abstract base class."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ensure_entities_called = False
        self.import_direction_calls = []
        self.build_cache_called = False

    def _ensure_entities(self):
        self.ensure_entities_called = True

    def _import_direction(self, direction: str, selected_load_cases: Set[str]) -> Dict:
        self.import_direction_calls.append((direction, selected_load_cases))
        return {'records': len(selected_load_cases)}

    def _build_cache(self):
        self.build_cache_called = True

    def _create_stats_dict(self) -> Dict:
        return {'records': 0, 'errors': []}


@pytest.fixture
def mock_session():
    """Create mock database session."""
    session = MagicMock()

    # Mock ResultSet query
    mock_result_set = MagicMock()
    mock_result_set.id = 1
    mock_result_set.name = "TestResultSet"
    session.query.return_value.get.return_value = mock_result_set

    return session


@pytest.fixture
def importer(mock_session, tmp_path):
    """Create importer instance for testing."""
    file_path = tmp_path / "test.xlsx"
    file_path.touch()

    return ConcretePushoverImporter(
        project_id=1,
        session=mock_session,
        result_set_id=1,
        file_path=file_path,
        selected_load_cases_x=['Push_X+', 'Push_X-'],
        selected_load_cases_y=['Push_Y+'],
        progress_callback=None
    )


class TestBasePushoverImporterInit:
    """Test importer initialization."""

    def test_init_stores_parameters(self, mock_session, tmp_path):
        """Importer stores all initialization parameters."""
        file_path = tmp_path / "test.xlsx"
        file_path.touch()

        importer = ConcretePushoverImporter(
            project_id=42,
            session=mock_session,
            result_set_id=10,
            file_path=file_path,
            selected_load_cases_x=['A', 'B'],
            selected_load_cases_y=['C'],
        )

        assert importer.project_id == 42
        assert importer.session == mock_session
        assert importer.result_set_id == 10
        assert importer.file_path == file_path
        assert importer.selected_load_cases_x == {'A', 'B'}
        assert importer.selected_load_cases_y == {'C'}

    def test_init_creates_empty_caches(self, importer):
        """Importer initializes empty caches."""
        assert importer.stories_cache == {}
        assert importer.load_cases_cache == {}
        assert importer.elements_cache == {}
        assert importer.story_order == {}


class TestImportAll:
    """Test import_all workflow."""

    def test_import_all_calls_ensure_entities(self, importer):
        """import_all calls _ensure_entities."""
        importer.import_all()

        assert importer.ensure_entities_called is True

    def test_import_all_imports_x_direction(self, importer):
        """import_all imports X direction when cases selected."""
        importer.import_all()

        x_calls = [c for c in importer.import_direction_calls if c[0] == 'X']
        assert len(x_calls) == 1
        assert x_calls[0][1] == {'Push_X+', 'Push_X-'}

    def test_import_all_imports_y_direction(self, importer):
        """import_all imports Y direction when cases selected."""
        importer.import_all()

        y_calls = [c for c in importer.import_direction_calls if c[0] == 'Y']
        assert len(y_calls) == 1
        assert y_calls[0][1] == {'Push_Y+'}

    def test_import_all_skips_empty_x_selection(self, mock_session, tmp_path):
        """import_all skips X direction when no cases selected."""
        file_path = tmp_path / "test.xlsx"
        file_path.touch()

        importer = ConcretePushoverImporter(
            project_id=1,
            session=mock_session,
            result_set_id=1,
            file_path=file_path,
            selected_load_cases_x=[],  # Empty
            selected_load_cases_y=['Push_Y+'],
        )

        importer.import_all()

        x_calls = [c for c in importer.import_direction_calls if c[0] == 'X']
        assert len(x_calls) == 0

    def test_import_all_calls_flush(self, importer, mock_session):
        """import_all flushes session after imports."""
        importer.import_all()

        mock_session.flush.assert_called()

    def test_import_all_builds_cache(self, importer):
        """import_all calls _build_cache."""
        importer.import_all()

        assert importer.build_cache_called is True

    def test_import_all_commits_on_success(self, importer, mock_session):
        """import_all commits session on success."""
        importer.import_all()

        mock_session.commit.assert_called()

    def test_import_all_rolls_back_on_error(self, importer, mock_session):
        """import_all rolls back on error."""
        importer._ensure_entities = Mock(side_effect=Exception("Test error"))

        with pytest.raises(Exception):
            importer.import_all()

        mock_session.rollback.assert_called()

    def test_import_all_raises_for_missing_result_set(self, mock_session, tmp_path):
        """import_all raises error if result set not found."""
        mock_session.query.return_value.get.return_value = None

        file_path = tmp_path / "test.xlsx"
        file_path.touch()

        importer = ConcretePushoverImporter(
            project_id=1,
            session=mock_session,
            result_set_id=999,
            file_path=file_path,
            selected_load_cases_x=['A'],
            selected_load_cases_y=[],
        )

        with pytest.raises(ValueError, match="Result set ID 999 not found"):
            importer.import_all()


class TestProgressCallback:
    """Test progress reporting."""

    def test_calls_progress_callback(self, mock_session, tmp_path):
        """import_all calls progress callback."""
        file_path = tmp_path / "test.xlsx"
        file_path.touch()

        progress_calls = []

        def progress_callback(message, current, total):
            progress_calls.append((message, current, total))

        importer = ConcretePushoverImporter(
            project_id=1,
            session=mock_session,
            result_set_id=1,
            file_path=file_path,
            selected_load_cases_x=['A'],
            selected_load_cases_y=['B'],
            progress_callback=progress_callback
        )

        importer.import_all()

        # Should have multiple progress updates
        assert len(progress_calls) > 0

        # First should be 0%
        assert progress_calls[0][1] == 0

        # Last should be 100%
        assert progress_calls[-1][1] == 100


class TestEntityManagement:
    """Test entity creation/caching methods."""

    def test_get_or_create_story_creates_new(self, importer, mock_session):
        """Creates new story if not exists."""
        mock_session.query.return_value.filter.return_value.first.return_value = None

        story = importer._get_or_create_story("Level 1", sort_order=0)

        mock_session.add.assert_called()
        mock_session.flush.assert_called()

    def test_get_or_create_story_caches_result(self, importer, mock_session):
        """Caches story after creation."""
        mock_story = MagicMock()
        mock_story.name = "Level 1"
        mock_session.query.return_value.filter.return_value.first.return_value = mock_story

        story1 = importer._get_or_create_story("Level 1")
        story2 = importer._get_or_create_story("Level 1")

        assert story1 == story2
        assert "Level 1" in importer.stories_cache

    def test_get_or_create_load_case_creates_new(self, importer, mock_session):
        """Creates new load case if not exists."""
        mock_session.query.return_value.filter.return_value.first.return_value = None

        load_case = importer._get_or_create_load_case("Push_X+")

        mock_session.add.assert_called()

    def test_get_or_create_load_case_caches_result(self, importer, mock_session):
        """Caches load case after creation."""
        mock_lc = MagicMock()
        mock_lc.name = "Push_X+"
        mock_session.query.return_value.filter.return_value.first.return_value = mock_lc

        lc1 = importer._get_or_create_load_case("Push_X+")
        lc2 = importer._get_or_create_load_case("Push_X+")

        assert lc1 == lc2
        assert "Push_X+" in importer.load_cases_cache

    def test_get_or_create_element_creates_new(self, importer, mock_session):
        """Creates new element if not exists."""
        mock_session.query.return_value.filter.return_value.first.return_value = None

        element = importer._get_or_create_element("P1", "Wall")

        mock_session.add.assert_called()

    def test_get_or_create_element_caches_by_type(self, importer, mock_session):
        """Caches elements by type and name."""
        mock_wall = MagicMock()
        mock_wall.name = "P1"
        mock_wall.element_type = "Wall"

        mock_column = MagicMock()
        mock_column.name = "P1"
        mock_column.element_type = "Column"

        # Return different elements for different types
        def filter_side_effect(*args, **kwargs):
            mock_result = MagicMock()
            # We'll control what first() returns based on the element type
            return mock_result

        mock_session.query.return_value.filter.side_effect = filter_side_effect

        importer._get_or_create_element("P1", "Wall")
        importer._get_or_create_element("P1", "Column")

        # Should have separate cache entries
        assert "Wall:P1" in importer.elements_cache
        assert "Column:P1" in importer.elements_cache


class TestStatsMerging:
    """Test statistics merging."""

    def test_merge_stats_prefixes_keys(self, importer):
        """Merges stats with direction prefix."""
        stats = {'errors': []}
        direction_stats = {'records': 5, 'shears': 10}

        importer._merge_stats(stats, direction_stats, 'x')

        assert stats['x_records'] == 5
        assert stats['x_shears'] == 10

    def test_merge_stats_accumulates_errors(self, importer):
        """Merges errors into main list."""
        stats = {'errors': ['Error 1']}
        direction_stats = {'errors': ['Error 2', 'Error 3']}

        importer._merge_stats(stats, direction_stats, 'x')

        assert stats['errors'] == ['Error 1', 'Error 2', 'Error 3']

    def test_merge_stats_handles_single_error(self, importer):
        """Handles single error (not in list)."""
        stats = {'errors': []}
        direction_stats = {'errors': 'Single error'}

        importer._merge_stats(stats, direction_stats, 'x')

        assert stats['errors'] == ['Single error']


class TestGetLoadCaseIds:
    """Test load case ID retrieval."""

    def test_returns_cached_load_case_ids(self, importer):
        """Returns IDs of cached load cases."""
        mock_lc1 = MagicMock()
        mock_lc1.id = 1
        mock_lc2 = MagicMock()
        mock_lc2.id = 2

        importer.load_cases_cache = {
            'Case1': mock_lc1,
            'Case2': mock_lc2
        }

        ids = importer._get_load_case_ids()

        assert set(ids) == {1, 2}

    def test_returns_empty_for_no_cached_cases(self, importer):
        """Returns empty list when no cached cases."""
        importer.load_cases_cache = {}

        ids = importer._get_load_case_ids()

        assert ids == []
