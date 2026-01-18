from pathlib import Path
from types import SimpleNamespace

import pandas as pd

from services.export_pushover import PushoverExporter


class _SessionStub:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _ContextStub:
    def session(self):
        return _SessionStub()


class _Case:
    def __init__(self, id, name):
        self.id = id
        self.name = name


class _Point:
    def __init__(self, step, base_shear, disp):
        self.step_number = step
        self.base_shear = base_shear
        self.displacement = disp


class _RepoStub:
    def __init__(self, session):
        pass

    def get_by_result_set(self, result_set_id):
        return [_Case(1, "CaseA"), _Case(2, "CaseB")]

    def get_curve_data(self, case_id):
        return [
            _Point(1, 100.0 * case_id, 10.0 * case_id),
            _Point(2, 150.0 * case_id, 15.0 * case_id),
        ]


def test_pushover_exporter_writes_sheets(tmp_path):
    context = _ContextStub()
    exporter = PushoverExporter(context, repo_factory=lambda session: _RepoStub(session))

    output = tmp_path / "pushover.xlsx"
    exporter.export_curves(result_set_id=1, output_path=output)

    assert output.exists()
    xls = pd.ExcelFile(output)
    # Expect sheets for both cases, truncated to Excel sheet name limit if needed
    assert "CaseA" in xls.sheet_names
    assert "CaseB" in xls.sheet_names
