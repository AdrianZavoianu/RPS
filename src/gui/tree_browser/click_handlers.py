"""Click handlers for ResultsTreeBrowser.

This module contains the item click handler that dispatches to appropriate
signal emitters based on tree item type.
"""

import logging
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QTreeWidgetItem

if TYPE_CHECKING:
    from .browser import ResultsTreeBrowser

logger = logging.getLogger(__name__)


def on_item_clicked(
    browser: "ResultsTreeBrowser",
    item: QTreeWidgetItem,
    column: int,
) -> None:
    """Handle tree item click.

    Dispatches to appropriate signal emitter based on the item type.

    Args:
        browser: ResultsTreeBrowser instance with signals
        item: The clicked tree widget item
        column: Column index (unused, always 0)
    """
    data = item.data(0, Qt.ItemDataRole.UserRole)
    if not data or not isinstance(data, dict):
        return

    item_type = data.get("type")

    # Standard NLTHA result type clicks
    if item_type == "result_type":
        _handle_result_type(browser, data)
    elif item_type == "maxmin_results":
        _handle_maxmin_results(browser, data)
    elif item_type == "element_maxmin_results":
        _handle_element_maxmin_results(browser, data)
    elif item_type == "all_rotations":
        _handle_all_rotations(browser, data)
    elif item_type == "all_column_rotations":
        _handle_all_column_rotations(browser, data)
    elif item_type == "beam_rotations_plot":
        _handle_beam_rotations_plot(browser, data)
    elif item_type == "beam_rotations_table":
        _handle_beam_rotations_table(browser, data)
    elif item_type == "soil_pressure_plot":
        _handle_soil_pressure_plot(browser, data)
    elif item_type == "soil_pressure_table":
        _handle_soil_pressure_table(browser, data)
    elif item_type == "vertical_displacement_plot":
        _handle_vertical_displacement_plot(browser, data)
    elif item_type == "vertical_displacement_table":
        _handle_vertical_displacement_table(browser, data)

    # Comparison set clicks
    elif item_type == "comparison_result_type":
        _handle_comparison_result_type(browser, data)
    elif item_type == "comparison_element_result":
        _handle_comparison_element_result(browser, data)
    elif item_type == "comparison_all_rotations":
        _handle_comparison_all_rotations(browser, data)
    elif item_type == "comparison_all_joints":
        _handle_comparison_all_joints(browser, data)

    # Pushover clicks
    elif item_type == "pushover_global_result":
        _handle_pushover_global_result(browser, data)
    elif item_type == "pushover_curve":
        _handle_pushover_curve(browser, data)
    elif item_type == "pushover_all_curves":
        _handle_pushover_all_curves(browser, data)
    elif item_type == "pushover_wall_result":
        _handle_pushover_wall_result(browser, data)
    elif item_type == "pushover_quad_rotation_result":
        _handle_pushover_quad_rotation_result(browser, data)
    elif item_type == "pushover_column_result":
        _handle_pushover_column_result(browser, data)
    elif item_type == "pushover_column_shear_result":
        _handle_pushover_column_shear_result(browser, data)
    elif item_type == "pushover_beam_result":
        _handle_pushover_beam_result(browser, data)
    elif item_type == "pushover_all_column_rotations":
        _handle_pushover_all_column_rotations(browser, data)
    elif item_type == "pushover_beam_rotations_plot":
        _handle_pushover_beam_rotations_plot(browser, data)
    elif item_type == "pushover_beam_rotations_table":
        _handle_pushover_beam_rotations_table(browser, data)
    elif item_type == "pushover_joint_displacement_result":
        _handle_pushover_joint_displacement_result(browser, data)
    elif item_type == "pushover_soil_pressure_plot":
        _handle_pushover_soil_pressure_plot(browser, data)
    elif item_type == "pushover_soil_pressure_table":
        _handle_pushover_soil_pressure_table(browser, data)
    elif item_type == "pushover_vertical_displacement_plot":
        _handle_pushover_vertical_displacement_plot(browser, data)
    elif item_type == "pushover_vertical_displacement_table":
        _handle_pushover_vertical_displacement_table(browser, data)


