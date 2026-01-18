import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.base import Base
import database.models as models  # registers models
from processing.cache_builder import CacheBuilder


@pytest.fixture()
def session_factory():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    try:
        yield SessionLocal
    finally:
        SessionLocal().close()
        engine.dispose()


def test_cache_builder_generates_global_cache(session_factory):
    SessionLocal = session_factory
    session = SessionLocal()

    project = models.Project(name="P1")
    session.add(project)
    session.flush()

    result_set = models.ResultSet(project_id=project.id, name="DES")
    session.add(result_set)
    session.flush()

    category = models.ResultCategory(
        result_set_id=result_set.id,
        category_name="Envelopes",
        category_type="Global",
    )
    session.add(category)
    session.flush()

    story = models.Story(project_id=project.id, name="L1", sort_order=0)
    session.add(story)
    load_case = models.LoadCase(project_id=project.id, name="LC1", case_type="Time History")
    session.add(load_case)
    session.flush()

    drift = models.StoryDrift(
        story_id=story.id,
        load_case_id=load_case.id,
        result_category_id=category.id,
        direction="X",
        drift=0.01,
        story_sort_order=0,
    )
    session.add(drift)
    session.commit()

    builder = CacheBuilder(
        session=session,
        project_id=project.id,
        result_set_id=result_set.id,
        result_category_id=category.id,
    )

    # Should complete without raising and upsert drifts cache
    builder.generate_all()

    cache_entries = session.query(models.GlobalResultsCache).all()
    assert len(cache_entries) == 1
    entry = cache_entries[0]
    assert entry.result_type == "Drifts"
    assert entry.results_matrix.get("LC1_X") == pytest.approx(0.01)

    session.close()
