"""Project detail dataset loaders and comparison handlers."""

from __future__ import annotations

from PyQt6.QtWidgets import QDialog

from . import view_loaders


def load_standard_dataset(window, result_type: str, direction: str, result_set_id: int) -> None:
    """Load and display directional results for the selected type."""
    view_loaders.load_standard_dataset(window, result_type, direction, result_set_id, window.content_area)


def load_element_dataset(window, element_id: int, result_type: str, direction: str, result_set_id: int) -> None:
    """Load and display element-specific results."""
    view_loaders.load_element_dataset(window, element_id, result_type, direction, result_set_id, window.content_area)


def load_joint_dataset(window, result_type: str, result_set_id: int) -> None:
    """Load and display joint-level results."""
    view_loaders.load_joint_dataset(window, result_type, result_set_id, window.content_area)


def load_maxmin_dataset(window, result_set_id: int, base_result_type: str = "Drifts"):
    """Load and display absolute Max/Min drift results."""
    view_loaders.load_maxmin_dataset(window, result_set_id, window.content_area, base_result_type)


def load_element_maxmin_dataset(window, element_id: int, result_set_id: int, base_result_type: str = "WallShears"):
    """Load and display element-specific Max/Min results."""
    view_loaders.load_element_maxmin_dataset(
        window,
        element_id,
        result_set_id,
        window.content_area,
        base_result_type,
    )


def load_all_rotations(window, result_set_id: int):
    """Load and display all quad rotations."""
    view_loaders.load_all_rotations(window, result_set_id, window.content_area)


def load_all_column_rotations(window, result_set_id: int):
    """Load and display all column rotations."""
    view_loaders.load_all_column_rotations(window, result_set_id, window.content_area)


def load_all_beam_rotations(window, result_set_id: int):
    """Load and display all beam rotations."""
    view_loaders.load_all_beam_rotations(window, result_set_id, window.content_area)


def load_beam_rotations_table(window, result_set_id: int):
    """Load and display beam rotations table."""
    view_loaders.load_beam_rotations_table(window, result_set_id, window.content_area)


def load_all_soil_pressures(window, result_set_id: int):
    """Load and display all soil pressures as bar chart."""
    view_loaders.load_all_soil_pressures(window, result_set_id, window.content_area)


def load_soil_pressures_table(window, result_set_id: int):
    """Load and display soil pressures table."""
    view_loaders.load_soil_pressures_table(window, result_set_id, window.content_area)


def load_all_vertical_displacements(window, result_set_id: int):
    """Load and display all vertical displacements."""
    view_loaders.load_all_vertical_displacements(window, result_set_id, window.content_area)


def load_vertical_displacements_table(window, result_set_id: int):
    """Load and display vertical displacements table."""
    view_loaders.load_vertical_displacements_table(window, result_set_id, window.content_area)


def load_pushover_curve(window, case_name: str):
    """Load and display a pushover curve."""
    view_loaders.load_pushover_curve(window, case_name, window.content_area)


def load_all_pushover_curves(window, direction: str):
    """Load and display all pushover curves for a given direction."""
    view_loaders.load_all_pushover_curves(window, direction, window.content_area)


def load_comparison_all_rotations(window, comparison_set):
    """Load and display all quad rotations comparison."""
    view_loaders.load_comparison_all_rotations(window, comparison_set, window.content_area)


def load_comparison_joint_scatter(window, comparison_set, result_type: str):
    """Load and display joint results comparison scatter plot."""
    view_loaders.load_comparison_joint_scatter(window, comparison_set, result_type, window.content_area)


# -------------------------------------------------------------------------
# Project data management
# -------------------------------------------------------------------------


def create_comparison_set(window):
    """Open dialog to create a new comparison set."""
    from gui.dialogs.comparison.comparison_set_dialog import ComparisonSetDialog
    from PyQt6.QtWidgets import QMessageBox
    from services.data_access import DataAccessService

    data_service = window.data_service or DataAccessService(window.context.session)
    result_sets = data_service.get_result_sets(window.project_id)

    if len(result_sets) < 2:
        QMessageBox.warning(
            window,
            "Insufficient Result Sets",
            "You need at least 2 result sets to create a comparison.\n\n"
            "Please import more result sets first."
        )
        return

    from gui.ui_helpers import show_dialog_with_blur
    # Pass session_factory for DataAccessService usage
    dialog = ComparisonSetDialog(window.project_id, result_sets, window.context.session, window)
    if show_dialog_with_blur(dialog, window) == QDialog.DialogCode.Accepted:
        data = dialog.get_comparison_data()

        if data_service.check_comparison_set_duplicate(window.project_id, data['name']):
            QMessageBox.warning(
                window,
                "Duplicate Name",
                f"A comparison set named '{data['name']}' already exists.\n"
                "Please choose a different name."
            )
            return

        try:
            data_service.create_comparison_set(
                project_id=window.project_id,
                name=data['name'],
                result_set_ids=data['result_set_ids'],
                result_types=data['result_types'],
                description=data['description']
            )

            QMessageBox.information(
                window,
                "Comparison Set Created",
                f"Comparison set '{data['name']}' has been created successfully!\n\n"
                "Reload the project data to see it in the browser."
            )

            window.load_project_data()

        except Exception as e:
            QMessageBox.critical(
                window,
                "Error",
                f"Failed to create comparison set:\n{str(e)}"
            )


def get_available_result_types(window, result_sets):
    """Check which result types have data for each result set."""
    from services.data_access import DataAccessService

    available_types = {}
    data_service = window.data_service or DataAccessService(window.context.session)

    for result_set in result_sets:
        types_for_set = set()

        global_types = data_service.get_available_global_types([result_set.id])
        types_for_set.update(global_types)

        element_types = data_service.get_available_element_types([result_set.id])
        for result_type in element_types:
            base_type = result_type.split("_")[0]
            types_for_set.add(base_type)

        joint_types = data_service.get_available_joint_types([result_set.id])
        for result_type in joint_types:
            types_for_set.add(result_type)
            base_type = result_type.split("_")[0]
            types_for_set.add(base_type)

        if data_service.has_time_series(result_set.id):
            types_for_set.add("TimeSeriesGlobal")

        available_types[result_set.id] = types_for_set

    return available_types


__all__ = [
    "load_standard_dataset",
    "load_element_dataset",
    "load_joint_dataset",
    "load_maxmin_dataset",
    "load_element_maxmin_dataset",
    "load_all_rotations",
    "load_all_column_rotations",
    "load_all_beam_rotations",
    "load_beam_rotations_table",
    "load_all_soil_pressures",
    "load_soil_pressures_table",
    "load_all_vertical_displacements",
    "load_vertical_displacements_table",
    "load_pushover_curve",
    "load_all_pushover_curves",
    "load_comparison_all_rotations",
    "load_comparison_joint_scatter",
    "create_comparison_set",
    "get_available_result_types",
]
