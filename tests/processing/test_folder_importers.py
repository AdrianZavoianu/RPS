"""Tests confirming folder importers aggregate stats correctly."""

from __future__ import annotations

import types
from pathlib import Path

from processing.folder_importer import FolderImporter
from processing.enhanced_folder_importer import EnhancedFolderImporter


class DummySession:
    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        pass


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
        "processing.enhanced_folder_importer.SelectiveDataImporter",
        StubSelectiveImporter,
    )
    _patch_repositories(monkeypatch, "processing.enhanced_folder_importer")

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
