import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.base import Base
from database.repository import ProjectRepository
from processing.import_context import ResultImportHelper


@pytest.fixture()
def session():
    """Provide an in-memory database session for importer tests."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    sess = SessionLocal()
    try:
        yield sess
    finally:
        sess.close()
        engine.dispose()


def test_story_sort_order_preserved(session):
    project = ProjectRepository(session).create("Test Tower")
    helper = ResultImportHelper(session, project.id, ["Roof", "L02", "GFL"])

    roof = helper.get_story("Roof")
    ground = helper.get_story("GFL")

    assert roof.sort_order == 0
    assert ground.sort_order == 2


def test_story_sort_order_preserves_existing_records(session):
    project = ProjectRepository(session).create("Retrofit")

    helper_initial = ResultImportHelper(session, project.id, ["Roof", "L02"])
    story = helper_initial.get_story("L02")
    assert story.sort_order == 1

    helper_updated = ResultImportHelper(session, project.id, ["L02", "Roof"])
    updated_story = helper_updated.get_story("L02")
    session.commit()
    session.refresh(updated_story)

    assert updated_story.sort_order == 1


def test_load_case_cached(session):
    project = ProjectRepository(session).create("Seismic")
    helper = ResultImportHelper(session, project.id, [])

    lc_time_history = helper.get_load_case("TH01", case_type="Time History")
    lc_again = helper.get_load_case("TH01")

    assert lc_time_history.id == lc_again.id
