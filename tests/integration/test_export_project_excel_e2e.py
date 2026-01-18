from datetime import datetime
from types import SimpleNamespace

import pandas as pd
import pytest

from services.export_service import ExportService, ProjectExportExcelOptions


class _ContextStub:
    def __init__(self):
        self.slug = "demo"
        self.db_path = "demo.db"

    def session(self):
        raise RuntimeError("session should not be called in this stubbed test")

    def session_factory(self):
        return self.session


class _ResultServiceStub:
    def __init__(self):
        self.project_id = 1


def _fake_metadata():
    catalog_project = SimpleNamespace(
        name="Demo",
        description="Stub project",
        slug="demo",
        created_at=datetime(2024, 1, 1, 12, 0, 0),
    )
    summary = SimpleNamespace(result_sets=1, load_cases=1, stories=1)
    result_set = SimpleNamespace(id=1, name="DES", description="", created_at=datetime(2024, 1, 2, 8, 0, 0))
    load_case = SimpleNamespace(name="LC1", description="")
    story = SimpleNamespace(name="S1", sort_order=1, elevation=0.0)
    element = SimpleNamespace(name="E1", unique_name="E1", element_type="Wall")
    return {
        "catalog_project": catalog_project,
        "summary": summary,
        "result_sets": [result_set],
        "result_categories": [],
        "load_cases": [load_case],
        "stories": [story],
        "elements": [element],
    }


def test_export_project_excel_writes_basic_sheets(monkeypatch, tmp_path):
    # Stub helpers to avoid hitting real DB
    monkeypatch.setattr(
        "services.export_metadata.ExportMetadataBuilder.build_metadata",
        lambda self: _fake_metadata(),
    )

    def _fake_discover_and_write(self, writer, result_set_id, result_sets, progress_callback):
        df = pd.DataFrame([{"Story": "S1", "LC1": 0.1}])
        df.to_excel(writer, sheet_name="Drifts_X", index=False)
        return {"global": ["Drifts_X"], "element": []}

    monkeypatch.setattr("services.export_discovery.ExportDiscovery.discover_and_write", _fake_discover_and_write)

    def _fake_import_data_sheet(self, writer, metadata, result_sheets):
        pd.DataFrame([{"import_metadata": "{}"}]).to_excel(writer, sheet_name="IMPORT_DATA", index=False)

    monkeypatch.setattr("services.export_import_data.ImportDataBuilder.write_import_data_sheet", _fake_import_data_sheet)

    ctx = _ContextStub()
    result_service = _ResultServiceStub()
    svc = ExportService(ctx, result_service)

    output = tmp_path / "project.xlsx"
    opts = ProjectExportExcelOptions(output_path=output)
    svc.export_project_excel(opts)

    assert output.exists() and output.stat().st_size > 0

    xls = pd.ExcelFile(output)
    sheets = set(xls.sheet_names)
    assert {"README", "Result Sets", "Load Cases", "Stories", "Elements", "Drifts_X"}.issubset(sheets)
