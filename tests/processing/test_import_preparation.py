"""Tests for the import preparation service and helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import pytest

from services.import_preparation import (
    ImportPreparationService,
    detect_conflicts,
    determine_allowed_load_cases,
)


class StubParser:
    """Minimal Excel parser stub for prescan tests."""

    def __init__(self, sheet_data: Dict[str, List[str]]) -> None:
        self.sheet_data = sheet_data

    def get_available_sheets(self):
        return list(self.sheet_data.keys())

    def validate_sheet_exists(self, sheet_name: str) -> bool:
        return sheet_name in self.sheet_data

    def get_story_drifts(self):
        return None, self.sheet_data.get("Story Drifts", []), None

    def get_foundation_joints(self):
        return self.sheet_data.get("Fou", [])

    def get_joint_displacements(self):
        return None, self.sheet_data.get("Joint Displacements", []), None

    def get_load_cases_only(self, sheet_name: str):
        if sheet_name not in self.sheet_data:
            return None
        return self.sheet_data.get(sheet_name, [])


class StubParserFactory:
    """Factory that returns StubParser instances based on file name."""

    def __init__(self, mapping: Dict[str, Dict[str, List[str]]]) -> None:
        self.mapping = mapping

    def __call__(self, path: Path) -> StubParser:
        return StubParser(self.mapping[path.name])


def test_prescan_merges_foundation_joints() -> None:
    files = [Path("file1.xlsx"), Path("file2.xlsx")]
    parser_data = {
        "file1.xlsx": {
            "Story Drifts": ["DES_X"],
            "Fou": ["J1", "J2"],
        },
        "file2.xlsx": {
            "Story Drifts": ["MCE_X"],
            "Fou": ["J2", "J3"],
        },
    }
    service = ImportPreparationService(
        target_sheets={"Story Drifts": ["Story Drifts"]},
        parser_factory=StubParserFactory(parser_data),
    )

    result = service.prescan_files(files, result_types=None, progress_callback=None)

    assert list(result.file_load_cases.keys()) == ["file1.xlsx", "file2.xlsx"]
    assert result.file_load_cases["file1.xlsx"]["Story Drifts"] == ["DES_X"]
    assert result.foundation_joints == ["J1", "J2", "J3"]
    summary = result.file_summaries["file1.xlsx"]
    assert summary.available_sheets == {"Story Drifts", "Fou"}
    assert summary.foundation_joints == ["J1", "J2"]


def test_prescan_includes_vertical_displacements_when_requested() -> None:
    files = [Path("file.xlsx")]
    parser_data = {
        "file.xlsx": {
            "Joint Displacements": ["VDES_X", "VDES_Y"],
        }
    }
    service = ImportPreparationService(
        target_sheets={"Story Drifts": ["Story Drifts"]},  # not requested
        parser_factory=StubParserFactory(parser_data),
    )

    result = service.prescan_files(
        files,
        result_types={"vertical displacements"},
        progress_callback=None,
    )

    assert "Vertical Displacements" in result.file_load_cases["file.xlsx"]
    assert result.file_load_cases["file.xlsx"]["Vertical Displacements"] == ["VDES_X", "VDES_Y"]
    assert "file.xlsx" in result.file_summaries
    assert "Joint Displacements" in result.file_summaries["file.xlsx"].available_sheets


def test_prescan_records_summary_even_without_target_sheets() -> None:
    files = [Path("file.xlsx")]
    parser_data = {
        "file.xlsx": {
            "Fou": ["J1"],
            "Random Sheet": ["LC1"],
        }
    }

    service = ImportPreparationService(
        target_sheets={"Story Drifts": ["Story Drifts"]},
        parser_factory=StubParserFactory(parser_data),
    )

    result = service.prescan_files(files, result_types=None, progress_callback=None)

    assert "file.xlsx" not in result.file_load_cases
    assert "file.xlsx" in result.file_summaries
    summary = result.file_summaries["file.xlsx"]
    assert summary.available_sheets == {"Fou", "Random Sheet"}
    assert summary.foundation_joints == ["J1"]


def test_detect_conflicts_flags_duplicate_load_cases() -> None:
    file_load_cases = {
        "file1.xlsx": {"Story Drifts": ["DES_X", "MCE_X"]},
        "file2.xlsx": {"Story Drifts": ["DES_X"]},
    }
    conflicts = detect_conflicts(file_load_cases, {"DES_X"})
    assert conflicts == {"DES_X": {"Story Drifts": ["file1.xlsx", "file2.xlsx"]}}


def test_determine_allowed_load_cases_honors_resolution() -> None:
    file_sheets = {"Story Drifts": ["DES_X", "MCE_X"]}
    selected = {"DES_X", "MCE_X"}
    resolution = {
        "Story Drifts": {
            "DES_X": "file1.xlsx",
            "MCE_X": None,
        }
    }
    already_imported = {"Story Drifts": {"DES_X"}}

    allowed, skipped = determine_allowed_load_cases(
        file_name="file1.xlsx",
        file_sheets=file_sheets,
        selected_load_cases=selected,
        resolution=resolution,
        already_imported=already_imported,
    )

    assert allowed == {"DES_X"}
    assert "MCE_X (user skipped)" in skipped["Story Drifts"]
