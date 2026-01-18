from datetime import datetime
from types import SimpleNamespace

import pandas as pd

from services.export_excel_sections import write_readme_sheet, write_metadata_sheets


def _build_metadata():
    catalog_project = SimpleNamespace(
        name="Demo",
        description="Test project",
        slug="demo",
        created_at=datetime(2024, 1, 1, 12, 0, 0),
    )
    summary = SimpleNamespace(result_sets=1, load_cases=2, stories=3)
    result_sets = [
        SimpleNamespace(name="DES", description="", created_at=datetime(2024, 1, 2, 8, 0, 0))
    ]
    load_cases = [SimpleNamespace(name="LC1", description="Case 1")]
    stories = [SimpleNamespace(name="S1", sort_order=1, elevation=0.0)]
    elements = [SimpleNamespace(name="E1", unique_name="E1", element_type="Wall")]
    return {
        "catalog_project": catalog_project,
        "summary": summary,
        "result_sets": result_sets,
        "load_cases": load_cases,
        "stories": stories,
        "elements": elements,
    }


def test_write_readme_and_metadata_sheets(tmp_path):
    meta = _build_metadata()
    output = tmp_path / "meta.xlsx"

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        write_readme_sheet(writer, meta, app_version="2.0")
        write_metadata_sheets(writer, meta)

    xls = pd.ExcelFile(output)
    sheets = set(xls.sheet_names)
    assert "README" in sheets
    assert "Result Sets" in sheets
    assert "Load Cases" in sheets
    assert "Stories" in sheets
    assert "Elements" in sheets
