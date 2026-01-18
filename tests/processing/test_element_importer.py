import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.base import Base
import database.models as models  # registers models with Base
from processing.element_importer import ElementImporter


class StubParser:
    def get_pier_forces(self):
        df = pd.DataFrame(
            [
                {"Story": "S1", "Pier": "W1", "Output Case": "LC1", "Location": "Bottom", "V2": 10.0, "V3": 12.0},
            ]
        )
        return df, ["LC1"], ["S1"], ["W1"]

    def get_quad_rotations(self):
        df = pd.DataFrame(
            [
                {"Story": "S1", "PropertyName": "Q1", "Output Case": "LC1", "Name": "Q1", "StepType": "Max", "Rotation": 0.01},
                {"Story": "S1", "PropertyName": "Q1", "Output Case": "LC1", "Name": "Q1", "StepType": "Min", "Rotation": -0.02},
            ]
        )
        return df, ["LC1"], ["S1"], ["Q1"]

    def get_column_forces(self):
        df = pd.DataFrame(
            [
                {"Story": "S1", "Column": "C1", "Output Case": "LC1", "Location": "Bottom", "V2": 5.0, "V3": 6.0, "P": -25.0, "Unique Name": "C1"},
            ]
        )
        return df, ["LC1"], ["S1"], ["C1"]

    def get_fiber_hinge_states(self):
        df = pd.DataFrame(
            [
                {"Story": "S1", "Frame/Wall": "C1", "Output Case": "LC1", "Unique Name": "C1", "R2": 0.02, "R3": 0.03},
            ]
        )
        return df, ["LC1"], ["S1"], ["C1"]

    def get_hinge_states(self):
        df = pd.DataFrame(
            [
                {
                    "Story": "S1",
                    "Frame/Wall": "B1",
                    "Output Case": "LC1",
                    "Unique Name": "B1",
                    "Hinge": "H1",
                    "Generated Hinge": "",
                    "Rel Dist": 0.5,
                    "R3 Plastic": 0.04,
                },
            ]
        )
        return df, ["LC1"], ["S1"], ["B1"]


def test_element_importer_creates_elements_and_results():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    project = models.Project(name="P1")
    session.add(project)
    session.commit()

    category = models.ResultCategory(
        result_set_id=1,  # lightweight; importer only uses category id
        category_name="Envelopes",
        category_type="Global",
    )
    session.add(category)
    session.commit()

    importer = ElementImporter(
        session=session,
        parser=StubParser(),
        project_id=project.id,
        result_category_id=category.id,
    )

    stats_pier = importer.import_pier_forces()
    stats_quad = importer.import_quad_rotations()
    stats_cf = importer.import_column_forces()
    stats_ca = importer.import_column_axials()
    stats_cr = importer.import_column_rotations()
    stats_br = importer.import_beam_rotations()

    # Basic counts
    assert stats_pier["pier_forces"] == 2  # V2 + V3
    assert stats_pier["piers"] == 1
    assert stats_quad["quad_rotations"] == 1
    assert stats_cf["column_forces"] == 2  # V2 + V3
    assert stats_cf["columns"] == 1
    assert stats_ca["column_axials"] == 1
    assert stats_cr["column_rotations"] == 2  # R2 + R3
    assert stats_br["beam_rotations"] == 1

    # Persistence checks
    assert session.query(models.Element).count() == 4  # W1, Q1, C1, B1
    assert session.query(models.WallShear).count() == 2
    assert session.query(models.QuadRotation).count() == 1
    assert session.query(models.ColumnShear).count() == 2
    assert session.query(models.ColumnAxial).count() == 1
    assert session.query(models.ColumnRotation).count() == 2
    assert session.query(models.BeamRotation).count() == 1

    # Load case and story reuse
    assert session.query(models.LoadCase).count() == 1
    assert session.query(models.Story).count() == 1

    # Column axial min/max should both be persisted (even if equal)
    axial = session.query(models.ColumnAxial).one()
    assert axial.min_axial == -25.0
    assert axial.max_axial == -25.0

    session.close()
