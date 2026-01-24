"""Signal consistency tests for worker threads."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from gui.components.import_dialog_base import BaseImportWorker
from gui.dialogs.import_.folder_import_dialog import LoadCaseScanWorker, FolderImportWorker
from gui.dialogs.import_.import_project_dialog import ImportProjectWorker
from gui.dialogs.import_.pushover_global_import_dialog import PushoverImportWorker, PushoverScanWorker
from gui.dialogs.import_.time_history_import_dialog import TimeHistoryImportWorker, TimeHistoryPrescanWorker


class _DummyContext:
    name = "TestProject"

    def session_factory(self):
        return lambda: None


def _build_workers():
    return [
        BaseImportWorker(),
        LoadCaseScanWorker(Path("C:/tmp")),
        FolderImportWorker(
            context=_DummyContext(),
            folder_path=Path("C:/tmp"),
            result_set_name="DES",
        ),
        TimeHistoryPrescanWorker(Path("C:/tmp")),
        TimeHistoryImportWorker(
            session_factory=lambda: None,
            file_paths=[],
            project_id=1,
            result_set_id=1,
            selected_load_cases=set(),
        ),
        PushoverScanWorker(Path("C:/tmp")),
        PushoverImportWorker(
            project_id=1,
            session_factory=lambda: None,
            folder_path=Path("C:/tmp"),
            result_set_name="DES",
            global_files=[],
            wall_files=[],
            column_files=[],
            beam_files=[],
            selected_load_cases_x=[],
            selected_load_cases_y=[],
        ),
        ImportProjectWorker(MagicMock()),
    ]


def test_all_workers_have_consistent_signal_signatures(qt_app):
    """Workers emit progress with (str, int, int)."""
    for worker in _build_workers():
        worker.progress.emit("Step", 1, 2)


def test_progress_signal_params_are_str_int_int(qt_app):
    """Progress signals reject missing parameters."""
    worker = BaseImportWorker()
    worker.progress.emit("Step", 1, 2)
    with pytest.raises(TypeError):
        worker.progress.emit("Step")


def test_finished_signal_emits_on_completion(qt_app):
    """Finished signal delivers payload."""

    class DummyWorker(BaseImportWorker):
        def run(self):
            self.finished.emit({"ok": True})

    worker = DummyWorker()
    seen = {}

    def on_finished(payload):
        seen["payload"] = payload

    worker.finished.connect(on_finished)
    worker.run()

    assert seen["payload"] == {"ok": True}


def test_error_signal_includes_message(qt_app):
    """Error signal includes message string."""
    worker = BaseImportWorker()
    messages = []
    worker.error.connect(messages.append)

    worker.error.emit("Boom")
    assert messages == ["Boom"]
