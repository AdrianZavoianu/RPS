"""Tests for import task orchestration and stats aggregation."""

from __future__ import annotations

from pathlib import Path

from processing.data_importer import DataImporter
from processing.import_tasks import ImportTask
from processing.import_stats import ImportStatsAggregator


class DummyTimer:
    def measure(self, *args, **kwargs):
        class _Ctx:
            def __enter__(self_inner):
                return None

            def __exit__(self_inner, exc_type, exc, tb):
                return False

        return _Ctx()


class ImporterHarness:
    """Minimal object reusing DataImporter helpers for testing."""

    _run_import_tasks = DataImporter._run_import_tasks
    _task_sheets_available = DataImporter._task_sheets_available

    def __init__(self):
        self.result_types = None
        self._phase_timer = DummyTimer()
        self._import_tasks = ()
        self.available = set()
        self.calls: list[str] = []
        self.file_path = Path("test.xlsx")
        self._merge_task_stats = DataImporter._merge_task_stats

    def _should_import(self, label: str) -> bool:  # pragma: no cover - simple passthrough
        return True

    def _sheet_available(self, sheet_name: str) -> bool:
        return sheet_name in self.available

    def _import_fake(self, session, project_id: int):
        self.calls.append("fake")
        return {"drifts": 2}


def test_run_import_tasks_skips_when_sheet_missing():
    harness = ImporterHarness()
    harness._import_tasks = (
        ImportTask(label="Fake", handler="_import_fake", phase="fake", sheets=("Story Drifts",)),
    )
    harness.available = set()
    stats = {"drifts": 0, "errors": []}

    harness._run_import_tasks(None, 1, stats)

    assert harness.calls == []
    assert stats["drifts"] == 0


def test_run_import_tasks_updates_stats_when_handler_runs():
    harness = ImporterHarness()
    harness._import_tasks = (
        ImportTask(label="Fake", handler="_import_fake", phase="fake", sheets=(), require_all_sheets=False),
    )
    harness.available = {"anything"}
    stats = {"drifts": 0, "errors": []}

    harness._run_import_tasks(None, 1, stats)

    assert harness.calls == ["fake"]
    assert stats["drifts"] == 2


def test_import_stats_aggregator_merges_numeric_and_errors():
    aggregator = ImportStatsAggregator()
    aggregator.merge({"drifts": 3, "project": "Tower"})
    aggregator.extend_errors(["file1: boom"])
    aggregator.merge({"drifts": 2, "accelerations": 5})

    data = aggregator.as_dict()

    assert data["drifts"] == 5
    assert data["accelerations"] == 5
    assert "errors" in data
