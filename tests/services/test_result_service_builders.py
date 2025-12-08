"""Tests for result service builder modules - comparison, maxmin, metadata builders."""

import pytest
import pandas as pd
from unittest.mock import MagicMock, patch

from processing.result_service.models import (
    ResultDataset,
    ResultDatasetMeta,
    ComparisonDataset,
    ComparisonSeries,
    MaxMinDataset,
)
from config.result_config import ResultTypeConfig


class MockResultSet:
    """Mock ResultSet for testing."""
    def __init__(self, id: int, name: str):
        self.id = id
        self.name = name


class TestResultDatasetMeta:
    """Tests for ResultDatasetMeta dataclass."""

    def test_creation(self):
        """Test creating ResultDatasetMeta."""
        meta = ResultDatasetMeta(
            result_type="Drifts",
            direction="X",
            result_set_id=1,
            display_name="Drifts X (DES)"
        )

        assert meta.result_type == "Drifts"
        assert meta.direction == "X"
        assert meta.result_set_id == 1
        assert meta.display_name == "Drifts X (DES)"

    def test_is_frozen(self):
        """Test that meta is immutable (frozen)."""
        meta = ResultDatasetMeta(
            result_type="Drifts",
            direction="X",
            result_set_id=1,
            display_name="Drifts X"
        )

        # Should raise error when trying to modify
        with pytest.raises(AttributeError):
            meta.result_type = "Forces"

    def test_none_direction(self):
        """Test creation with None direction."""
        meta = ResultDatasetMeta(
            result_type="QuadRotations",
            direction=None,
            result_set_id=1,
            display_name="Quad Rotations"
        )

        assert meta.direction is None


class TestResultDataset:
    """Tests for ResultDataset dataclass."""

    def test_creation_with_data(self):
        """Test creating ResultDataset with DataFrame."""
        meta = ResultDatasetMeta(
            result_type="Drifts",
            direction="X",
            result_set_id=1,
            display_name="Drifts X"
        )
        data = pd.DataFrame({
            'Story': ['L3', 'L2', 'L1'],
            'TH01': [0.1, 0.15, 0.12],
            'TH02': [0.11, 0.16, 0.13],
            'Avg': [0.105, 0.155, 0.125],
        })
        config = MagicMock(spec=ResultTypeConfig)

        dataset = ResultDataset(
            meta=meta,
            data=data,
            config=config,
            load_case_columns=['TH01', 'TH02'],
            summary_columns=['Avg']
        )

        assert dataset.meta == meta
        assert len(dataset.data) == 3
        assert dataset.load_case_columns == ['TH01', 'TH02']
        assert dataset.summary_columns == ['Avg']

    def test_default_summary_columns(self):
        """Test that summary_columns defaults to empty list."""
        meta = ResultDatasetMeta(
            result_type="Drifts",
            direction="X",
            result_set_id=1,
            display_name="Drifts X"
        )
        data = pd.DataFrame({'Story': ['L1'], 'TH01': [0.1]})
        config = MagicMock(spec=ResultTypeConfig)

        dataset = ResultDataset(
            meta=meta,
            data=data,
            config=config,
            load_case_columns=['TH01']
        )

        assert dataset.summary_columns == []


class TestComparisonSeries:
    """Tests for ComparisonSeries dataclass."""

    def test_creation_with_data(self):
        """Test creating ComparisonSeries with data."""
        series = ComparisonSeries(
            result_set_id=1,
            result_set_name="DES",
            values={"L3": 0.1, "L2": 0.15, "L1": 0.12},
            has_data=True
        )

        assert series.result_set_id == 1
        assert series.result_set_name == "DES"
        assert len(series.values) == 3
        assert series.has_data is True
        assert series.warning is None

    def test_creation_without_data(self):
        """Test creating ComparisonSeries without data."""
        series = ComparisonSeries(
            result_set_id=2,
            result_set_name="MCE",
            values={},
            has_data=False,
            warning="No data for Drifts_X"
        )

        assert series.has_data is False
        assert series.warning == "No data for Drifts_X"


