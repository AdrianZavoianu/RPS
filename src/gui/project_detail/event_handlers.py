"""Event handlers for ProjectDetailWindow.

This module contains handlers for browser selection changes,
comparison selection, and element comparison selection.
"""

import logging
from typing import TYPE_CHECKING

from config.result_config import format_result_type_with_unit
from utils.error_handling import log_exception

if TYPE_CHECKING:
    from .window import ProjectDetailWindow

logger = logging.getLogger(__name__)


def on_browser_selection_changed(
    window: "ProjectDetailWindow",
    result_set_id: int,
    category: str,
    result_type: str,
    direction: str,
    element_id: int = 0,
) -> None:
    """Handle browser selection changes.

    Args:
        window: ProjectDetailWindow instance
        result_set_id: ID of the selected result set
        category: Category name (e.g., "Envelopes", "Pushover")
        result_type: Result type (e.g., "Drifts", "Accelerations", "WallShears", "Curves")
        direction: Direction ('X', 'Y', 'V22', 'V33', case name for pushover)
        element_id: Element ID for element-specific results (0 for global results, -1 for all elements)
    """
    from . import view_loaders

    logger.debug(
        "on_browser_selection_changed: category=%s, result_type=%s, result_set_id=%s",
        category,
        result_type,
        result_set_id,
    )

    # Automatically switch context based on result set's analysis type
    result_set = window.result_set_repo.get_by_id(result_set_id) if result_set_id else None
    if result_set:
        analysis_type = getattr(result_set, "analysis_type", None)
        logger.debug("Result set %s analysis_type: %s", result_set_id, analysis_type)

        if analysis_type == "Pushover":
            logger.debug("Result set is Pushover, auto-switching to Pushover context")
            window._switch_context("Pushover")
        else:
            logger.debug("Result set is not Pushover, auto-switching to NLTHA context")
            window._switch_context("NLTHA")
    elif category == "Pushover":
        logger.debug("No result set but category is Pushover, switching to Pushover context")
        window._switch_context("Pushover")
    else:
        logger.debug("Defaulting to NLTHA context")
        window._switch_context("NLTHA")

    window.controller.update_selection(
        result_type=result_type,
        result_set_id=result_set_id,
        direction=direction,
        element_id=element_id,
    )

    # Special handling for pushover curves
    if category == "Pushover" and result_type == "Curves":
        case_name = direction  # Direction field contains the case name
        view_loaders.load_pushover_curve(window, case_name, window.content_area)
        return

    # Special handling for all pushover curves
    if category == "Pushover" and result_type == "AllCurves":
        curve_direction = direction  # Direction field contains X or Y
        view_loaders.load_all_pushover_curves(window, curve_direction, window.content_area)
        return

    if result_type and result_set_id:
        if result_type == "AllQuadRotations":
            window.content_area.show_all_rotations()
            view_loaders.load_all_rotations(window, result_set_id, window.content_area)
        elif result_type == "AllColumnRotations":
            window.content_area.show_all_rotations()
            view_loaders.load_all_column_rotations(window, result_set_id, window.content_area)
        elif result_type == "AllBeamRotations":
            window.content_area.show_all_rotations()
            view_loaders.load_all_beam_rotations(window, result_set_id, window.content_area)
        elif result_type == "BeamRotationsTable":
            window.content_area.show_beam_table()
            view_loaders.load_beam_rotations_table(window, result_set_id, window.content_area)
        elif result_type.startswith("MaxMin") and element_id > 0:
            window.content_area.show_maxmin()
            base_type = window._extract_base_result_type(result_type)
            view_loaders.load_element_maxmin_dataset(
                window,
                element_id,
                result_set_id,
                window.content_area,
                base_type,
            )
        elif result_type.startswith("MaxMin"):
            window.content_area.show_maxmin()
            base_type = window._extract_base_result_type(result_type)
            view_loaders.load_maxmin_dataset(window, result_set_id, window.content_area, base_type)
        elif result_type == "AllSoilPressures":
            window.content_area.show_soil_pressure()
            view_loaders.load_all_soil_pressures(window, result_set_id, window.content_area)
        elif result_type == "SoilPressuresTable":
            window.content_area.show_beam_table()
            view_loaders.load_soil_pressures_table(window, result_set_id, window.content_area)
        elif result_type == "AllVerticalDisplacements":
            window.content_area.show_soil_pressure()
            view_loaders.load_all_vertical_displacements(window, result_set_id, window.content_area)
        elif result_type == "VerticalDisplacementsTable":
            window.content_area.show_beam_table()
            view_loaders.load_vertical_displacements_table(window, result_set_id, window.content_area)
        elif result_type == "TimeSeriesGlobal":
            # Time series animated view with 4 plots
            # Direction is encoded as "direction:load_case_name"
            if ":" in direction:
                actual_direction, load_case_name = direction.split(":", 1)
            else:
                actual_direction = direction
                load_case_name = None
            window.controller.update_selection(load_case_name=load_case_name)
            view_loaders.load_time_series_global(window, actual_direction, load_case_name, window.content_area)
        elif element_id > 0:
            window.content_area.show_standard()
            view_loaders.load_element_dataset(window, element_id, result_type, direction, result_set_id, window.content_area)
        else:
            window.content_area.show_standard()
            view_loaders.load_standard_dataset(window, result_type, direction, result_set_id, window.content_area)
    else:
        window.content_area.content_title.setText("Select a result type")
        window.content_area.show_standard()
        window.standard_view.clear()