# ============================================================================
# NLTHA Result Handlers
# ============================================================================


def _handle_result_type(browser: "ResultsTreeBrowser", data: dict) -> None:
    """Handle standard result type click."""
    result_set_id = data.get("result_set_id")
    category = data.get("category")
    result_type = data.get("result_type")
    direction = data.get("direction", "X")
    element_id = data.get("element_id", 0)
    browser.selection_changed.emit(result_set_id, category, result_type, direction, element_id)


def _handle_maxmin_results(browser: "ResultsTreeBrowser", data: dict) -> None:
    """Handle Max/Min results click."""
    result_set_id = data.get("result_set_id")
    category = data.get("category")
    result_type = data.get("result_type")
    browser.selection_changed.emit(result_set_id, category, result_type, "", 0)


def _handle_element_maxmin_results(browser: "ResultsTreeBrowser", data: dict) -> None:
    """Handle element-specific Max/Min results click."""
    result_set_id = data.get("result_set_id")
    category = data.get("category")
    result_type = data.get("result_type")
    element_id = data.get("element_id", 0)
    browser.selection_changed.emit(result_set_id, category, result_type, "", element_id)


def _handle_all_rotations(browser: "ResultsTreeBrowser", data: dict) -> None:
    """Handle All Rotations view click."""
    result_set_id = data.get("result_set_id")
    category = data.get("category")
    browser.selection_changed.emit(result_set_id, category, "AllQuadRotations", "", -1)


def _handle_all_column_rotations(browser: "ResultsTreeBrowser", data: dict) -> None:
    """Handle All Column Rotations view click."""
    result_set_id = data.get("result_set_id")
    category = data.get("category")
    browser.selection_changed.emit(result_set_id, category, "AllColumnRotations", "", -1)


def _handle_beam_rotations_plot(browser: "ResultsTreeBrowser", data: dict) -> None:
    """Handle Beam Rotations Plot view click."""
    result_set_id = data.get("result_set_id")
    category = data.get("category")
    browser.selection_changed.emit(result_set_id, category, "AllBeamRotations", "", -1)


def _handle_beam_rotations_table(browser: "ResultsTreeBrowser", data: dict) -> None:
    """Handle Beam Rotations Table view click."""
    result_set_id = data.get("result_set_id")
    category = data.get("category")
    browser.selection_changed.emit(result_set_id, category, "BeamRotationsTable", "", -1)


def _handle_soil_pressure_plot(browser: "ResultsTreeBrowser", data: dict) -> None:
    """Handle Soil Pressure Plot view click."""
    result_set_id = data.get("result_set_id")
    category = data.get("category")
    browser.selection_changed.emit(result_set_id, category, "AllSoilPressures", "", -3)


def _handle_soil_pressure_table(browser: "ResultsTreeBrowser", data: dict) -> None:
    """Handle Soil Pressure Table view click."""
    result_set_id = data.get("result_set_id")
    category = data.get("category")
    browser.selection_changed.emit(result_set_id, category, "SoilPressuresTable", "", -4)


def _handle_vertical_displacement_plot(browser: "ResultsTreeBrowser", data: dict) -> None:
    """Handle Vertical Displacement Plot view click."""
    result_set_id = data.get("result_set_id")
    category = data.get("category")
    browser.selection_changed.emit(result_set_id, category, "AllVerticalDisplacements", "", -5)


def _handle_vertical_displacement_table(browser: "ResultsTreeBrowser", data: dict) -> None:
    """Handle Vertical Displacement Table view click."""
    result_set_id = data.get("result_set_id")
    category = data.get("category")
    browser.selection_changed.emit(result_set_id, category, "VerticalDisplacementsTable", "", -6)


# ============================================================================
# Comparison Result Handlers
# ============================================================================


def _handle_comparison_result_type(browser: "ResultsTreeBrowser", data: dict) -> None:
    """Handle comparison set result type click."""
    comparison_set_id = data.get("comparison_set_id")
    result_type = data.get("result_type")
    direction = data.get("direction", "X")
    browser.comparison_selected.emit(comparison_set_id, result_type, direction)


