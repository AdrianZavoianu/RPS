import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.base import Base
from database.element_result_repository import ElementResultQueryRepository
from database import models


def test_fetch_records_filters_by_result_set_id():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        project = models.Project(name="Tower")
        session.add(project)
        session.flush()

        rs_des = models.ResultSet(project_id=project.id, name="DES")
        rs_mce = models.ResultSet(project_id=project.id, name="MCE")
        session.add_all([rs_des, rs_mce])
        session.flush()

        cat_des = models.ResultCategory(
            result_set_id=rs_des.id, category_name="Envelopes", category_type="Elements"
        )
        cat_mce = models.ResultCategory(
            result_set_id=rs_mce.id, category_name="Envelopes", category_type="Elements"
        )
        session.add_all([cat_des, cat_mce])
        session.flush()

        story = models.Story(project_id=project.id, name="L1", sort_order=1)
        session.add(story)
        session.flush()

        lc_des = models.LoadCase(project_id=project.id, name="TH01")
        lc_mce = models.LoadCase(project_id=project.id, name="TH02")
        session.add_all([lc_des, lc_mce])
        session.flush()

        element = models.Element(
            project_id=project.id, element_type="Beam", name="B1", unique_name="B1"
        )
        session.add(element)
        session.flush()

        # DES record
        session.add(
            models.BeamRotation(
                element_id=element.id,
                story_id=story.id,
                load_case_id=lc_des.id,
                result_category_id=cat_des.id,
                r3_plastic=0.01,
                max_r3_plastic=0.02,
                min_r3_plastic=-0.01,
            )
        )
        # MCE record
        session.add(
            models.BeamRotation(
                element_id=element.id,
                story_id=story.id,
                load_case_id=lc_mce.id,
                result_category_id=cat_mce.id,
                r3_plastic=0.03,
                max_r3_plastic=0.04,
                min_r3_plastic=-0.02,
            )
        )
        session.commit()

        repo = ElementResultQueryRepository(session)

        filtered_records, model_info = repo.fetch_records(
            base_result_type="BeamRotations",
            project_id=project.id,
            element_id=element.id,
            result_set_id=rs_des.id,
        )

        assert model_info.model is models.BeamRotation
        assert len(filtered_records) == 1
        record, load_case, _story = filtered_records[0]
        assert load_case.id == lc_des.id
        assert record.result_category_id == cat_des.id
    finally:
        session.close()
