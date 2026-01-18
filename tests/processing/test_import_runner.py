"""Unit tests for import_runner helpers."""

from __future__ import annotations

from pathlib import Path

from processing.import_runner import merge_task_stats, run_import_tasks, task_sheets_available
from processing.import_tasks import ImportTask


class DummyTimer:
    def __init__(self):
        self.measured = []

    def measure(self, phase, extra=None):
        class _Ctx:
            def __init__(self, parent, phase, extra):
                self.parent = parent
                self.phase = phase
                self.extra = extra

            def __enter__(self_inner):
                return None

            def __exit__(self_inner, exc_type, exc, tb):
                self_inner.parent.measured.append((self_inner.phase, self_inner.extra))
                return False

        return _Ctx(self, phase, extra or {})


class Harness:
    def __init__(self):
        self.calls = []
        self.available = set()

    def _should_import(self, label: str) -> bool:
        return True

    def _sheet_available(self, name: str) -> bool:
        return name in self.available

    def handler(self, *_args, **_kwargs):
        self.calls.append("handler")
        return {"drifts": 2, "errors": ["warn"]}


def test_task_sheets_available_respects_require_all():
    task_all = ImportTask(label="All", handler="h", phase="p", sheets=("A", "B"), require_all_sheets=True)
    task_any = ImportTask(label="Any", handler="h", phase="p", sheets=("A", "B"), require_all_sheets=False)

    assert not task_sheets_available(task_all, lambda n: n == "A")
    assert task_sheets_available(task_any, lambda n: n == "A")


def test_run_import_tasks_merges_stats_and_timings():
    harness = Harness()
    harness.available = {"Sheet1"}
    task = ImportTask(label="Demo", handler="handler", phase="demo", sheets=("Sheet1",))
    timer = DummyTimer()
    stats = {"errors": []}

    run_import_tasks(
        tasks=[task],
        should_import=harness._should_import,
        sheet_available=harness._sheet_available,
        get_handler=lambda name: getattr(harness, name, None),
        phase_timer=timer,
        session=None,
        project_id=1,
        stats=stats,
        file_name="file.xlsx",
    )

    assert harness.calls == ["handler"]
    assert stats["drifts"] == 2
    assert stats["errors"] == ["warn"]
    assert ("demo", {"task": "Demo"}) in timer.measured


def test_merge_task_stats_handles_non_numeric_and_errors():
    stats = {"drifts": 1, "errors": []}
    merge_task_stats(stats, {"drifts": 2, "meta": "ok", "errors": ["boom"]})

    assert stats["drifts"] == 3
    assert stats["meta"] == "ok"
    assert stats["errors"] == ["boom"]
