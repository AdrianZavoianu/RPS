"""Tests for pushover curve export sheet naming."""

import tempfile
from pathlib import Path

import openpyxl
import pytest

from database.base import Base, engine, get_session
from database.models import PushoverCase, PushoverCurvePoint, ResultSet
from database.repository import ProjectRepository, ResultSetRepository
from services.export_service import ExportService


@pytest.fixture()
def session():
    Base.metadata.create_all(bind=engine)
    session = get_session()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


class DummyContext:
    def __init__(self, session_factory):
        self._factory = session_factory

    def session(self):
        return self._factory()


def test_pushover_curve_export_uses_shorthand_sheet_names(session):
    project_repo = ProjectRepository(session)
    result_set_repo = ResultSetRepository(session)

    project = project_repo.create("PushoverExport")
    result_set = result_set_repo.create(project_id=project.id, name="PUSH")
    result_set.analysis_type = "Pushover"

    pushover_case = PushoverCase(
        project_id=project.id,
        result_set_id=result_set.id,
        name="Push-Mod-X+Ecc+",
        direction="X",
        base_story="Base",
    )
    session.add(pushover_case)
    session.flush()

    session.add_all(
        [
            PushoverCurvePoint(
                pushover_case_id=pushover_case.id,
                step_number=1,
                displacement=0.0,
                base_shear=0.0,
            ),
            PushoverCurvePoint(
                pushover_case_id=pushover_case.id,
                step_number=2,
                displacement=10.0,
                base_shear=100.0,
            ),
        ]
    )
    session.commit()

    context = DummyContext(get_session)
    export_service = ExportService(context, result_service=None)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        tmp_path = Path(tmp.name)

    try:
        export_service.export_pushover_curves(result_set.id, tmp_path)

        wb = openpyxl.load_workbook(tmp_path)
        # Should keep full load case name for sheet
        assert "Push-Mod-X+Ecc+"[:31] in wb.sheetnames
    finally:
        tmp_path.unlink(missing_ok=True)
