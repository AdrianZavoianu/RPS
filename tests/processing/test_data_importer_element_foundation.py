import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.base import Base
import database.models as models  # registers models with Base
from processing.data_importer import DataImporter
from processing.foundation_importer import FoundationImporter


class StubParser:
    """Minimal parser covering pier forces and soil pressures."""

    def get_pier_forces(self):
        df = pd.DataFrame(
            [
                {
                    "Story": "L1",
                    "Pier": "P1",
                    "Output Case": "LC1",
                    "Location": "Bottom",
                    "V2": 10.0,
                    "V3": 20.0,
                },
            ]
        )
        return df, ["LC1"], ["L1"], ["P1"]

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


class SoilPressureParserOne:
    def get_soil_pressures(self):
        df = pd.DataFrame(
            [
                {
                    "Output Case": "TH01",
                    "Shell Object": "F1",
                    "Unique Name": "F1",
                    "Soil Pressure": -10.0,
                }
            ]
        )
        return df, ["TH01"], ["F1"]


class SoilPressureParserTwo:
    def get_soil_pressures(self):
        df = pd.DataFrame(
            [
                {
                    "Output Case": "TH02",
                    "Shell Object": "F2",
                    "Unique Name": "F2",
                    "Soil Pressure": -20.0,
                }
            ]
        )
        return df, ["TH02"], ["F2"]


def test_data_importer_imports_element_and_foundation_and_generates_cache(tmp_path):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)

    dummy_file = tmp_path / "fake.xlsx"
    dummy_file.write_text("", encoding="utf-8")

    cache_calls = []

    def session_factory():
        return SessionLocal()

    importer = DataImporter(
        file_path=str(dummy_file),
        project_name="Tower",
        result_set_name="DES",
        result_types=["Pier Forces", "Soil Pressures"],
        session_factory=session_factory,
        generate_cache=True,
    )
    importer.parser = StubParser()
    importer._sheet_available = lambda _name: True  # Allow tasks to run
    importer._generate_cache = lambda session, project_id, result_set_id: cache_calls.append(
        (project_id, result_set_id)
    )

    stats = importer.import_all()

    assert stats["pier_forces"] == 2  # V2 + V3
    assert stats["piers"] == 1
    assert stats["soil_pressures"] == 1
    assert cache_calls, "Cache generation should be invoked"

    session = SessionLocal()
    try:
        assert session.query(models.Project).count() == 1
        assert session.query(models.ResultSet).count() == 1
        assert session.query(models.LoadCase).count() == 1
        assert session.query(models.Story).count() == 1
        assert session.query(models.WallShear).count() == 2
        assert session.query(models.SoilPressure).count() == 1
    finally:
        session.close()


def test_generate_cache_if_needed_invokes_when_pending(tmp_path):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)

    dummy_file = tmp_path / "fake.xlsx"
    dummy_file.write_text("", encoding="utf-8")

    cache_calls = []

    def session_factory():
        return SessionLocal()

    importer = DataImporter(
        file_path=str(dummy_file),
        project_name="Tower",
        result_set_name="DES",
        result_types=["Pier Forces"],
        session_factory=session_factory,
        generate_cache=False,
    )
    importer.parser = StubParser()
    importer._sheet_available = lambda _name: True
    importer._generate_cache = lambda session, project_id, result_set_id: cache_calls.append(
        (project_id, result_set_id)
    )

    stats = importer.import_all()
    assert cache_calls == []  # deferred

    importer.generate_cache_if_needed()
    assert len(cache_calls) == 1
    assert cache_calls[0][0] == stats["project_id"]
    assert cache_calls[0][1] == stats["result_set_id"]


def test_foundation_importer_merges_soil_pressures_by_load_case():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        project = models.Project(name="Tower")
        session.add(project)
        session.flush()

        result_set = models.ResultSet(project_id=project.id, name="MCE")
        session.add(result_set)
        session.commit()

        importer_one = FoundationImporter(
            session=session,
            parser=SoilPressureParserOne(),
            project_id=project.id,
            result_set_id=result_set.id,
        )
        importer_one.import_soil_pressures()

        importer_two = FoundationImporter(
            session=session,
            parser=SoilPressureParserTwo(),
            project_id=project.id,
            result_set_id=result_set.id,
        )
        importer_two.import_soil_pressures()

        rows = (
            session.query(models.SoilPressure, models.LoadCase.name)
            .join(models.LoadCase, models.SoilPressure.load_case_id == models.LoadCase.id)
            .all()
        )

        assert len(rows) == 2
        pressures = {name: sp.min_pressure for sp, name in rows}
        assert pressures["TH01"] == -10.0
        assert pressures["TH02"] == -20.0
    finally:
        session.close()
