"""Standard and element dataset loaders for ProjectDetailWindow."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from utils.error_handling import log_exception

if TYPE_CHECKING:
    from ..window import ProjectDetailWindow
    from ..content import ContentArea

logger = logging.getLogger(__name__)


def load_standard_dataset(
    window: "ProjectDetailWindow",
    result_type: str,
    direction: str,
    result_set_id: int,
    area: "ContentArea",
) -> None:
    """Load and display directional results for the selected type."""
    try:
        dataset, shorthand_mapping = window.view_controller.get_standard_view(
            window.result_service, result_type, direction, result_set_id
        )

        if not dataset:
            area.standard_view.clear()
            window.statusBar().showMessage(
                f"No data available for {result_type} ({direction})"
            )
            return

        area.content_title.setText(f"> {dataset.meta.display_name}")
        area.standard_view.set_dataset(dataset, shorthand_mapping=shorthand_mapping)

        story_count = len(dataset.data.index)
        window.statusBar().showMessage(
            f"Loaded {story_count} stories for {dataset.meta.display_name}"
        )

    except Exception as exc:
        area.standard_view.clear()
        window.statusBar().showMessage(f"Error loading results: {str(exc)}")
        log_exception(exc, "Error loading results")


def load_element_dataset(
    window: "ProjectDetailWindow",
    element_id: int,
    result_type: str,
    direction: str,
    result_set_id: int,
    area: "ContentArea",
) -> None:
    """Load and display element-specific results (pier shears, etc.)."""
    try:
        logger.debug(
            "load_element_dataset called: element_id=%s, result_type=%s, direction=%s, result_set_id=%s, active_context=%s",
            element_id,
            result_type,
            direction,
            result_set_id,
            window.controller.get_active_context().value,
        )

        dataset, shorthand_mapping = window.view_controller.get_element_view(
            window.result_service, element_id, result_type, direction, result_set_id
        )

        if not dataset:
            area.standard_view.clear()
            window.statusBar().showMessage("No data available for element results")
            return

        area.content_title.setText(f"> {dataset.meta.display_name}")
        logger.debug("Passing mapping to standard_view: %s", shorthand_mapping is not None)
        area.standard_view.set_dataset(dataset, shorthand_mapping=shorthand_mapping)

        story_count = len(dataset.data.index)
        window.statusBar().showMessage(
            f"Loaded {story_count} stories for {dataset.meta.display_name}"
        )

    except Exception as exc:
        area.standard_view.clear()
        window.statusBar().showMessage(f"Error loading element results: {str(exc)}")
        log_exception(exc, "Error loading element results")


def load_joint_dataset(
    window: "ProjectDetailWindow",
    result_type: str,
    result_set_id: int,
    area: "ContentArea",
) -> None:
    """Load and display joint-level results (soil pressures, etc.)."""
    try:
        logger.debug(
            "load_joint_dataset called: result_type=%s, result_set_id=%s, active_context=%s",
            result_type,
            result_set_id,
            window.controller.get_active_context().value,
        )

        dataset, shorthand_mapping = window.view_controller.get_joint_view(
            window.result_service, result_type, result_set_id
        )

        if not dataset:
            area.standard_view.clear()
            window.statusBar().showMessage("No data available for joint results")
            return

        area.content_title.setText(f"> {dataset.meta.display_name}")
        logger.debug("Passing mapping to standard_view: %s", shorthand_mapping is not None)
        area.standard_view.set_dataset(dataset, shorthand_mapping=shorthand_mapping)

        element_count = len(dataset.data.index)
        window.statusBar().showMessage(
            f"Loaded {element_count} foundation elements for {dataset.meta.display_name}"
        )

    except Exception as exc:
        area.standard_view.clear()
        window.statusBar().showMessage(f"Error loading joint results: {str(exc)}")
        log_exception(exc, "Error loading data")


def load_maxmin_dataset(
    window: "ProjectDetailWindow",
    result_set_id: int,
    area: "ContentArea",
    base_result_type: str = "Drifts",
) -> None:
    """Load and display absolute Max/Min drift results from database."""
    try:
        dataset = window.result_service.get_maxmin_dataset(result_set_id, base_result_type)

        if not dataset or dataset.data.empty:
            area.maxmin_widget.clear_data()
            area.content_title.setText("> Max/Min Results")
            window.statusBar().showMessage("No absolute max/min data available")
            return

        area.maxmin_widget.load_dataset(dataset)
        area.content_title.setText(f"> {dataset.meta.display_name}")

        story_count = len(dataset.data.index)
        window.statusBar().showMessage(
            f"Loaded {dataset.meta.display_name} for {story_count} stories"
        )

    except Exception as exc:
        area.maxmin_widget.clear_data()
        window.statusBar().showMessage(f"Error loading Max/Min results: {str(exc)}")
        log_exception(exc, "Error loading data")


def load_element_maxmin_dataset(
    window: "ProjectDetailWindow",
    element_id: int,
    result_set_id: int,
    area: "ContentArea",
    base_result_type: str = "WallShears",
) -> None:
    """Load and display element-specific Max/Min results (pier shears)."""
    try:
        dataset = window.result_service.get_element_maxmin_dataset(
            element_id, result_set_id, base_result_type
        )

        if not dataset or dataset.data.empty:
            area.maxmin_widget.clear_data()
            area.content_title.setText("> Element Max/Min Results")
            window.statusBar().showMessage("No element max/min data available")
            return

        area.maxmin_widget.load_dataset(dataset)
        area.content_title.setText(f"> {dataset.meta.display_name}")

        story_count = len(dataset.data.index)
        window.statusBar().showMessage(
            f"Loaded {dataset.meta.display_name} for {story_count} stories"
        )

    except Exception as exc:
        area.maxmin_widget.clear_data()
        window.statusBar().showMessage(f"Error loading element Max/Min results: {str(exc)}")
        log_exception(exc, "Error loading data")
