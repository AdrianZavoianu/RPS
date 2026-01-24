"""Tests for import dialogs and base helpers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from PyQt6.QtCore import QThread
from PyQt6.QtWidgets import QDialog

from gui.components.import_dialog_base import BaseImportWorker, ImportDialogBase
from gui.dialogs.import_.folder_import_dialog import FolderImportDialog
from gui.dialogs.import_.pushover_import_dialog import PushoverImportDialog
from gui.dialogs.import_.time_history_import_dialog import TimeHistoryImportDialog
from services.import_preparation import PrescanResult


def test_folder_import_dialog_setup_ui(qt_app):
    """Dialog builds core widgets and starts disabled."""
    dialog = FolderImportDialog()

    assert dialog.import_btn.isEnabled() is False
    assert dialog.folder_input is not None
    assert dialog.result_set_input is not None
    assert dialog.load_case_checkboxes == {}


def test_folder_import_dialog_prescan(qt_app):
    """Prescan results populate load case checkboxes."""
    dialog = FolderImportDialog()

    prescan = PrescanResult(
        file_load_cases={
            "file1.xlsx": {
                "Story Drifts": ["DES_X", "DES_Y"],
                "Story Forces": ["MCE_X"],
            },
            "file2.xlsx": {"Story Drifts": ["DES_X"]},
        },
        files_scanned=2,
    )

    dialog._on_scan_finished(prescan)

    assert set(dialog.load_case_checkboxes.keys()) == {"DES_X", "DES_Y", "MCE_X"}
    assert dialog.select_all_lc_btn.isEnabled() is True
    assert dialog.select_none_lc_btn.isEnabled() is True


def test_worker_signal_emission_format(qt_app):
    """Base worker emits progress with expected signature."""
    worker = BaseImportWorker()
    seen = {}

    def on_progress(message, current, total):
        seen["args"] = (message, current, total)

    worker.progress.connect(on_progress)
    worker._emit_progress("Scanning", 1, 4)

    assert seen["args"] == ("Scanning", 1, 4)


def test_progress_updates_reach_ui(qt_app):
    """ImportDialogBase updates progress bar and log text."""

    class DummyDialog(ImportDialogBase):
        def _setup_specific_ui(self) -> None:
            self._progress_bar, self._log_text, group = self._create_progress_section()
            self._main_layout.addWidget(group)

        def _on_browse(self) -> None:
            pass

        def _start_import(self) -> None:
            pass

    dialog = DummyDialog()
    dialog._update_progress("Step 1", 1, 4)

    assert dialog._progress_bar.value() == 25
    assert "Step 1" in dialog._log_text.toPlainText()


def test_import_dialog_base_inheritance():
    """Base classes inherit Qt types."""
    assert issubclass(ImportDialogBase, QDialog)
    assert issubclass(BaseImportWorker, QThread)


def test_pushover_import_dialog_validation(qt_app):
    """Missing required fields trigger warnings."""
    dialog = PushoverImportDialog(
        project_id=1,
        project_name="Test",
        session_factory=lambda: None,
    )

    with patch("gui.dialogs.import_.pushover_import_dialog.QMessageBox.warning") as warn:
        dialog._on_import()
        dialog.file_path = Path("fake.xlsx")
        dialog._on_import()
        dialog.result_set_edit.setText("RS1")
        dialog._on_import()

        assert warn.call_args_list[0][0][1] == "No File"
        assert warn.call_args_list[1][0][1] == "No Result Set"
        assert warn.call_args_list[2][0][1] == "No Base Story"


def test_time_history_import_dialog_load_cases(qt_app, monkeypatch):
    """Scan results populate load case list and enable import."""
    monkeypatch.setattr(TimeHistoryImportDialog, "_load_result_sets", lambda self: None)
    dialog = TimeHistoryImportDialog(
        project_id=1,
        project_name="Test",
        session_factory=lambda: None,
    )

    dialog.folder_path = Path("C:/tmp")
    dialog.result_set_combo.addItem("DES", 1)
    dialog.result_set_combo.setCurrentIndex(0)

    file_load_cases = {
        "C:/tmp/th01.xlsx": "TH01",
        "C:/tmp/th02.xlsx": "TH02",
    }

    dialog._on_scan_finished(file_load_cases)

    assert set(dialog.load_case_checkboxes.keys()) == {"TH01", "TH02"}
    assert dialog.import_btn.isEnabled() is True