def on_comparison_selected(
    window: "ProjectDetailWindow",
    comparison_set_id: int,
    result_type: str,
    direction: str,
) -> None:
    """Handle comparison set selection.

    Args:
        window: ProjectDetailWindow instance
        comparison_set_id: ID of the selected comparison set
        result_type: Result type (e.g., "Drifts", "Forces", "QuadRotations")
        direction: Direction ("X", "Y", or "All" for all rotations view)
    """
    from database.repository import ComparisonSetRepository
    from . import view_loaders

    try:
        comparison_set_repo = ComparisonSetRepository(window.session)
        comparison_set = comparison_set_repo.get_by_id(comparison_set_id)

        if not comparison_set:
            window.statusBar().showMessage("Error: Comparison set not found")
            return

        # Check if this is "All Rotations" view
        if direction == "All" and result_type == "QuadRotations":
            view_loaders.load_comparison_all_rotations(window, comparison_set, window.content_area)
            return

        # Check if this is "All Column Rotations" view
        if direction == "AllColumns" and result_type == "ColumnRotations":
            view_loaders.load_comparison_all_column_rotations(window, comparison_set, window.content_area)
            return

        # Check if this is "All Beam Rotations" view
        if direction == "AllBeams" and result_type == "BeamRotations":
            view_loaders.load_comparison_all_beam_rotations(window, comparison_set, window.content_area)
            return

        # Check if this is "All Joints" view (soil pressures, vertical displacements)
        if direction == "AllJoints" and result_type in ["SoilPressures", "VerticalDisplacements"]:
            view_loaders.load_comparison_joint_scatter(window, comparison_set, result_type, window.content_area)
            return

        # Load comparison dataset
        dataset = window.result_service.get_comparison_dataset(
            result_type=result_type,
            direction=direction,
            result_set_ids=comparison_set.result_set_ids,
            metric="Avg",
        )

        if not dataset:
            window.content_title.setText(f"> Comparison: {result_type} {direction}")
            window.statusBar().showMessage("No comparison data available")
            window.content_area.hide_all()
            return

        # Show comparison view
        window.content_area.show_comparison()

        # Load data into comparison view
        window.comparison_view.set_dataset(dataset)

        # Build readable title with result set names and units
        result_set_names = [series.result_set_name for series in dataset.series if series.has_data]
        result_type_with_unit = format_result_type_with_unit(result_type, direction)

        if len(result_set_names) >= 2:
            comparison_title = f"{result_type_with_unit} - {' vs '.join(result_set_names)} Comparison"
        else:
            comparison_title = f"{result_type_with_unit} Comparison"

        window.content_title.setText(f"> {comparison_title}")

        # Show status with warnings if any
        warning_msg = f" ({len(dataset.warnings)} warnings)" if dataset.warnings else ""
        window.statusBar().showMessage(
            f"Loaded comparison for {len(dataset.series)} result sets{warning_msg}"
        )

    except Exception as exc:
        window.statusBar().showMessage(f"Error loading comparison: {str(exc)}")
        log_exception(exc, "Error loading comparison")


def on_comparison_element_selected(
    window: "ProjectDetailWindow",
    comparison_set_id: int,
    result_type: str,
    element_id: int,
    direction: str,
) -> None:
    """Handle comparison element selection.

    Args:
        window: ProjectDetailWindow instance
        comparison_set_id: ID of the selected comparison set
        result_type: Result type (e.g., "WallShears", "QuadRotations")
        element_id: ID of the element to compare
        direction: Direction (e.g., "V2", "V3") or None
    """
    from database.repository import ComparisonSetRepository, ElementRepository

    try:
        comparison_set_repo = ComparisonSetRepository(window.session)
        comparison_set = comparison_set_repo.get_by_id(comparison_set_id)

        if not comparison_set:
            window.statusBar().showMessage("Error: Comparison set not found")
            return

        element_repo = ElementRepository(window.session)
        element = element_repo.get_by_id(element_id)

        if not element:
            window.statusBar().showMessage("Error: Element not found")
            return

        # Load comparison dataset for this element
        dataset = window.result_service.get_comparison_dataset(
            result_type=result_type,
            direction=direction,
            result_set_ids=comparison_set.result_set_ids,
            metric="Avg",
            element_id=element_id,
        )

        if not dataset:
            window.content_title.setText(f"> Comparison: {element.name} - {result_type}")
            window.statusBar().showMessage("No comparison data available")
            window.content_area.hide_all()
            return

        # Show comparison view
        window.content_area.show_comparison()

        # Load data into comparison view
        window.comparison_view.set_dataset(dataset)

        # Build readable title with result set names and units
        result_set_names = [series.result_set_name for series in dataset.series if series.has_data]
        result_type_with_unit = format_result_type_with_unit(result_type, direction)

        if len(result_set_names) >= 2:
            comparison_title = f"{element.name} - {result_type_with_unit} - {' vs '.join(result_set_names)} Comparison"
        else:
            comparison_title = f"{element.name} - {result_type_with_unit} Comparison"

        window.content_title.setText(f"> {comparison_title}")

        # Show status with warnings if any
        warning_msg = f" ({len(dataset.warnings)} warnings)" if dataset.warnings else ""
        window.statusBar().showMessage(
            f"Loaded comparison for {len(dataset.series)} result sets{warning_msg}"
        )

    except Exception as exc:
        window.statusBar().showMessage(f"Error loading element comparison: {str(exc)}")
        log_exception(exc, "Error loading comparison")
