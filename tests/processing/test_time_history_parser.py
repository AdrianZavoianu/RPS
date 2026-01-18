"""Tests for time_history_parser.py"""

import pytest
from unittest.mock import MagicMock, patch
import pandas as pd

from processing.time_history_parser import (
    TimeHistoryParser,
    TimeHistoryParseResult,
    TimeSeriesData,
    prescan_time_history_file,
)


class TestTimeSeriesData:
    """Tests for TimeSeriesData dataclass."""

    def test_creates_with_required_fields(self):
        """TimeSeriesData should store all required fields."""
        data = TimeSeriesData(
            story="Level 1",
            direction="X",
            time_steps=[0.0, 0.01, 0.02],
            values=[0.0, 0.5, 1.0],
        )
        assert data.story == "Level 1"
        assert data.direction == "X"
        assert data.time_steps == [0.0, 0.01, 0.02]
        assert data.values == [0.0, 0.5, 1.0]
        assert data.story_sort_order == 0  # Default

    def test_creates_with_sort_order(self):
        """TimeSeriesData should accept custom sort_order."""
        data = TimeSeriesData(
            story="Roof",
            direction="Y",
            time_steps=[0.0, 0.01],
            values=[0.0, 0.3],
            story_sort_order=5,
        )
        assert data.story_sort_order == 5


class TestTimeHistoryParseResult:
    """Tests for TimeHistoryParseResult dataclass."""

    def test_creates_with_load_case_name(self):
        """TimeHistoryParseResult should store load case name."""
        result = TimeHistoryParseResult(load_case_name="TH01")
        assert result.load_case_name == "TH01"
        assert result.drifts_x == []
        assert result.drifts_y == []
        assert result.forces_x == []
        assert result.forces_y == []
        assert result.displacements_x == []
        assert result.displacements_y == []
        assert result.accelerations_x == []
        assert result.accelerations_y == []
        assert result.stories == []

    def test_stores_all_result_lists(self):
        """TimeHistoryParseResult should store all result type lists."""
        drift_x = TimeSeriesData("L1", "X", [0.0], [0.1])
        drift_y = TimeSeriesData("L1", "Y", [0.0], [0.2])

        result = TimeHistoryParseResult(
            load_case_name="TH02",
            drifts_x=[drift_x],
            drifts_y=[drift_y],
            stories=["L1"],
        )

        assert len(result.drifts_x) == 1
        assert len(result.drifts_y) == 1
        assert result.stories == ["L1"]


class TestTimeHistoryParserInit:
    """Tests for TimeHistoryParser initialization."""

    def test_stores_file_path(self, tmp_path):
        """Parser should store file path."""
        file_path = tmp_path / "test.xlsx"
        file_path.touch()

        # TimeHistoryParser.__init__ just stores file_path and sets _xl = None
        # It doesn't open the file until parse() is called
        parser = TimeHistoryParser(file_path)

        assert parser.file_path == file_path
        assert parser._xl is None


class TestDetectLoadCaseName:
    """Tests for _detect_load_case_name method."""

    def test_detects_load_case_from_story_drifts(self):
        """Should detect load case name from Output Case column."""
        mock_xl = MagicMock()
        mock_xl.sheet_names = ["Story Drifts"]

        # Create DataFrame with Output Case in column 1
        df = pd.DataFrame({
            "Story": ["Roof", "Level 1"],
            "Output Case": ["TH07", "TH07"],
            "Case Type": ["LinModHist", "LinModHist"],
        })

        with patch("pandas.read_excel", return_value=df):
            parser = TimeHistoryParser.__new__(TimeHistoryParser)
            parser._xl = mock_xl
            parser.STORY_DRIFTS_SHEET = "Story Drifts"

            result = parser._detect_load_case_name()

        assert result == "TH07"

    def test_returns_unknown_when_sheet_missing(self):
        """Should return 'Unknown' if Story Drifts sheet is missing."""
        mock_xl = MagicMock()
        mock_xl.sheet_names = ["Other Sheet"]

        parser = TimeHistoryParser.__new__(TimeHistoryParser)
        parser._xl = mock_xl
        parser.STORY_DRIFTS_SHEET = "Story Drifts"

        result = parser._detect_load_case_name()

        assert result == "Unknown"


