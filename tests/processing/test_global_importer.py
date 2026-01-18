import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.base import Base
import database.models as models  # registers models with Base
from processing.global_importer import GlobalImporter


class StubParser:
    def get_story_drifts(self):
        df = pd.DataFrame(
            [
                {"Output Case": "LC1", "Direction": "X", "Story": "S1", "Drift": 0.10},
                {"Output Case": "LC1", "Direction": "Y", "Story": "S1", "Drift": -0.20},
            ]
        )
        return df, ["LC1"], ["S1"]

    def get_story_accelerations(self):
        df = pd.DataFrame(
            [
                {"Output Case": "LC1", "Story": "S1", "Step Type": "Max", "Max UX": 9810.0, "Max UY": 4905.0, "Min UX": 0.0, "Min UY": 0.0},
                {"Output Case": "LC1", "Story": "S1", "Step Type": "Min", "Max UX": 0.0, "Max UY": 0.0, "Min UX": -9810.0, "Min UY": -4905.0},
            ]
        )
        return df, ["LC1"], ["S1"]

    def get_story_forces(self):
        df = pd.DataFrame(
            [
                {"Output Case": "LC1", "Story": "S1", "Location": "Bottom", "VX": 100.0, "VY": 150.0},
            ]
        )
        return df, ["LC1"], ["S1"]

    def get_joint_displacements(self):
        df = pd.DataFrame(
            [
                {"Story": "S1", "Output Case": "LC1", "Ux": 0.5, "Uy": -0.25},
            ]
        )
        return df, ["LC1"], ["S1"]


def test_global_importer_creates_story_results_and_reuses_load_cases():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    project = models.Project(name="P1")
    session.add(project)
    session.commit()

    result_set = models.ResultSet(project_id=project.id, name="DES")
    session.add(result_set)
    session.commit()

    category = models.ResultCategory(
        result_set_id=result_set.id,
        category_name="Envelopes",
        category_type="Global",
    )
    session.add(category)
    session.commit()

    importer = GlobalImporter(
        session=session,
        parser=StubParser(),
        project_id=project.id,
        result_category_id=category.id,
    )

    stats_drifts = importer.import_story_drifts()
    stats_accels = importer.import_story_accelerations()
    stats_forces = importer.import_story_forces()
    stats_disp = importer.import_joint_displacements()

    assert stats_drifts["drifts"] == 2
    assert stats_drifts["load_cases"] == 1
    assert stats_drifts["stories"] == 1

    assert stats_accels["accelerations"] == 2
    assert stats_forces["forces"] == 2
    assert stats_disp["displacements"] == 2

    # Validate persistence
    assert session.query(models.StoryDrift).count() == 2
    assert session.query(models.StoryAcceleration).count() == 2
    assert session.query(models.StoryForce).count() == 2
    assert session.query(models.StoryDisplacement).count() == 2

    # Only one load case and story should be created and reused
    assert session.query(models.LoadCase).count() == 1
    assert session.query(models.Story).count() == 1

    session.close()
