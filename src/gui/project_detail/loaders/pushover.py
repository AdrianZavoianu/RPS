"""Pushover curve view loaders."""

from __future__ import annotations

from typing import TYPE_CHECKING

from utils.error_handling import log_exception

if TYPE_CHECKING:
    from ..window import ProjectDetailWindow
    from ..content import ContentArea


def _get_data_service(window: "ProjectDetailWindow"):
    data_service = getattr(window, "data_service", None)
    if data_service is None:
        from services.data_access import DataAccessService

        data_service = DataAccessService(window.context.session)
    return data_service


def load_pushover_curve(window: "ProjectDetailWindow", case_name: str, area: "ContentArea") -> None:
    """Load and display a pushover curve."""
    try:
        # Hide other views and show the pushover curve area
        area.show_pushover_curve()

        data_service = _get_data_service(window)

        case = data_service.get_pushover_case_by_name(
            window.project_id,
            window.controller.selection.result_set_id,
            case_name,
        )

        if not case:
            window.statusBar().showMessage(f"Pushover case '{case_name}' not found")
            return

        curve_points = data_service.get_pushover_curve_data(case.id)

        if not curve_points:
            window.statusBar().showMessage(f"No data points found for '{case_name}'")
            return

        step_numbers = [pt.step_number for pt in curve_points]
        displacements = [pt.displacement for pt in curve_points]
        base_shears = [pt.base_shear for pt in curve_points]

        area.pushover_curve_view.display_curve(
            case_name=case_name,
            step_numbers=step_numbers,
            displacements=displacements,
            base_shears=base_shears,
        )

        area.content_title.setText(f"Pushover Curve: {case_name}")

        window.statusBar().showMessage(
            f"Loaded pushover curve: {case_name} ({len(curve_points)} points)"
        )

    except Exception as exc:
        window.statusBar().showMessage(f"Error loading pushover curve: {str(exc)}")
        log_exception(exc, "Error loading data")


def load_all_pushover_curves(window: "ProjectDetailWindow", direction: str, area: "ContentArea") -> None:
    """Load and display all pushover curves for a given direction."""
    try:
        # Hide other views and show the pushover curve area
        area.show_pushover_curve()

        data_service = _get_data_service(window)

        all_cases = data_service.get_pushover_cases(window.controller.selection.result_set_id)

        direction_cases = [c for c in all_cases if c.direction == direction]

        if not direction_cases:
            window.statusBar().showMessage(f"No {direction} direction curves found")
            return

        curves_data = []
        for case in direction_cases:
            curve_points = data_service.get_pushover_curve_data(case.id)

            if curve_points:
                curves_data.append({
                    "case_name": case.name,
                    "displacements": [pt.displacement for pt in curve_points],
                    "base_shears": [pt.base_shear for pt in curve_points],
                })

        if not curves_data:
            window.statusBar().showMessage(f"No curve data found for {direction} direction")
            return

        area.pushover_curve_view.display_all_curves(curves_data)

        area.content_title.setText(f"All Pushover Curves - {direction} Direction")

        window.statusBar().showMessage(
            f"Loaded {len(curves_data)} pushover curves for {direction} direction"
        )

    except Exception as exc:
        window.statusBar().showMessage(f"Error loading all pushover curves: {str(exc)}")
        log_exception(exc, "Error loading data")