def _handle_comparison_element_result(browser: "ResultsTreeBrowser", data: dict) -> None:
    """Handle comparison set element result click."""
    comparison_set_id = data.get("comparison_set_id")
    result_type = data.get("result_type")
    element_id = data.get("element_id")
    direction = data.get("direction")
    browser.comparison_element_selected.emit(comparison_set_id, result_type, element_id, direction)


def _handle_comparison_all_rotations(browser: "ResultsTreeBrowser", data: dict) -> None:
    """Handle comparison all rotations view click."""
    comparison_set_id = data.get("comparison_set_id")
    result_type = data.get("result_type")
    browser.comparison_selected.emit(comparison_set_id, result_type, "All")


def _handle_comparison_all_joints(browser: "ResultsTreeBrowser", data: dict) -> None:
    """Handle comparison all joints click."""
    comparison_set_id = data.get("comparison_set_id")
    result_type = data.get("result_type")
    browser.comparison_selected.emit(comparison_set_id, result_type, "AllJoints")


# ============================================================================
# Pushover Result Handlers
# ============================================================================


def _handle_pushover_global_result(browser: "ResultsTreeBrowser", data: dict) -> None:
    """Handle pushover global result click."""
    result_set_id = data.get("result_set_id")
    result_type = data.get("result_type")
    direction = data.get("direction")

    # Map display name to internal type
    type_map = {
        "Story Drifts": "Drifts",
        "Story Forces": "Forces",
        "Floor Displacements": "Displacements"
    }
    internal_type = type_map.get(result_type, result_type)
    browser.selection_changed.emit(result_set_id, "Pushover", internal_type, direction, 0)


def _handle_pushover_curve(browser: "ResultsTreeBrowser", data: dict) -> None:
    """Handle pushover curve click."""
    result_set_id = data.get("result_set_id")
    case_name = data.get("case_name")
    browser.selection_changed.emit(result_set_id, "Pushover", "Curves", case_name, 0)


def _handle_pushover_all_curves(browser: "ResultsTreeBrowser", data: dict) -> None:
    """Handle all pushover curves in a direction click."""
    result_set_id = data.get("result_set_id")
    direction = data.get("direction")
    browser.selection_changed.emit(result_set_id, "Pushover", "AllCurves", direction, 0)


def _handle_pushover_wall_result(browser: "ResultsTreeBrowser", data: dict) -> None:
    """Handle pushover wall result click."""
    result_set_id = data.get("result_set_id")
    result_type = data.get("result_type")
    direction = data.get("direction")
    element_id = data.get("element_id")
    browser.selection_changed.emit(result_set_id, "Pushover", result_type, direction, element_id)


def _handle_pushover_quad_rotation_result(browser: "ResultsTreeBrowser", data: dict) -> None:
    """Handle pushover quad rotation result click."""
    result_set_id = data.get("result_set_id")
    result_type = data.get("result_type")
    direction = data.get("direction")
    element_id = data.get("element_id")
    browser.selection_changed.emit(result_set_id, "Pushover", result_type, direction, element_id)


def _handle_pushover_column_result(browser: "ResultsTreeBrowser", data: dict) -> None:
    """Handle pushover column rotation result click."""
    result_set_id = data.get("result_set_id")
    direction = data.get("direction")
    element_id = data.get("element_id")

    logger.debug(
        "Browser: pushover_column_result clicked - result_type=%s, direction=%s, element_id=%s",
        "ColumnRotations",
        direction,
        element_id,
    )
    browser.selection_changed.emit(result_set_id, "Pushover", "ColumnRotations", direction, element_id)


def _handle_pushover_column_shear_result(browser: "ResultsTreeBrowser", data: dict) -> None:
    """Handle pushover column shear result click."""
    result_set_id = data.get("result_set_id")
    result_type = data.get("result_type")
    direction = data.get("direction")
    element_id = data.get("element_id")

    logger.debug(
        "Browser: pushover_column_shear_result clicked - result_type=%s, direction=%s, element_id=%s",
        result_type,
        direction,
        element_id,
    )
    browser.selection_changed.emit(result_set_id, "Pushover", result_type, direction, element_id)


