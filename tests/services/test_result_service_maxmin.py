from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.base import Base
import database.models as models
from database.repository import CacheRepository, StoryRepository, LoadCaseRepository, ElementRepository, ResultSetRepository
from services.result_service import ResultDataService


def _setup_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_element_maxmin_preserves_signs_for_column_axials():
    session = _setup_session()

    project = models.Project(name="P1")
    session.add(project)
    session.commit()

    result_set = models.ResultSet(project_id=project.id, name="DES", analysis_type="NLTHA")
    session.add(result_set)
    session.commit()

    story = models.Story(project_id=project.id, name="S1", sort_order=1)
    session.add(story)
    session.commit()

    lc1 = models.LoadCase(project_id=project.id, name="LC1")
    session.add(lc1)
    session.commit()

    element = models.Element(project_id=project.id, element_type="Column", unique_name="C1", name="C1")
    session.add(element)
    session.commit()

    session.add(
        models.ColumnAxial(
            element_id=element.id,
            story_id=story.id,
            load_case_id=lc1.id,
            result_category_id=None,
            min_axial=-1500.0,
            max_axial=800.0,
            story_sort_order=1,
        )
    )
    session.commit()

    cache_repo = CacheRepository(session)
    story_repo = StoryRepository(session)
    load_case_repo = LoadCaseRepository(session)
    element_repo = ElementRepository(session)
    result_set_repo = ResultSetRepository(session)

    rds = ResultDataService(
        project_id=project.id,
        cache_repo=cache_repo,
        story_repo=story_repo,
        load_case_repo=load_case_repo,
        abs_maxmin_repo=None,
        element_cache_repo=None,
        element_repo=element_repo,
        joint_cache_repo=None,
        session=session,
    )

    dataset = rds.get_element_maxmin_dataset(
        element_id=element.id,
        result_set_id=result_set.id,
        base_result_type="ColumnAxials",
    )

    assert dataset is not None
    row = dataset.data.iloc[0]
    # Signs should be preserved (no absolute value conversion)
    assert row["Max_LC1"] == 800.0
    assert row["Min_LC1"] == -1500.0

    # Display name should omit direction suffix
    assert "Direction" not in dataset.meta.display_name

    session.close()