class TestParseStoryDrifts:
    """Tests for _parse_story_drifts method."""

    def test_parses_x_direction_drifts(self, sample_story_drifts_df):
        """Should parse X direction drifts correctly."""
        mock_xl = MagicMock()

        with patch("pandas.read_excel", return_value=sample_story_drifts_df):
            parser = TimeHistoryParser.__new__(TimeHistoryParser)
            parser._xl = mock_xl
            parser.STORY_DRIFTS_SHEET = "Story Drifts"

            drifts_x, drifts_y, stories = parser._parse_story_drifts()

        # Should have 3 stories (Roof, Level 3, Level 2)
        assert len(stories) == 3
        assert "Roof" in stories

        # Should have X direction drifts for each story
        assert len(drifts_x) == 3

        # Verify first story's time series
        roof_drift = next(d for d in drifts_x if d.story == "Roof")
        assert roof_drift.direction == "X"
        assert len(roof_drift.time_steps) == 2
        assert len(roof_drift.values) == 2

    def test_preserves_story_order(self, sample_story_drifts_df):
        """Should preserve story order from Excel (top to bottom)."""
        mock_xl = MagicMock()

        with patch("pandas.read_excel", return_value=sample_story_drifts_df):
            parser = TimeHistoryParser.__new__(TimeHistoryParser)
            parser._xl = mock_xl
            parser.STORY_DRIFTS_SHEET = "Story Drifts"

            drifts_x, drifts_y, stories = parser._parse_story_drifts()

        # Stories should be in Excel order (Roof first, then down)
        assert stories[0] == "Roof"
        assert stories[1] == "Level 3"
        assert stories[2] == "Level 2"


class TestParseStoryForces:
    """Tests for _parse_story_forces method."""

    def test_parses_vx_and_vy_forces(self, sample_story_forces_df):
        """Should parse both VX and VY forces."""
        mock_xl = MagicMock()

        with patch("pandas.read_excel", return_value=sample_story_forces_df):
            parser = TimeHistoryParser.__new__(TimeHistoryParser)
            parser._xl = mock_xl
            parser.STORY_FORCES_SHEET = "Story Forces"

            forces_x, forces_y, stories = parser._parse_story_forces()

        # Should have forces for both directions
        assert len(forces_x) == 2  # Roof and Level 3
        assert len(forces_y) == 2

        # Verify X direction
        roof_vx = next(f for f in forces_x if f.story == "Roof")
        assert roof_vx.direction == "X"
        assert roof_vx.values == [50, 55]

        # Verify Y direction
        roof_vy = next(f for f in forces_y if f.story == "Roof")
        assert roof_vy.direction == "Y"
        assert roof_vy.values == [30, 35]


class TestParseJointDisplacements:
    """Tests for _parse_joint_displacements method."""

    def test_filters_by_label_1(self, sample_joint_displacements_df):
        """Should filter to Label=1 joints only."""
        mock_xl = MagicMock()

        with patch("pandas.read_excel", return_value=sample_joint_displacements_df):
            parser = TimeHistoryParser.__new__(TimeHistoryParser)
            parser._xl = mock_xl
            parser.JOINT_DISPLACEMENTS_SHEET = "Joint Displacements"

            disp_x, disp_y, stories = parser._parse_joint_displacements()

        # All data has Label=1, so should parse all
        assert len(disp_x) == 2  # Roof and Level 3
        assert len(disp_y) == 2

    def test_parses_ux_and_uy_displacements(self, sample_joint_displacements_df):
        """Should parse Ux and Uy displacement values."""
        mock_xl = MagicMock()

        with patch("pandas.read_excel", return_value=sample_joint_displacements_df):
            parser = TimeHistoryParser.__new__(TimeHistoryParser)
            parser._xl = mock_xl
            parser.JOINT_DISPLACEMENTS_SHEET = "Joint Displacements"

            disp_x, disp_y, stories = parser._parse_joint_displacements()

        roof_ux = next(d for d in disp_x if d.story == "Roof")
        assert roof_ux.values == [10.5, 12.3]


class TestParseDiaphragmAccelerations:
    """Tests for _parse_diaphragm_accelerations method."""

    def test_parses_max_ux_and_max_uy(self, sample_diaphragm_accelerations_df):
        """Should parse Max UX and Max UY accelerations."""
        mock_xl = MagicMock()

        with patch("pandas.read_excel", return_value=sample_diaphragm_accelerations_df):
            parser = TimeHistoryParser.__new__(TimeHistoryParser)
            parser._xl = mock_xl
            parser.DIAPHRAGM_ACCELERATIONS_SHEET = "Diaphragm Accelerations"

            accel_x, accel_y, stories = parser._parse_diaphragm_accelerations()

        assert len(accel_x) == 2  # Roof and Level 3
        assert len(accel_y) == 2

        roof_ax = next(a for a in accel_x if a.story == "Roof")
        assert roof_ax.values == [1000, 1500]

        roof_ay = next(a for a in accel_y if a.story == "Roof")
        assert roof_ay.values == [500, 750]


