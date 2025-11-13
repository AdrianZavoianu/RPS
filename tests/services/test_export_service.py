"""
Unit tests for ExportService.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock
import pandas as pd

from services.export_service import ExportService, ExportOptions


@pytest.fixture
def mock_context():
    """Mock ProjectContext with correct session pattern."""
    context = Mock()

    # Mock session context manager
    session_mock = MagicMock()
    context.session = Mock(return_value=session_mock)
    context.slug = "testproject"

    return context


@pytest.fixture
def mock_result_service():
    """Mock ResultDataService with sample dataset."""
    service = Mock()

    # Mock dataset with DataFrame in correct format
    mock_dataset = Mock()
    mock_dataset.df = pd.DataFrame({
        'Story': ['S4', 'S3', 'S2', 'S1', 'Base'],
        'TH01': [0.0030, 0.0028, 0.0025, 0.0020, 0.0000],
        'TH02': [0.0032, 0.0030, 0.0027, 0.0022, 0.0000],
        'MCR1': [0.0035, 0.0033, 0.0029, 0.0024, 0.0000],
    })

    service.get_standard_dataset.return_value = mock_dataset

    return service


@pytest.fixture
def export_service(mock_context, mock_result_service):
    """Create ExportService with mocked dependencies."""
    return ExportService(mock_context, mock_result_service)


def test_export_to_excel(export_service, mock_context, mock_result_service, tmp_path):
    """Test exporting result type to Excel file."""
    output_path = tmp_path / "test_export.xlsx"

    options = ExportOptions(
        result_set_id=1,
        result_type="Drifts_X",
        output_path=output_path,
        format="excel",
    )

    export_service.export_result_type(options)

    # Verify get_standard_dataset was called with correct arguments (no element_id!)
    mock_result_service.get_standard_dataset.assert_called_once_with(
        result_type="Drifts",
        direction="X",
        result_set_id=1
    )

    # Verify file was created
    assert output_path.exists()

    # Verify content
    df = pd.read_excel(output_path, engine='openpyxl')
    assert 'Story' in df.columns
    assert len(df) == 5
    assert list(df['Story']) == ['S4', 'S3', 'S2', 'S1', 'Base']


def test_export_to_csv(export_service, tmp_path):
    """Test exporting result type to CSV file."""
    output_path = tmp_path / "test_export.csv"

    options = ExportOptions(
        result_set_id=1,
        result_type="Drifts_X",
        output_path=output_path,
        format="csv",
    )

    export_service.export_result_type(options)

    # Verify file was created
    assert output_path.exists()

    # Verify content
    df = pd.read_csv(output_path)
    assert 'Story' in df.columns
    assert len(df) == 5


def test_export_with_progress_callback(export_service, tmp_path):
    """Test that progress callback is invoked during export."""
    output_path = tmp_path / "test_export.xlsx"
    progress_calls = []

    def progress_callback(message, current, total):
        progress_calls.append((message, current, total))

    options = ExportOptions(
        result_set_id=1,
        result_type="Drifts_X",
        output_path=output_path,
        format="excel",
    )

    export_service.export_result_type(options, progress_callback=progress_callback)

    # Verify progress was reported
    assert len(progress_calls) == 3
    assert progress_calls[0] == ("Loading data...", 1, 3)
    assert progress_calls[1] == ("Writing file...", 2, 3)
    assert progress_calls[2] == ("Export complete!", 3, 3)


def test_export_unknown_result_type(export_service, tmp_path):
    """Test that exporting unknown result type raises ValueError."""
    output_path = tmp_path / "test_export.xlsx"

    options = ExportOptions(
        result_set_id=1,
        result_type="UnknownType_X",
        output_path=output_path,
        format="excel",
    )

    with pytest.raises(ValueError, match="Unknown result type"):
        export_service.export_result_type(options)


def test_extract_direction_with_direction(export_service):
    """Test direction extraction for results with directions."""
    from config.result_config import RESULT_CONFIGS

    # Test directional result
    config = RESULT_CONFIGS.get("Drifts_X")
    direction = export_service._extract_direction("Drifts_X", config)
    assert direction == "X"


def test_extract_direction_directionless(export_service):
    """Test direction extraction for directionless results."""
    # Mock config for directionless result
    mock_config = Mock()
    mock_config.direction_suffix = ""

    direction = export_service._extract_direction("QuadRotations", mock_config)
    assert direction == ""


def test_extract_base_type_with_direction(export_service):
    """Test base type extraction for directional results."""
    base_type = export_service._extract_base_type("Drifts_X")
    assert base_type == "Drifts"

    base_type = export_service._extract_base_type("WallShears_V2")
    assert base_type == "WallShears"


def test_extract_base_type_directionless(export_service):
    """Test base type extraction for directionless results."""
    base_type = export_service._extract_base_type("QuadRotations")
    assert base_type == "QuadRotations"

    base_type = export_service._extract_base_type("MinAxial")
    assert base_type == "MinAxial"


def test_build_filename_excel(export_service):
    """Test filename building for Excel format."""
    filename = export_service.build_filename("Drifts_X", "excel")
    assert filename == "Drifts_X.xlsx"

    filename = export_service.build_filename("WallShears_V2", "excel")
    assert filename == "WallShears_V2.xlsx"


def test_build_filename_csv(export_service):
    """Test filename building for CSV format."""
    filename = export_service.build_filename("Drifts_X", "csv")
    assert filename == "Drifts_X.csv"

    filename = export_service.build_filename("QuadRotations", "csv")
    assert filename == "QuadRotations.csv"


def test_get_available_result_types(export_service, mock_context):
    """Test querying available result types from cache."""
    # Mock session query results
    mock_session = MagicMock()
    mock_context.session.return_value.__enter__.return_value = mock_session

    mock_query = MagicMock()
    mock_session.query.return_value = mock_query
    mock_query.filter.return_value = mock_query
    mock_query.distinct.return_value = mock_query
    mock_query.all.return_value = [("Drifts_X",), ("Drifts_Y",), ("Accelerations_UX",)]

    result_types = export_service.get_available_result_types(result_set_id=1)

    # Verify results
    assert len(result_types) == 3
    assert "Drifts_X" in result_types
    assert "Drifts_Y" in result_types
    assert "Accelerations_UX" in result_types
