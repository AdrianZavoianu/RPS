"""Project detail export/reporting actions."""

from __future__ import annotations

from config.analysis_types import AnalysisType


def export_results(window):
    """Export results to file - contextual based on active mode."""
    if window.controller.get_active_context() == AnalysisType.PUSHOVER:
        window.export_pushover_results()
    else:
        window.export_nltha_results()


def export_nltha_results(window):
    """Export NLTHA results."""
    from gui.export import ComprehensiveExportDialog

    result_set_id = window.controller.selection.result_set_id
    if not result_set_id:
        from services.data_access import DataAccessService

        data_service = window.data_service or DataAccessService(window.context.session)
        result_sets = data_service.get_result_sets(window.project_id)
        if result_sets:
            result_set_id = result_sets[0].id
            window.controller.update_selection(result_set_id=result_set_id)
        else:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(window, "No Data", "No result sets available in this project")
            return

    from gui.ui_helpers import show_dialog_with_blur
    dialog = ComprehensiveExportDialog(
        context=window.context,
        result_service=window.result_service,
        current_result_set_id=result_set_id,
        project_name=window.project_name,
        analysis_context='NLTHA',
        parent=window
    )

    show_dialog_with_blur(dialog, window)


def open_reporting(window):
    """Open the reporting window for generating PDF reports."""
    from gui.reporting.report_window import ReportWindow
    from gui.ui_helpers import show_dialog_with_blur

    result_set_id = window.controller.selection.result_set_id
    if not result_set_id:
        from services.data_access import DataAccessService

        data_service = window.data_service or DataAccessService(window.context.session)
        result_sets = data_service.get_result_sets(window.project_id)
        nltha_sets = [rs for rs in result_sets if getattr(rs, 'analysis_type', None) != 'Pushover']
        if nltha_sets:
            result_set_id = nltha_sets[0].id
        else:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(window, "No Data", "No NLTHA result sets available in this project")
            return

    dialog = ReportWindow(window.runtime, result_set_id, parent=window, analysis_context='NLTHA')
    show_dialog_with_blur(dialog, window)


def open_pushover_reporting(window):
    """Open the reporting window for generating PDF reports for Pushover results."""
    from gui.reporting.report_window import ReportWindow
    from gui.ui_helpers import show_dialog_with_blur

    result_set_id = window.controller.selection.result_set_id
    if not result_set_id:
        from services.data_access import DataAccessService

        data_service = window.data_service or DataAccessService(window.context.session)
        result_sets = data_service.get_result_sets(window.project_id)
        pushover_sets = [rs for rs in result_sets if getattr(rs, 'analysis_type', None) == 'Pushover']
        if pushover_sets:
            result_set_id = pushover_sets[0].id
        else:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(window, "No Data", "No Pushover result sets available in this project")
            return

    dialog = ReportWindow(window.runtime, result_set_id, parent=window, analysis_context='Pushover')
    show_dialog_with_blur(dialog, window)


def export_pushover_results(window):
    """Export pushover results."""
    from gui.export import ComprehensiveExportDialog
    from PyQt6.QtWidgets import QMessageBox

    result_set_id = window.controller.selection.result_set_id
    if not result_set_id:
        from services.data_access import DataAccessService

        data_service = window.data_service or DataAccessService(window.context.session)
        result_sets = data_service.get_result_sets(window.project_id)
        pushover_sets = [rs for rs in result_sets if getattr(rs, 'analysis_type', None) == 'Pushover']
        if pushover_sets:
            result_set_id = pushover_sets[0].id
            window.controller.update_selection(result_set_id=result_set_id)
        else:
            QMessageBox.warning(
                window,
                "No Pushover Data",
                "No pushover result sets found in this project.\n\n"
                "Please import pushover curves or global results first."
            )
            return

    from gui.ui_helpers import show_dialog_with_blur
    dialog = ComprehensiveExportDialog(
        context=window.context,
        result_service=window.result_service,
        current_result_set_id=result_set_id,
        project_name=window.project_name,
        analysis_context='Pushover',
        parent=window
    )

    show_dialog_with_blur(dialog, window)


def export_project_excel(window):
    """Export complete project to Excel workbook."""
    from gui.export import ExportProjectExcelDialog

    dialog = ExportProjectExcelDialog(
        context=window.context,
        result_service=window.result_service,
        project_name=window.project_name,
        parent=window
    )

    dialog.exec()


__all__ = [
    "export_results",
    "export_nltha_results",
    "open_reporting",
    "open_pushover_reporting",
    "export_pushover_results",
    "export_project_excel",
]
