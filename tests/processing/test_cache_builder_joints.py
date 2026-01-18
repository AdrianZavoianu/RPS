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


def test_cache_builder_generates_joint_caches(session_factory):
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

    load_case = models.LoadCase(project_id=project.id, name="LC1", case_type="Time History")
    session.add(load_case)
    session.flush()

    sp = models.SoilPressure(
        project_id=project.id,
        result_set_id=result_set.id,
        load_case_id=load_case.id,
        shell_object="F1",
        unique_name="F1",
        min_pressure=-12.3,
    )
    vd = models.VerticalDisplacement(
        project_id=project.id,
        result_set_id=result_set.id,
        load_case_id=load_case.id,
        story="BASE",
        label="J1",
        unique_name="J1",
        min_displacement=-0.45,
    )
    session.add_all([sp, vd])
    session.commit()

    builder = CacheBuilder(
        session=session,
        project_id=project.id,
        result_set_id=result_set.id,
        result_category_id=category.id,
    )
    builder.generate_all()

    joint_caches = session.query(models.JointResultsCache).all()
    assert len(joint_caches) == 2
    soil_entry = next(c for c in joint_caches if c.result_type == "SoilPressures_Min")
    vert_entry = next(c for c in joint_caches if c.result_type == "VerticalDisplacements_Min")

    assert soil_entry.results_matrix["LC1"] == pytest.approx(-12.3)
    assert soil_entry.unique_name == "F1"
    assert vert_entry.results_matrix["LC1"] == pytest.approx(-0.45)
    assert vert_entry.unique_name == "J1"

    session.close()
