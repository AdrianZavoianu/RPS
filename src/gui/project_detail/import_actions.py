"""Project detail import actions."""

from __future__ import annotations

import logging

from PyQt6.QtWidgets import QDialog

from utils.error_handling import log_exception

logger = logging.getLogger(__name__)


def load_data_from_folder(window):
    """Load data from folder into current project."""
    from PyQt6.QtWidgets import QMessageBox
    from gui.dialogs.import_.folder_import_dialog import FolderImportDialog
    from gui.ui_helpers import show_dialog_with_blur

    dialog = FolderImportDialog(window, context=window.context)

    if show_dialog_with_blur(dialog, window) == QDialog.DialogCode.Accepted:
        window.session.expire_all()
        result_set_id = getattr(dialog, "last_result_set_id", None)
        if result_set_id:
            window.result_service.invalidate_result_set(result_set_id)
        else:
            window.result_service.invalidate_all()
        window.load_project_data()

        sel = window.controller.selection
        if sel.result_type and sel.result_set_id:
            if sel.result_type.startswith("MaxMin"):
                base_type = window._extract_base_result_type(sel.result_type)
                window.result_service.invalidate_maxmin_dataset(sel.result_set_id, base_type)
                window.load_maxmin_dataset(sel.result_set_id, base_type)
            elif sel.element_id > 0:
                window.result_service.invalidate_element_dataset(
                    sel.element_id, sel.result_type, sel.direction, sel.result_set_id
                )
                window.load_element_dataset(sel.element_id, sel.result_type, sel.direction, sel.result_set_id)
            else:
                window.result_service.invalidate_standard_dataset(sel.result_type, sel.direction, sel.result_set_id)
                window.load_standard_dataset(sel.result_type, sel.direction, sel.result_set_id)

        QMessageBox.information(
            window,
            "Load Complete",
            f"Successfully loaded data into project: {window.project_name}\n\n"
            f"The results browser has been refreshed."
        )


def load_pushover_curves(window):
    """Load pushover curves from Excel file."""
    from gui.dialogs.import_.pushover_import_dialog import PushoverImportDialog
    from gui.ui_helpers import show_dialog_with_blur

    dialog = PushoverImportDialog(
        project_id=window.project.id,
        project_name=window.project_name,
        session_factory=window.context.session_factory(),
        parent=window
    )

    dialog.import_completed.connect(lambda stats: window._on_pushover_import_completed(stats))

    show_dialog_with_blur(dialog, window)


def on_pushover_import_completed(window, stats: dict):
    """Handle pushover import completion."""
    window.session.expire_all()
    result_set_id = stats.get("result_set_id")
    if result_set_id:
        window.result_service.invalidate_result_set(result_set_id)
    else:
        window.result_service.invalidate_all()
    window.load_project_data()
    logger.info("Imported %d pushover curves into %s", stats['curves_imported'], stats['result_set_name'])


def load_pushover_results(window):
    """Load pushover global results from folder."""
    from PyQt6.QtWidgets import QFileDialog, QMessageBox
    from gui.dialogs.import_.pushover_global_import_dialog import PushoverGlobalImportDialog
    from gui.ui_helpers import show_dialog_with_blur

    folder_path = QFileDialog.getExistingDirectory(
        window,
        "Select Folder with Pushover Global Results",
        "",
        QFileDialog.Option.ShowDirsOnly
    )

    if not folder_path:
        return

    try:
        dialog = PushoverGlobalImportDialog(
            project_id=window.project.id,
            project_name=window.project_name,
            folder_path=folder_path,
            session_factory=window.context.session_factory(),
            parent=window
        )

        dialog.import_completed.connect(lambda stats: window._on_pushover_global_import_completed(stats))

        show_dialog_with_blur(dialog, window)

    except Exception as e:
        QMessageBox.critical(
            window,
            "Import Error",
            f"Failed to open pushover global import dialog:\n\n{str(e)}"
        )
        log_exception(e, "Failed to open pushover global import dialog")


def on_pushover_global_import_completed(window, stats: dict):
    """Handle pushover global results import completion."""
    window.session.expire_all()
    result_set_id = stats.get("result_set_id")
    if result_set_id:
        window.result_service.invalidate_result_set(result_set_id)
    else:
        window.result_service.invalidate_all()
    window.load_project_data()
    logger.info("Imported pushover global results: %d result types", stats.get('result_types_imported', 0))


def load_time_series(window):
    """Load time history data for animated visualization."""
    from PyQt6.QtWidgets import QMessageBox
    from gui.dialogs.import_.time_history_import_dialog import TimeHistoryImportDialog
    from gui.ui_helpers import show_dialog_with_blur

    dialog = TimeHistoryImportDialog(
        project_id=window.project.id,
        project_name=window.project_name,
        session_factory=window.context.session_factory(),
        parent=window
    )

    dialog.import_completed.connect(lambda count: window._on_time_series_import_completed(count))

    show_dialog_with_blur(dialog, window)


def on_time_series_import_completed(window, count: int):
    """Handle time series import completion."""
    window.session.expire_all()
    window.result_service.invalidate_all()
    window.load_project_data()
    logger.info("Imported %d time series records", count)


__all__ = [
    "load_data_from_folder",
    "load_pushover_curves",
    "on_pushover_import_completed",
    "load_pushover_results",
    "on_pushover_global_import_completed",
    "load_time_series",
    "on_time_series_import_completed",
]
