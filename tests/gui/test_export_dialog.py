"""Tests for Export dialogs and their decomposed modules.

These tests verify the export dialog components work correctly
after the decomposition refactoring.
"""

import pytest
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