class TestExtractTimeSeriesByDirection:
    """Tests for _extract_time_series_by_direction method."""

    def test_extracts_single_direction(self):
        """Should extract time series for specified direction only."""
        df = pd.DataFrame({
            "Story": ["Roof", "Roof", "Roof", "Roof"],
            "Step_Num": [1, 2, 1, 2],
            "Direction": ["X", "X", "Y", "Y"],
            "Drift": [0.001, 0.002, 0.0005, 0.001],
            "Step_Type": ["Step By Step"] * 4,
        })
        story_order = ["Roof"]

        parser = TimeHistoryParser.__new__(TimeHistoryParser)
        result = parser._extract_time_series_by_direction(df, "X", "Drift", story_order)

        assert len(result) == 1
        assert result[0].direction == "X"
        assert result[0].values == [0.001, 0.002]

    def test_assigns_sort_order_from_story_index(self):
        """Should assign story_sort_order based on story_order index."""
        df = pd.DataFrame({
            "Story": ["Roof", "Roof", "Level 1", "Level 1"],
            "Step_Num": [1, 2, 1, 2],
            "Direction": ["X", "X", "X", "X"],
            "Drift": [0.001, 0.002, 0.0015, 0.0025],
            "Step_Type": ["Step By Step"] * 4,
        })
        story_order = ["Roof", "Level 1"]

        parser = TimeHistoryParser.__new__(TimeHistoryParser)
        result = parser._extract_time_series_by_direction(df, "X", "Drift", story_order)

        roof_data = next(r for r in result if r.story == "Roof")
        level1_data = next(r for r in result if r.story == "Level 1")

        assert roof_data.story_sort_order == 0
        assert level1_data.story_sort_order == 1


class TestExtractTimeSeriesDirect:
    """Tests for _extract_time_series_direct method."""

    def test_extracts_vx_as_x_direction(self):
        """Should map VX column to X direction."""
        df = pd.DataFrame({
            "Story": ["Roof", "Roof"],
            "Step_Num": [1, 2],
            "VX": [100, 150],
            "Step_Type": ["Step By Step"] * 2,
        })
        story_order = ["Roof"]

        parser = TimeHistoryParser.__new__(TimeHistoryParser)
        result = parser._extract_time_series_direct(df, "VX", story_order)

        assert len(result) == 1
        assert result[0].direction == "X"
        assert result[0].values == [100, 150]

    def test_extracts_vy_as_y_direction(self):
        """Should map VY column to Y direction."""
        df = pd.DataFrame({
            "Story": ["Roof", "Roof"],
            "Step_Num": [1, 2],
            "VY": [50, 75],
            "Step_Type": ["Step By Step"] * 2,
        })
        story_order = ["Roof"]

        parser = TimeHistoryParser.__new__(TimeHistoryParser)
        result = parser._extract_time_series_direct(df, "VY", story_order)

        assert len(result) == 1
        assert result[0].direction == "Y"


class TestPrescanTimeHistoryFile:
    """Tests for prescan_time_history_file function."""

    def test_returns_load_case_name(self):
        """Should return load case name from file."""
        df = pd.DataFrame({
            "Story": ["Roof"],
            "Output Case": ["TH03"],
            "Case Type": ["LinModHist"],
            "Step Type": ["Step By Step"],
            "Step Num": [1],
        })

        mock_xl = MagicMock()
        mock_xl.sheet_names = ["Story Drifts"]

        with patch("pandas.ExcelFile", return_value=mock_xl):
            with patch("pandas.read_excel", return_value=df):
                result = prescan_time_history_file("test.xlsx")

        assert result["load_case_name"] == "TH03"

    def test_returns_story_count(self):
        """Should return number of unique stories."""
        df = pd.DataFrame({
            "Story": ["Roof", "Roof", "Level 1", "Level 1"],
            "Output Case": ["TH03"] * 4,
            "Case Type": ["LinModHist"] * 4,
            "Step Type": ["Step By Step"] * 4,
            "Step Num": [1, 2, 1, 2],
        })

        mock_xl = MagicMock()
        mock_xl.sheet_names = ["Story Drifts"]

        with patch("pandas.ExcelFile", return_value=mock_xl):
            with patch("pandas.read_excel", return_value=df):
                result = prescan_time_history_file("test.xlsx")

        assert result["num_stories"] == 2

    def test_returns_available_sheets(self):
        """Should return list of available sheets."""
        mock_xl = MagicMock()
        mock_xl.sheet_names = ["Story Drifts", "Story Forces", "Other"]

        df = pd.DataFrame({
            "Story": ["Roof"],
            "Output Case": ["TH01"],
            "Case Type": ["LinModHist"],
            "Step Type": ["Step By Step"],
            "Step Num": [1],
        })

        with patch("pandas.ExcelFile", return_value=mock_xl):
            with patch("pandas.read_excel", return_value=df):
                result = prescan_time_history_file("test.xlsx")

        assert "Story Drifts" in result["available_sheets"]
        assert "Story Forces" in result["available_sheets"]

    def test_handles_missing_story_drifts_sheet(self):
        """Should return Unknown when Story Drifts sheet is missing."""
        mock_xl = MagicMock()
        mock_xl.sheet_names = ["Other Sheet"]

        with patch("pandas.ExcelFile", return_value=mock_xl):
            result = prescan_time_history_file("test.xlsx")

        assert result["load_case_name"] == "Unknown"
        assert result["num_stories"] == 0