class TestComparisonDataset:
    """Tests for ComparisonDataset dataclass."""

    def test_creation(self):
        """Test creating ComparisonDataset."""
        series1 = ComparisonSeries(
            result_set_id=1,
            result_set_name="DES",
            values={"L3": 0.1, "L2": 0.15},
            has_data=True
        )
        series2 = ComparisonSeries(
            result_set_id=2,
            result_set_name="MCE",
            values={"L3": 0.18, "L2": 0.25},
            has_data=True
        )
        data = pd.DataFrame({
            'Story': ['L3', 'L2'],
            'DES_Avg': [0.1, 0.15],
            'MCE_Avg': [0.18, 0.25],
            'MCE/DES': [1.8, 1.67],
        })
        meta = ResultDatasetMeta(
            result_type="Drifts",
            direction="X",
            result_set_id=1,
            display_name="Drifts X"
        )
        config = MagicMock(spec=ResultTypeConfig)

        comparison = ComparisonDataset(
            result_type="Drifts",
            direction="X",
            metric="Avg",
            config=config,
            series=[series1, series2],
            data=data,
            meta=meta,
            warnings=[]
        )

        assert comparison.result_type == "Drifts"
        assert comparison.direction == "X"
        assert comparison.metric == "Avg"
        assert len(comparison.series) == 2
        assert len(comparison.data) == 2
        assert comparison.warnings == []

    def test_warnings_default_to_empty_list(self):
        """Test that warnings defaults to empty list."""
        series = ComparisonSeries(
            result_set_id=1,
            result_set_name="DES",
            values={},
            has_data=True
        )
        data = pd.DataFrame()
        meta = ResultDatasetMeta(
            result_type="Drifts",
            direction="X",
            result_set_id=1,
            display_name="Drifts X"
        )
        config = MagicMock(spec=ResultTypeConfig)

        comparison = ComparisonDataset(
            result_type="Drifts",
            direction="X",
            metric="Avg",
            config=config,
            series=[series],
            data=data,
            meta=meta
        )

        assert comparison.warnings == []


class TestMaxMinDataset:
    """Tests for MaxMinDataset dataclass."""

    def test_creation(self):
        """Test creating MaxMinDataset."""
        meta = ResultDatasetMeta(
            result_type="MaxMinDrifts",
            direction=None,
            result_set_id=1,
            display_name="Max/Min Drifts"
        )
        data = pd.DataFrame({
            'Story': ['L3', 'L2', 'L1'],
            'Max_X': [0.1, 0.15, 0.12],
            'Max_Y': [0.08, 0.12, 0.09],
        })

        dataset = MaxMinDataset(
            meta=meta,
            data=data,
            directions=("X", "Y"),
            source_type="Drifts"
        )

        assert dataset.meta == meta
        assert len(dataset.data) == 3
        assert dataset.directions == ("X", "Y")
        assert dataset.source_type == "Drifts"

    def test_default_values(self):
        """Test MaxMinDataset default values."""
        meta = ResultDatasetMeta(
            result_type="MaxMinDrifts",
            direction=None,
            result_set_id=1,
            display_name="Max/Min"
        )
        data = pd.DataFrame()

        dataset = MaxMinDataset(meta=meta, data=data)

        assert dataset.directions == ("X", "Y")
        assert dataset.source_type == "Drifts"


class TestComparisonBuilder:
    """Tests for comparison builder functions."""

    def test_build_global_comparison_imports(self):
        """Test that comparison builder can be imported."""
        from processing.result_service.comparison_builder import build_global_comparison
        assert build_global_comparison is not None

    def test_build_global_comparison_with_mocks(self):
        """Test build_global_comparison with mock data."""
        from processing.result_service.comparison_builder import build_global_comparison

        # Create mock config
        mock_config = MagicMock(spec=ResultTypeConfig)
        mock_config.unit = "%"
        mock_config.format_suffix = ""
        mock_config.decimal_places = 2

        # Create mock dataset
        mock_data = pd.DataFrame({
            'Story': ['L3', 'L2', 'L1'],
            'TH01': [0.1, 0.15, 0.12],
            'Avg': [0.1, 0.15, 0.12],
        })
        mock_meta = ResultDatasetMeta(
            result_type="Drifts",
            direction="X",
            result_set_id=1,
            display_name="Drifts X"
        )
        mock_dataset = ResultDataset(
            meta=mock_meta,
            data=mock_data,
            config=mock_config,
            load_case_columns=['TH01'],
            summary_columns=['Avg']
        )

        # Create mock result set repository
        mock_result_set_repo = MagicMock()
        mock_result_set_repo.get_by_id.return_value = MockResultSet(1, "DES")

        # Create mock get_dataset function
        def mock_get_dataset(result_type, direction, result_set_id):
            return mock_dataset

        result = build_global_comparison(
            result_type="Drifts",
            direction="X",
            result_set_ids=[1],
            metric="Avg",
            config=mock_config,
            get_dataset_func=mock_get_dataset,
            result_set_repo=mock_result_set_repo
        )

        assert isinstance(result, ComparisonDataset)
        assert result.result_type == "Drifts"
        assert result.direction == "X"
        assert result.metric == "Avg"
        assert len(result.series) == 1

    def test_build_global_comparison_missing_result_set(self):
        """Test build_global_comparison when result set is missing."""
        from processing.result_service.comparison_builder import build_global_comparison

        mock_config = MagicMock(spec=ResultTypeConfig)
        mock_config.unit = "%"

        # Result set repo returns None
        mock_result_set_repo = MagicMock()
        mock_result_set_repo.get_by_id.return_value = None

        def mock_get_dataset(result_type, direction, result_set_id):
            return None

        result = build_global_comparison(
            result_type="Drifts",
            direction="X",
            result_set_ids=[9999],
            metric="Avg",
            config=mock_config,
            get_dataset_func=mock_get_dataset,
            result_set_repo=mock_result_set_repo
        )

        assert len(result.warnings) > 0
        assert "not found" in result.warnings[0]


