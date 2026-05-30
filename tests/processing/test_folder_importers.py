"""Tests confirming folder importers aggregate stats correctly."""

from __future__ import annotations

import types
from pathlib import Path

from processing.folder_importer import FolderImporter
from processing.folder_importer import EnhancedFolderImporter
from processing.selective_data_importer import SelectiveDataImporter


class DummySession:
    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        pass

    def query(self, *args, **kwargs):
        class DummyQuery:
            def filter(self, *args, **kwargs):
                return self

            def filter_by(self, *args, **kwargs):
                return self

            def first(self):
                return types.SimpleNamespace(id=1)

            def all(self):
                return []

        return DummyQuery()


def _dummy_session_factory():
    return DummySession()


def _patch_repositories(monkeypatch, module_prefix: str):
    class DummyProjectRepo:
        def __init__(self, session):
            pass

        def get_by_name(self, name):
            return types.SimpleNamespace(id=1)

    class DummyLoadCaseRepo:
        def __init__(self, session):
            pass

        def get_by_project(self, project_id):
            return [1, 2]

    class DummyStoryRepo:
        def __init__(self, session):
            pass

        def get_by_project(self, project_id):
            return [1]

    monkeypatch.setattr(f"{module_prefix}.ProjectRepository", DummyProjectRepo)
    monkeypatch.setattr(f"{module_prefix}.LoadCaseRepository", DummyLoadCaseRepo)
    monkeypatch.setattr(f"{module_prefix}.StoryRepository", DummyStoryRepo)


def test_folder_importer_aggregates_stats(tmp_path, monkeypatch):
    folder = tmp_path / "imports"
    folder.mkdir()
    file1 = folder / "file1.xlsx"
    file2 = folder / "file2.xlsx"
    file1.write_text("", encoding="utf-8")
    file2.write_text("", encoding="utf-8")

    stats_by_file = {
        str(file1): {"project": "Tower", "drifts": 5, "errors": ["warn1"]},
        str(file2): {"project": "Tower", "forces": 2},
    }

    class StubImporter:
        def __init__(self, file_path, *args, **kwargs):
            self.file_path = file_path

        def import_all(self):
            return stats_by_file[self.file_path]

    class StubParser:
        def __init__(self, path):
            self.path = Path(path)

        def get_available_sheets(self):
            if self.path.name == "file1.xlsx":
                return ["Story Drifts"]
            return ["Story Forces"]

    monkeypatch.setattr("processing.folder_importer.DataImporter", StubImporter)
    monkeypatch.setattr("processing.folder_importer.ExcelParser", StubParser)
    _patch_repositories(monkeypatch, "processing.folder_importer")

    importer = FolderImporter(
        folder_path=str(folder),
        project_name="Tower",
        result_set_name="DES",
        session_factory=_dummy_session_factory,
    )

    stats = importer.import_all()

    assert stats["files_processed"] == 2
    assert stats["drifts"] == 5
    assert stats["forces"] == 2
    assert "warn1" in stats["errors"]


def test_enhanced_folder_importer_shares_aggregator(tmp_path, monkeypatch):
    folder = tmp_path / "enhanced"
    folder.mkdir()
    file1 = folder / "file1.xlsx"
    file1.write_text("", encoding="utf-8")

    class StubSelectiveImporter:
        def __init__(self, file_path, *args, **kwargs):
            self.file_path = file_path

        def import_all(self):
            return {
                "project": "Tower",
                "displacements": 4,
                "errors": ["resolved"],
                "phase_timings": [{"phase": "dummy", "duration": 0.1}],
            }

        def generate_cache_if_needed(self):
            pass

    monkeypatch.setattr(
        "processing.folder_importer.SelectiveDataImporter",
        StubSelectiveImporter,
    )
    _patch_repositories(monkeypatch, "processing.folder_importer")

    def fake_prescan(self):
        return ({file1.name: {"Story Drifts": ["LC1"]}}, [])

    def fake_allowed(self, *args, **kwargs):
        return {"LC1"}

    monkeypatch.setattr(
        EnhancedFolderImporter,
        "_prescan_load_cases",
        fake_prescan,
    )
    monkeypatch.setattr(
        EnhancedFolderImporter,
        "_get_allowed_load_cases",
        fake_allowed,
    )

    importer = EnhancedFolderImporter(
        folder_path=str(folder),
        project_name="Tower",
        result_set_name="DES",
        session_factory=_dummy_session_factory,
        selected_load_cases={"LC1"},
    )

    stats = importer.import_all()

    assert stats["files_processed"] == 1
    assert stats["displacements"] == 4
    assert "resolved" in stats["errors"]


def test_enhanced_folder_importer_allows_load_cases_by_result_type_task(tmp_path):
    folder = tmp_path / "enhanced_task_scope"
    folder.mkdir()

    importer = EnhancedFolderImporter(
        folder_path=str(folder),
        project_name="Tower",
        result_set_name="DES",
        session_factory=_dummy_session_factory,
        selected_load_cases={"LC1"},
    )

    allowed_by_task = importer._get_allowed_load_cases_by_task(
        file_name="file1.xlsx",
        file_sheets={
            "Story Drifts": ["LC1"],
            "Story Forces": ["LC1"],
        },
        selected_load_cases={"LC1"},
        resolution={},
        already_imported={"Story Drifts": {"LC1"}},
    )

    assert "Story Drifts" not in allowed_by_task
    assert allowed_by_task["Story Forces"] == {"LC1"}


def test_selective_importer_missing_task_scope_does_not_fall_back_to_file_scope():
    importer = SelectiveDataImporter.__new__(SelectiveDataImporter)
    importer.allowed_load_cases = {"LC1"}
    importer.allowed_load_cases_by_task = {"Story Forces": {"LC1"}}

    assert importer._task_load_cases("Story Drifts") == set()
    assert importer._task_load_cases("Story Forces") == {"LC1"}


def test_enhanced_folder_importer_reads_nested_existing_resolution(tmp_path):
    folder = tmp_path / "enhanced_nested_resolution"
    folder.mkdir()

    importer = EnhancedFolderImporter(
        folder_path=str(folder),
        project_name="Tower",
        result_set_name="DES",
        session_factory=_dummy_session_factory,
        selected_load_cases={"LC1"},
        existing_data_resolution={
            "LC1": {
                "Story Drifts": "keep",
                "Story Forces": "replace",
            }
        },
    )

    assert importer._existing_data_action("LC1", "Story Drifts") == "keep"
    assert importer._existing_data_action("LC1", "Story Forces") == "replace"
