"""Helpers for writing common Excel sheets (README, metadata)."""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

import pandas as pd


def write_readme_sheet(writer, metadata: dict, app_version: str) -> None:
    """Write README sheet with project overview."""
    catalog = metadata["catalog_project"]
    summary = metadata["summary"]

    readme_lines = [
        ["PROJECT INFORMATION"],
        ["==================="],
        [""],
        ["Project Name:", catalog.name],
        ["Description:", catalog.description or ""],
        ["Created:", catalog.created_at.strftime("%Y-%m-%d %H:%M:%S")],
        ["Exported:", datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        ["RPS Version:", app_version],
        [""],
        ["DATABASE SUMMARY"],
        ["================"],
        [""],
        ["Result Sets:", summary.result_sets],
        ["Load Cases:", summary.load_cases],
        ["Stories:", summary.stories],
        ["Elements:", len(metadata["elements"])],
        [""],
        ["IMPORT INSTRUCTIONS"],
        ["==================="],
        [""],
        ["To import this project into RPS:"],
        ["1. Open RPS application"],
        ["2. Click 'Import Project' on Projects page"],
        ["3. Select this Excel file"],
        ["4. Review project summary"],
        ["5. Click 'Import'"],
        [""],
        ["The hidden 'IMPORT_DATA' sheet contains metadata required for re-import."],
        ["Do NOT delete or modify this sheet."],
    ]

    df = pd.DataFrame(readme_lines)
    df.to_excel(writer, sheet_name="README", index=False, header=False)


def write_metadata_sheets(writer, metadata: dict) -> None:
    """Write metadata sheets (Result Sets, Load Cases, Stories, Elements)."""
    result_sets_data = [
        {
            "Name": rs.name,
            "Description": rs.description or "",
            "Created At": rs.created_at.strftime("%Y-%m-%d %H:%M:%S") if rs.created_at else "",
        }
        for rs in metadata["result_sets"]
    ]
    if result_sets_data:
        pd.DataFrame(result_sets_data).to_excel(writer, sheet_name="Result Sets", index=False)

    load_cases_data = [
        {
            "Name": lc.name,
            "Description": lc.description or "",
        }
        for lc in metadata["load_cases"]
    ]
    if load_cases_data:
        pd.DataFrame(load_cases_data).to_excel(writer, sheet_name="Load Cases", index=False)

    stories_data = [
        {
            "Name": s.name,
            "Sort Order": s.sort_order,
            "Elevation": s.elevation or 0.0,
        }
        for s in metadata["stories"]
    ]
    if stories_data:
        pd.DataFrame(stories_data).to_excel(writer, sheet_name="Stories", index=False)

    elements_data = [
        {
            "Name": e.name,
            "Unique Name": e.unique_name or "",
            "Element Type": e.element_type,
        }
        for e in metadata["elements"]
    ]
    if elements_data:
        pd.DataFrame(elements_data).to_excel(writer, sheet_name="Elements", index=False)