class TestMetadataBuilder:
    """Tests for metadata builder functions."""

    def test_metadata_module_imports(self):
        """Test that metadata module can be imported."""
        from processing.result_service.metadata import build_display_label
        assert build_display_label is not None

    def test_build_display_label_with_direction(self):
        """Test display label generation with direction."""
        from processing.result_service.metadata import build_display_label

        # Test with direction
        label = build_display_label("Drifts", "X")
        assert "X" in label

    def test_build_display_label_no_direction(self):
        """Test display label generation without direction."""
        from processing.result_service.metadata import build_display_label

        label = build_display_label("MaxMinDrifts", None)
        assert "Max" in label or "Drift" in label

    def test_display_name_overrides(self):
        """Test that display name overrides work."""
        from processing.result_service.metadata import DISPLAY_NAME_OVERRIDES

        assert "Drifts" in DISPLAY_NAME_OVERRIDES
        assert DISPLAY_NAME_OVERRIDES["Drifts"] == "Story Drifts"
        assert "Forces" in DISPLAY_NAME_OVERRIDES
        assert DISPLAY_NAME_OVERRIDES["Forces"] == "Story Shears"


class TestStoryProvider:
    """Tests for StoryProvider."""

    def test_story_provider_imports(self):
        """Test that StoryProvider can be imported."""
        from processing.result_service.story_loader import StoryProvider
        assert StoryProvider is not None

    def test_story_provider_initialization(self):
        """Test StoryProvider initialization."""
        from processing.result_service.story_loader import StoryProvider

        mock_story_repo = MagicMock()
        provider = StoryProvider(mock_story_repo, project_id=1)

        assert provider._loaded is False
        assert provider._stories == []
        assert provider._story_index == {}

    def test_story_provider_lazy_loading(self):
        """Test StoryProvider lazy loads stories."""
        from processing.result_service.story_loader import StoryProvider

        # Create mock stories
        mock_story_1 = MagicMock()
        mock_story_1.id = 1
        mock_story_1.name = "L3"

        mock_story_2 = MagicMock()
        mock_story_2.id = 2
        mock_story_2.name = "L2"

        mock_story_repo = MagicMock()
        mock_story_repo.get_by_project.return_value = [mock_story_1, mock_story_2]

        provider = StoryProvider(mock_story_repo, project_id=1)

        # Before accessing, should not be loaded
        assert provider._loaded is False
        mock_story_repo.get_by_project.assert_not_called()

        # Access stories
        stories = provider.stories

        # Now should be loaded
        assert provider._loaded is True
        mock_story_repo.get_by_project.assert_called_once_with(1)
        assert len(stories) == 2

    def test_story_provider_index(self):
        """Test StoryProvider story index building."""
        from processing.result_service.story_loader import StoryProvider

        mock_story_1 = MagicMock()
        mock_story_1.id = 10
        mock_story_1.name = "L3"

        mock_story_2 = MagicMock()
        mock_story_2.id = 20
        mock_story_2.name = "L2"

        mock_story_repo = MagicMock()
        mock_story_repo.get_by_project.return_value = [mock_story_1, mock_story_2]

        provider = StoryProvider(mock_story_repo, project_id=1)

        # Access story_index
        index = provider.story_index

        # Should map story_id -> (order_index, name)
        assert 10 in index
        assert 20 in index
        assert index[10] == (0, "L3")
        assert index[20] == (1, "L2")
