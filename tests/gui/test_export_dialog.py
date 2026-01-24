"""Tests for Export dialogs and their decomposed modules.

These tests verify the export dialog components work correctly
after the decomposition refactoring.
"""

import pytest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch


class TestExportDialogImports:
    """Tests for import compatibility."""

    def test_imports_from_new_package(self):
        """Test that export classes can be imported from new package."""
        from gui.export import ComprehensiveExportDialog
        from gui.export import SimpleExportDialog
        from gui.export import ExportProjectExcelDialog
        from gui.export import ComprehensiveExportWorker
        from gui.export import ExportWorker
        from gui.export import ExportProjectExcelWorker

        assert ComprehensiveExportDialog is not None
        assert SimpleExportDialog is not None
        assert ExportProjectExcelDialog is not None
        assert ComprehensiveExportWorker is not None
        assert ExportWorker is not None
        assert ExportProjectExcelWorker is not None

    # Backward-compat wrapper tests removed - wrapper files deleted in v2.23


class TestExportWorkers:
    """Tests for export worker classes."""

    def test_workers_module_exists(self):
        """Test that workers module can be imported."""
        from gui.export import workers
        assert workers is not None

    def test_workers_has_expected_classes(self):
        """Test that workers module has expected classes."""
        from gui.export import workers

        assert hasattr(workers, 'ComprehensiveExportWorker')
        assert hasattr(workers, 'ExportWorker')
        assert hasattr(workers, 'ExportProjectExcelWorker')

    def test_comprehensive_worker_inherits_qthread(self):
        """Test that ComprehensiveExportWorker inherits from QThread."""
        from gui.export import ComprehensiveExportWorker
        from PyQt6.QtCore import QThread

        assert issubclass(ComprehensiveExportWorker, QThread)

    def test_comprehensive_export_worker_runs(self):
        """Test that comprehensive worker routes to combined export."""
        from gui.export.workers import ComprehensiveExportWorker

        worker = ComprehensiveExportWorker(
            context=MagicMock(session=MagicMock()),
            result_service=MagicMock(),
            result_set_ids=[1],
            result_types=["Drifts"],
            format_type="excel",
            is_combined=True,
            output_file=Path("out.xlsx"),
            output_folder=Path("C:/tmp"),
            analysis_context="NLTHA",
        )

        with patch.object(ComprehensiveExportWorker, "_export_combined") as combined, \
                patch.object(ComprehensiveExportWorker, "_export_per_file") as per_file:
            worker.run()
            combined.assert_called_once()
            per_file.assert_not_called()


class TestExportDialogs:
    """Tests for export dialog classes."""

    def test_dialogs_module_exists(self):
        """Test that dialogs module can be imported."""
        from gui.export import dialogs
        assert dialogs is not None

    def test_dialogs_has_expected_classes(self):
        """Test that dialogs module has expected classes."""
        from gui.export import dialogs

        assert hasattr(dialogs, 'ComprehensiveExportDialog')
        assert hasattr(dialogs, 'SimpleExportDialog')
        assert hasattr(dialogs, 'ExportProjectExcelDialog')

    def test_comprehensive_dialog_inherits_qdialog(self):
        """Test that ComprehensiveExportDialog inherits from QDialog."""
        from gui.export import ComprehensiveExportDialog
        from PyQt6.QtWidgets import QDialog

        assert issubclass(ComprehensiveExportDialog, QDialog)

    def test_export_format_selection(self, qt_app, monkeypatch):
        """CSV disables combine option; Excel re-enables it."""
        from gui.export.dialogs import ComprehensiveExportDialog

        def fake_discover_sets(self):
            self.available_result_sets = [(1, "Set1")]

        def fake_discover_types(self):
            self.available_types = {"global": ["Drifts"], "element": [], "joint": []}

        monkeypatch.setattr(ComprehensiveExportDialog, "_discover_result_sets", fake_discover_sets)
        monkeypatch.setattr(ComprehensiveExportDialog, "_discover_result_types", fake_discover_types)

        context = SimpleNamespace(name="TestProject", session=MagicMock())
        dialog = ComprehensiveExportDialog(
            context=context,
            result_service=MagicMock(),
            current_result_set_id=1,
            project_name="TestProject",
            analysis_context="NLTHA",
        )

        dialog.csv_radio.setChecked(True)
        assert dialog.combine_check.isEnabled() is False
        assert dialog.combine_check.isChecked() is False

        dialog.excel_radio.setChecked(True)
        assert dialog.combine_check.isEnabled() is True

    def test_result_set_filtering_by_context(self, qt_app, monkeypatch):
        """Discovery receives analysis_context when populating result sets."""
        from gui.export import dialogs

        class DummyDiscovery:
            def __init__(self, session):
                self.calls = []

            def discover_result_sets(self, project_name, analysis_context):
                self.calls.append(("sets", project_name, analysis_context))
                if analysis_context == "Pushover":
                    return [SimpleNamespace(id=2, name="PO")]
                return [SimpleNamespace(id=1, name="NLTHA")]

            def discover_result_types(self, result_set_ids, analysis_context):
                self.calls.append(("types", tuple(result_set_ids), analysis_context))
                return SimpleNamespace(global_types=["Drifts"], element_types=[], joint_types=[])

        monkeypatch.setattr(dialogs, "ExportDiscoveryService", DummyDiscovery)

        context = SimpleNamespace(name="TestProject", session=MagicMock())
        dialog = dialogs.ComprehensiveExportDialog(
            context=context,
            result_service=MagicMock(),
            current_result_set_id=2,
            project_name="TestProject",
            analysis_context="Pushover",
        )

        assert dialog.available_result_sets == [(2, "PO")]
        assert ("sets", "TestProject", "Pushover") in dialog.discovery_service.calls
