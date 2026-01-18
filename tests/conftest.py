"""Pytest configuration and fixtures."""

import sys
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Add src directory to Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from database.base import Base
from database.models import (
    Project,
    Story,
    LoadCase,
    ResultSet,
    TimeSeriesGlobalCache,
)


# ---------------------------------------------------------------------------
# Database Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def in_memory_engine():
    """Create an in-memory SQLite engine for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def db_session(in_memory_engine) -> Generator[Session, None, None]:
    """Create a database session for testing."""
    SessionLocal = sessionmaker(bind=in_memory_engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def sample_project(db_session: Session) -> Project:
    """Create a sample project for testing."""
    project = Project(name="TestProject")
    db_session.add(project)
    db_session.commit()
    return project


@pytest.fixture
def sample_result_set(db_session: Session, sample_project: Project) -> ResultSet:
    """Create a sample result set for testing."""
    result_set = ResultSet(
        project_id=sample_project.id,
        name="DES",
        analysis_type="NLTHA",
    )
    db_session.add(result_set)
    db_session.commit()
    return result_set


@pytest.fixture
def sample_stories(db_session: Session, sample_project: Project) -> list[Story]:
    """Create sample stories for testing (Ground to Roof)."""
    story_names = ["Ground", "Level 1", "Level 2", "Level 3", "Roof"]
    stories = []
    for idx, name in enumerate(story_names):
        story = Story(
            project_id=sample_project.id,
            name=name,
            sort_order=idx,
        )
        db_session.add(story)
        stories.append(story)
    db_session.commit()
    return stories


@pytest.fixture
def sample_load_cases(db_session: Session, sample_project: Project) -> list[LoadCase]:
    """Create sample load cases for testing."""
    load_case_names = ["DES_X", "DES_Y", "MCE_X", "MCE_Y"]
    load_cases = []
    for name in load_case_names:
        lc = LoadCase(
            project_id=sample_project.id,
            name=name,
        )
        db_session.add(lc)
        load_cases.append(lc)
    db_session.commit()
    return load_cases


# ---------------------------------------------------------------------------
# Time Series Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_time_series_data() -> dict:
    """Create sample time series data for testing."""
    return {
        "time_steps": [0.0, 0.01, 0.02, 0.03, 0.04, 0.05],
        "values": [0.0, 0.5, 1.0, 0.8, 0.3, 0.0],
    }


@pytest.fixture
def sample_time_series_cache(
    db_session: Session,
    sample_project: Project,
    sample_result_set: ResultSet,
    sample_stories: list[Story],
    sample_time_series_data: dict,
) -> list[TimeSeriesGlobalCache]:
    """Create sample time series cache entries for testing."""
    entries = []
    for story in sample_stories:
        entry = TimeSeriesGlobalCache(
            project_id=sample_project.id,
            result_set_id=sample_result_set.id,
            load_case_name="TH01",
            result_type="Drifts",
            direction="X",
            story_id=story.id,
            time_steps=sample_time_series_data["time_steps"],
            values=sample_time_series_data["values"],
            story_sort_order=story.sort_order,
        )
        db_session.add(entry)
        entries.append(entry)
    db_session.commit()
    return entries


# ---------------------------------------------------------------------------
# Mock Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_excel_file(tmp_path: Path) -> Path:
    """Create a mock Excel file path for testing."""
    excel_path = tmp_path / "test_data.xlsx"
    # Note: Actual Excel creation would use openpyxl
    # For unit tests, we typically mock pd.read_excel instead
    return excel_path


@pytest.fixture
def mock_progress_callback() -> MagicMock:
    """Create a mock progress callback for testing importers."""
    return MagicMock()


# ---------------------------------------------------------------------------
# DataFrame Fixtures for Parser Tests
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_story_drifts_df():
    """Create sample Story Drifts DataFrame matching ETABS format."""
    import pandas as pd

    data = {
        "Story": ["Roof", "Roof", "Level 3", "Level 3", "Level 2", "Level 2"],
        "Output Case": ["TH01", "TH01", "TH01", "TH01", "TH01", "TH01"],
        "Case Type": ["LinModHist", "LinModHist", "LinModHist", "LinModHist", "LinModHist", "LinModHist"],
        "Step Type": ["Step By Step", "Step By Step", "Step By Step", "Step By Step", "Step By Step", "Step By Step"],
        "Step Num": [1, 2, 1, 2, 1, 2],
        "Direction": ["X", "X", "X", "X", "X", "X"],
        "Drift": [0.001, 0.002, 0.0015, 0.0025, 0.0012, 0.0022],
    }
    return pd.DataFrame(data)


@pytest.fixture
def sample_story_forces_df():
    """Create sample Story Forces DataFrame matching ETABS format."""
    import pandas as pd

    data = {
        "Story": ["Roof", "Roof", "Level 3", "Level 3"],
        "Output Case": ["TH01", "TH01", "TH01", "TH01"],
        "Case Type": ["LinModHist", "LinModHist", "LinModHist", "LinModHist"],
        "Step Type": ["Step By Step", "Step By Step", "Step By Step", "Step By Step"],
        "Step Num": [1, 2, 1, 2],
        "Location": ["Bottom", "Bottom", "Bottom", "Bottom"],
        "P": [100, 105, 200, 210],
        "VX": [50, 55, 100, 110],
        "VY": [30, 35, 60, 65],
    }
    return pd.DataFrame(data)


@pytest.fixture
def sample_joint_displacements_df():
    """Create sample Joint Displacements DataFrame matching ETABS format."""
    import pandas as pd

    data = {
        "Story": ["Roof", "Roof", "Level 3", "Level 3"],
        "Label": [1, 1, 1, 1],
        "Unique Name": ["J1", "J1", "J2", "J2"],
        "Output Case": ["TH01", "TH01", "TH01", "TH01"],
        "Case Type": ["LinModHist", "LinModHist", "LinModHist", "LinModHist"],
        "Step Type": ["Step By Step", "Step By Step", "Step By Step", "Step By Step"],
        "Step Num": [1, 2, 1, 2],
        "Ux": [10.5, 12.3, 8.2, 9.5],
        "Uy": [5.2, 6.1, 4.1, 4.8],
        "Uz": [0.1, 0.15, 0.08, 0.12],
    }
    return pd.DataFrame(data)


@pytest.fixture
def sample_diaphragm_accelerations_df():
    """Create sample Diaphragm Accelerations DataFrame matching ETABS format."""
    import pandas as pd

    data = {
        "Story": ["Roof", "Roof", "Level 3", "Level 3"],
        "Diaphragm": ["D1", "D1", "D1", "D1"],
        "Output Case": ["TH01", "TH01", "TH01", "TH01"],
        "Case Type": ["LinModHist", "LinModHist", "LinModHist", "LinModHist"],
        "Step Type": ["Step By Step", "Step By Step", "Step By Step", "Step By Step"],
        "Step Num": [1, 2, 1, 2],
        "Max UX": [1000, 1500, 800, 1200],
        "Max UY": [500, 750, 400, 600],
    }
    return pd.DataFrame(data)
