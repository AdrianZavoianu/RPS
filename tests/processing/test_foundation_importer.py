import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.base import Base
import database.models as models  # registers models with Base
from processing.foundation_importer import FoundationImporter


class StubParser:
    def get_soil_pressures(self):
        df = pd.DataFrame(
            [
                {
                    "Output Case": "LC1",
                    "Shell Object": "F1",
                    "Unique Name": "F1",
                    "Soil Pressure": -12.3,
                }
            ]
        )
        return df, ["LC1"], ["F1"]

    def get_vertical_displacements(self):
        df = pd.DataFrame(
            [
                {
                    "Output Case": "LC1",
                    "Story": "BASE",
                    "Label": "J1",
                    "Unique Name": "J1",
                    "Min Uz": -0.45,
                }
            ]
        )
        return df, ["LC1"], ["J1"]


def test_foundation_importer_creates_joint_results_and_reuses_context():
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

    importer = FoundationImporter(
        session=session,
        parser=StubParser(),
        project_id=project.id,
        result_set_id=result_set.id,
    )

    stats_sp = importer.import_soil_pressures()
    stats_vd = importer.import_vertical_displacements()

    assert stats_sp["soil_pressures"] == 1
    assert stats_vd["vertical_displacements"] == 1

    assert session.query(models.SoilPressure).count() == 1
    assert session.query(models.VerticalDisplacement).count() == 1
    # Load cases should be reused across imports
    assert session.query(models.LoadCase).count() == 1
    # Joint result category created once and reused
    assert (
        session.query(models.ResultCategory)
        .filter_by(result_set_id=result_set.id, category_type="Joints")
        .count()
        == 1
    )

    session.close()