def _handle_pushover_beam_result(browser: "ResultsTreeBrowser", data: dict) -> None:
    """Handle pushover beam rotation result click."""
    result_set_id = data.get("result_set_id")
    result_type = data.get("result_type")
    direction = data.get("direction")
    element_id = data.get("element_id")

    logger.debug(
        "Browser: pushover_beam_result clicked - result_type=%s, element_id=%s",
        result_type,
        element_id,
    )
    browser.selection_changed.emit(result_set_id, "Pushover", result_type, direction, element_id)


def _handle_pushover_all_column_rotations(browser: "ResultsTreeBrowser", data: dict) -> None:
    """Handle All Column Rotations view click in pushover context."""
    result_set_id = data.get("result_set_id")
    category = data.get("category")

    logger.debug("Browser: pushover_all_column_rotations clicked - result_type=%s", "AllColumnRotations")
    browser.selection_changed.emit(result_set_id, category, "AllColumnRotations", "", -1)


def _handle_pushover_beam_rotations_plot(browser: "ResultsTreeBrowser", data: dict) -> None:
    """Handle All Beam Rotations plot view click in pushover context."""
    result_set_id = data.get("result_set_id")
    category = data.get("category")

    logger.debug("Browser: pushover_beam_rotations_plot clicked - result_type=%s", "AllBeamRotations")
    browser.selection_changed.emit(result_set_id, category, "AllBeamRotations", "", -1)


def _handle_pushover_beam_rotations_table(browser: "ResultsTreeBrowser", data: dict) -> None:
    """Handle Beam Rotations table view click in pushover context."""
    result_set_id = data.get("result_set_id")
    category = data.get("category")

    logger.debug("Browser: pushover_beam_rotations_table clicked - result_type=%s", "BeamRotationsTable")
    browser.selection_changed.emit(result_set_id, category, "BeamRotationsTable", "", -1)


def _handle_pushover_joint_displacement_result(browser: "ResultsTreeBrowser", data: dict) -> None:
    """Handle pushover joint displacement result click."""
    result_set_id = data.get("result_set_id")
    result_type = data.get("result_type")
    direction = data.get("direction")

    logger.debug(
        "Browser: pushover_joint_displacement_result clicked - result_type=%s, direction=%s",
        result_type,
        direction,
    )
    browser.selection_changed.emit(result_set_id, "Pushover", result_type, direction, -7)


def _handle_pushover_soil_pressure_plot(browser: "ResultsTreeBrowser", data: dict) -> None:
    """Handle Pushover Soil Pressure Plot view click."""
    result_set_id = data.get("result_set_id")
    category = data.get("category")

    logger.debug("Browser: pushover_soil_pressure_plot clicked - result_type=%s", "AllSoilPressures")
    browser.selection_changed.emit(result_set_id, category, "AllSoilPressures", "", -3)


def _handle_pushover_soil_pressure_table(browser: "ResultsTreeBrowser", data: dict) -> None:
    """Handle Pushover Soil Pressure Table view click."""
    result_set_id = data.get("result_set_id")
    category = data.get("category")

    logger.debug("Browser: pushover_soil_pressure_table clicked - result_type=%s", "SoilPressuresTable")
    browser.selection_changed.emit(result_set_id, category, "SoilPressuresTable", "", -4)


def _handle_pushover_vertical_displacement_plot(browser: "ResultsTreeBrowser", data: dict) -> None:
    """Handle Pushover Vertical Displacement Plot view click."""
    result_set_id = data.get("result_set_id")
    category = data.get("category")

    logger.debug("Browser: pushover_vertical_displacement_plot clicked - result_type=%s", "AllVerticalDisplacements")
    browser.selection_changed.emit(result_set_id, category, "AllVerticalDisplacements", "", -5)


def _handle_pushover_vertical_displacement_table(browser: "ResultsTreeBrowser", data: dict) -> None:
    """Handle Pushover Vertical Displacement Table view click."""
    result_set_id = data.get("result_set_id")
    category = data.get("category")

    logger.debug("Browser: pushover_vertical_displacement_table clicked - result_type=%s", "VerticalDisplacementsTable")
    browser.selection_changed.emit(result_set_id, category, "VerticalDisplacementsTable", "", -6)
