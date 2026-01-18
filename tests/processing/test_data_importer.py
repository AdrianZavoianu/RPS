import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.base import Base
from database.models import LoadCase, Project, ResultSet, Story, StoryDrift
from processing.data_importer import DataImporter


class StubParser:
    """Stub Excel parser returning a minimal Story Drifts sheet."""

    def __init__(self):
        self._stories = ["Roof", "GFL"]
        self._load_cases = ["EQ1"]
        self._data = pd.DataFrame(
            {
                "Output Case": ["EQ1", "EQ1", "EQ1", "EQ1"],
                "Direction": ["X", "X", "Y", "Y"],
                "Story": ["Roof", "GFL", "Roof", "GFL"],
                "Drift": [0.001, 0.002, 0.003, 0.004],
            }
        )

    def validate_sheet_exists(self, sheet_name: str) -> bool:
        return sheet_name == "Story Drifts"

    def get_story_drifts(self):
        return self._data, list(self._load_cases), list(self._stories)


@pytest.fixture()
def sqlite_session_factory():
    """Provide a session factory backed by an in-memory SQLite database."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)

    def factory():
        return SessionLocal()

    yield factory, SessionLocal

    SessionLocal().close()
    engine.dispose()


def test_import_all_persists_story_drifts(sqlite_session_factory, tmp_path):
    factory, SessionLocal = sqlite_session_factory
    fake_excel = tmp_path / "fake.xlsx"
    fake_excel.write_bytes(b"")

    importer = DataImporter(
        file_path=str(fake_excel),
        project_name="Test Tower",
        result_set_name="DES",
        result_types=["Story Drifts"],
        session_factory=factory,
    )
    importer.parser = StubParser()

    stats = importer.import_all()

    assert stats["project"] == "Test Tower"
    assert stats["load_cases"] == 1
    assert stats["stories"] == 2
    assert stats["drifts"] == 4

    session = SessionLocal()
    try:
        project = session.query(Project).filter_by(name="Test Tower").one()
        result_set = session.query(ResultSet).filter_by(project_id=project.id).one()
        load_cases = session.query(LoadCase).filter_by(project_id=project.id).all()
        stories = session.query(Story).filter_by(project_id=project.id).order_by(Story.sort_order).all()
        drifts = session.query(StoryDrift).order_by(StoryDrift.id).all()

        assert len(load_cases) == 1
        assert [story.name for story in stories] == ["Roof", "GFL"]
        assert all(drift.result_category_id is not None for drift in drifts)
        assert sorted(round(drift.drift, 4) for drift in drifts) == [0.001, 0.002, 0.003, 0.004]
    finally:
        session.close()
