"""View loader functions for ProjectDetailWindow.

This module contains all the data loading methods that populate the various
view widgets (standard view, comparison view, rotations, soil pressures, etc.).
"""

import logging
from typing import TYPE_CHECKING, Optional, Tuple

import pandas as pd
from PyQt6.QtWidgets import QTableWidgetItem

from config.result_config import RESULT_CONFIGS, format_result_type_with_unit
from gui.controllers.table_builder import (
    apply_headers,
    populate_beam_rotations_table,
    populate_foundation_table,
)

if TYPE_CHECKING:
    from .window import ProjectDetailWindow

logger = logging.getLogger(__name__)


def load_standard_dataset(
    window: "ProjectDetailWindow",
    result_type: str,
    direction: str,
    result_set_id: int,
) -> None:
    """Load and display directional results for the selected type."""
    try:
        dataset, shorthand_mapping = window.view_controller.get_standard_view(
            window.result_service, result_type, direction, result_set_id
        )

        if not dataset:
            window.standard_view.clear()
            window.statusBar().showMessage(
                f"No data available for {result_type} ({direction})"
            )
            return

        window.content_title.setText(f"> {dataset.meta.display_name}")
        window.standard_view.set_dataset(dataset, shorthand_mapping=shorthand_mapping)

        story_count = len(dataset.data.index)
        window.statusBar().showMessage(
            f"Loaded {story_count} stories for {dataset.meta.display_name}"
        )

    except Exception as exc:
        window.standard_view.clear()
        window.statusBar().showMessage(f"Error loading results: {str(exc)}")
        import traceback
        traceback.print_exc()


def load_element_dataset(
    window: "ProjectDetailWindow",
    element_id: int,
    result_type: str,
    direction: str,
    result_set_id: int,
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
            window.standard_view.clear()
            window.statusBar().showMessage("No data available for element results")
            return

        window.content_title.setText(f"> {dataset.meta.display_name}")
        logger.debug("Passing mapping to standard_view: %s", shorthand_mapping is not None)
        window.standard_view.set_dataset(dataset, shorthand_mapping=shorthand_mapping)

        story_count = len(dataset.data.index)
        window.statusBar().showMessage(
            f"Loaded {story_count} stories for {dataset.meta.display_name}"
        )

    except Exception as exc:
        window.standard_view.clear()
        window.statusBar().showMessage(f"Error loading element results: {str(exc)}")
        import traceback
        traceback.print_exc()


def load_joint_dataset(
    window: "ProjectDetailWindow",
    result_type: str,
    result_set_id: int,
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
            window.standard_view.clear()
            window.statusBar().showMessage("No data available for joint results")
            return

        window.content_title.setText(f"> {dataset.meta.display_name}")
        logger.debug("Passing mapping to standard_view: %s", shorthand_mapping is not None)
        window.standard_view.set_dataset(dataset, shorthand_mapping=shorthand_mapping)

        element_count = len(dataset.data.index)
        window.statusBar().showMessage(
            f"Loaded {element_count} foundation elements for {dataset.meta.display_name}"
        )

    except Exception as exc:
        window.standard_view.clear()
        window.statusBar().showMessage(f"Error loading joint results: {str(exc)}")
        import traceback
        traceback.print_exc()


def load_maxmin_dataset(
    window: "ProjectDetailWindow",
    result_set_id: int,
    base_result_type: str = "Drifts",
) -> None:
    """Load and display absolute Max/Min drift results from database."""
    try:
        dataset = window.result_service.get_maxmin_dataset(result_set_id, base_result_type)

        if not dataset or dataset.data.empty:
            window.maxmin_widget.clear_data()
            window.content_title.setText("> Max/Min Results")
            window.statusBar().showMessage("No absolute max/min data available")
            return

        window.maxmin_widget.load_dataset(dataset)
        window.content_title.setText(f"> {dataset.meta.display_name}")

        story_count = len(dataset.data.index)
        window.statusBar().showMessage(
            f"Loaded {dataset.meta.display_name} for {story_count} stories"
        )

    except Exception as exc:
        window.maxmin_widget.clear_data()
        window.statusBar().showMessage(f"Error loading Max/Min results: {str(exc)}")
        import traceback
        traceback.print_exc()


def load_element_maxmin_dataset(
    window: "ProjectDetailWindow",
    element_id: int,
    result_set_id: int,
    base_result_type: str = "WallShears",
) -> None:
    """Load and display element-specific Max/Min results (pier shears)."""
    try:
        dataset = window.result_service.get_element_maxmin_dataset(
            element_id, result_set_id, base_result_type
        )

        if not dataset or dataset.data.empty:
            window.maxmin_widget.clear_data()
            window.content_title.setText("> Element Max/Min Results")
            window.statusBar().showMessage("No element max/min data available")
            return

        window.maxmin_widget.load_dataset(dataset)
        window.content_title.setText(f"> {dataset.meta.display_name}")

        story_count = len(dataset.data.index)
        window.statusBar().showMessage(
            f"Loaded {dataset.meta.display_name} for {story_count} stories"
        )

    except Exception as exc:
        window.maxmin_widget.clear_data()
        window.statusBar().showMessage(f"Error loading element Max/Min results: {str(exc)}")
        import traceback
        traceback.print_exc()


def load_all_rotations(window: "ProjectDetailWindow", result_set_id: int) -> None:
    """Load and display all quad rotations across all elements as scatter plot."""
    try:
        df_max = window.result_service.get_all_quad_rotations_dataset(result_set_id, "Max")
        df_min = window.result_service.get_all_quad_rotations_dataset(result_set_id, "Min")

        if (df_max is None or df_max.empty) and (df_min is None or df_min.empty):
            window.all_rotations_widget.clear_data()
            window.content_title.setText("> All Quad Rotations")
            window.statusBar().showMessage("No quad rotation data available")
            return

        window.all_rotations_widget.set_x_label("Quad Rotation (%)")
        window.all_rotations_widget.load_dataset(df_max, df_min)
        window.content_title.setText("> All Quad Rotations")

        num_points_max = len(df_max) if df_max is not None and not df_max.empty else 0
        num_points_min = len(df_min) if df_min is not None and not df_min.empty else 0
        total_points = num_points_max + num_points_min

        df_ref = df_max if df_max is not None and not df_max.empty else df_min
        num_elements = df_ref["Element"].nunique() if df_ref is not None else 0
        num_stories = df_ref["Story"].nunique() if df_ref is not None else 0

        window.statusBar().showMessage(
            f"Loaded {total_points} rotation data points ({num_points_max} max, {num_points_min} min) "
            f"across {num_elements} elements and {num_stories} stories"
        )

    except Exception as exc:
        window.all_rotations_widget.clear_data()
        window.statusBar().showMessage(f"Error loading all rotations: {str(exc)}")
        import traceback
        traceback.print_exc()


def load_all_column_rotations(window: "ProjectDetailWindow", result_set_id: int) -> None:
    """Load and display all column rotations across all columns as scatter plot."""
    try:
        df_max = window.result_service.get_all_column_rotations_dataset(result_set_id, "Max")
        df_min = window.result_service.get_all_column_rotations_dataset(result_set_id, "Min")

        if (df_max is None or df_max.empty) and (df_min is None or df_min.empty):
            window.all_rotations_widget.clear_data()
            window.content_title.setText("> All Column Rotations")
            window.statusBar().showMessage("No column rotation data available")
            return

        window.all_rotations_widget.set_x_label("Column Rotation (%)")
        window.all_rotations_widget.load_dataset(df_max, df_min)
        window.content_title.setText("> All Column Rotations")

        num_points_max = len(df_max) if df_max is not None and not df_max.empty else 0
        num_points_min = len(df_min) if df_min is not None and not df_min.empty else 0
        total_points = num_points_max + num_points_min

        df_ref = df_max if df_max is not None and not df_max.empty else df_min
        num_elements = df_ref["Element"].nunique() if df_ref is not None else 0
        num_stories = df_ref["Story"].nunique() if df_ref is not None else 0

        window.statusBar().showMessage(
            f"Loaded {total_points} rotation data points ({num_points_max} max, {num_points_min} min) "
            f"across {num_elements} columns and {num_stories} stories"
        )

    except Exception as exc:
        window.all_rotations_widget.clear_data()
        window.statusBar().showMessage(f"Error loading all column rotations: {str(exc)}")
        import traceback
        traceback.print_exc()


def load_all_beam_rotations(window: "ProjectDetailWindow", result_set_id: int) -> None:
    """Load and display all beam rotations across all beams as scatter plot."""
    try:
        df_max = window.result_service.get_all_beam_rotations_dataset(result_set_id, "Max")
        df_min = window.result_service.get_all_beam_rotations_dataset(result_set_id, "Min")

        if (df_max is None or df_max.empty) and (df_min is None or df_min.empty):
            window.all_rotations_widget.clear_data()
            window.content_title.setText("> All Beam Rotations")
            window.statusBar().showMessage("No beam rotation data available")
            return

        window.all_rotations_widget.set_x_label("R3 Plastic Rotation (%)")
        window.all_rotations_widget.load_dataset(df_max, df_min)
        window.content_title.setText("> All Beam Rotations")

        num_points_max = len(df_max) if df_max is not None and not df_max.empty else 0
        num_points_min = len(df_min) if df_min is not None and not df_min.empty else 0
        total_points = num_points_max + num_points_min

        df_ref = df_max if df_max is not None and not df_max.empty else df_min
        num_elements = df_ref["Element"].nunique() if df_ref is not None else 0
        num_stories = df_ref["Story"].nunique() if df_ref is not None else 0

        window.statusBar().showMessage(
            f"Loaded {total_points} rotation data points ({num_points_max} max, {num_points_min} min) "
            f"across {num_elements} beams and {num_stories} stories"
        )

    except Exception as exc:
        window.all_rotations_widget.clear_data()
        window.statusBar().showMessage(f"Error loading all beam rotations: {str(exc)}")
        import traceback
        traceback.print_exc()


def load_comparison_all_rotations(window: "ProjectDetailWindow", comparison_set) -> None:
    """Load and display all quad rotations comparison across multiple result sets."""
    from database.repository import ResultSetRepository

    try:
        window._hide_all_views()
        window.comparison_all_rotations_widget.show()

        datasets = []
        result_set_repo = ResultSetRepository(window.session)

        for result_set_id in comparison_set.result_set_ids:
            result_set = result_set_repo.get_by_id(result_set_id)
            if not result_set:
                continue

            df_max = window.result_service.get_all_quad_rotations_dataset(result_set_id, "Max")
            df_min = window.result_service.get_all_quad_rotations_dataset(result_set_id, "Min")

            if df_max is not None and not df_max.empty and df_min is not None and not df_min.empty:
                df_combined = pd.concat([df_max, df_min], ignore_index=True)
            elif df_max is not None and not df_max.empty:
                df_combined = df_max
            elif df_min is not None and not df_min.empty:
                df_combined = df_min
            else:
                df_combined = None

            if df_combined is not None and not df_combined.empty:
                datasets.append((result_set.name, df_combined))

        if not datasets:
            window.comparison_all_rotations_widget.clear_data()
            window.content_title.setText("> All Rotations Comparison")
            window.statusBar().showMessage("No quad rotation data available for comparison")
            return

        window.comparison_all_rotations_widget.set_x_label("Quad Rotation (%)")
        window.comparison_all_rotations_widget.load_comparison_datasets(datasets)

        result_set_names = [name for name, _ in datasets]
        comparison_title = f"All Quad Rotations - {' vs '.join(result_set_names)} Comparison"
        window.content_title.setText(f"> {comparison_title}")

        total_points = sum(len(df) for _, df in datasets)
        window.statusBar().showMessage(
            f"Loaded {total_points} rotation data points across {len(datasets)} result sets"
        )

    except Exception as exc:
        window.comparison_all_rotations_widget.clear_data()
        window.statusBar().showMessage(f"Error loading comparison all rotations: {str(exc)}")
        import traceback
        traceback.print_exc()


def load_comparison_joint_scatter(
    window: "ProjectDetailWindow",
    comparison_set,
    result_type: str,
) -> None:
    """Load and display joint results comparison scatter plot across multiple result sets."""
    from database.repository import ResultSetRepository
    from processing.result_service.comparison_builder import build_all_joints_comparison
    from config.result_config import RESULT_CONFIGS

    try:
        window._hide_all_views()
        window.comparison_joint_scatter_widget.show()

        result_type_cache = f"{result_type}_Min"
        config = RESULT_CONFIGS.get(result_type_cache)

        if not config:
            window.statusBar().showMessage(f"Unknown result type: {result_type}")
            return

        result_set_repo = ResultSetRepository(window.session)
        datasets = build_all_joints_comparison(
            result_type=result_type_cache,
            result_set_ids=comparison_set.result_set_ids,
            config=config,
            get_dataset_func=lambda rt, rs_id: window.result_service.get_joint_dataset(rt, rs_id),
            result_set_repo=result_set_repo,
        )

        if not datasets:
            window.comparison_joint_scatter_widget.clear_data()
            window.content_title.setText(f"> {result_type} Comparison")
            window.statusBar().showMessage(f"No {result_type} data available for comparison")
            return

        window.comparison_joint_scatter_widget.load_comparison_datasets(datasets, result_type)

        result_set_names = [name for name, _, _ in datasets]
        comparison_title = f"All {result_type} - {' vs '.join(result_set_names)} Comparison"
        window.content_title.setText(f"> {comparison_title}")

        total_points = sum(len(df) * len(lc) for _, df, lc in datasets)
        num_load_cases = len(datasets[0][2]) if datasets else 0
        window.statusBar().showMessage(
            f"Loaded {total_points} data points across {len(datasets)} result sets and {num_load_cases} load cases"
        )

    except Exception as exc:
        window.comparison_joint_scatter_widget.clear_data()
        window.statusBar().showMessage(f"Error loading comparison joint scatter: {str(exc)}")
        import traceback
        traceback.print_exc()


def load_beam_rotations_table(window: "ProjectDetailWindow", result_set_id: int) -> None:
    """Load and display beam rotations table in wide format."""
    try:
        logger.debug(
            "load_beam_rotations_table called with result_set_id=%s, active_context=%s",
            result_set_id,
            window.controller.get_active_context().value,
        )

        df = window.result_service.get_beam_rotations_table_dataset(result_set_id)

        if df is None or df.empty:
            window.beam_rotations_table.clear()
            window.content_title.setText("> Beam Rotations - R3 Plastic")
            window.beam_rotations_table.setRowCount(1)
            window.beam_rotations_table.setColumnCount(1)
            window.beam_rotations_table.setHorizontalHeaderLabels(["Message"])
            message_item = QTableWidgetItem("No beam rotation data available")
            window.beam_rotations_table.setItem(0, 0, message_item)
            window.statusBar().showMessage("No beam rotation data available")
            return

        window.beam_rotations_table.clear()
        window.content_title.setText("> Beam Rotations - R3 Plastic (%)")

        num_rows = len(df)
        num_cols = len(df.columns)
        window.beam_rotations_table.setRowCount(num_rows)
        window.beam_rotations_table.setColumnCount(num_cols)

        column_names = df.columns.tolist()
        display_names = window.view_controller.apply_mapping_to_headers(column_names, result_set_id)
        apply_headers(window.beam_rotations_table, display_names)

        config = RESULT_CONFIGS.get("BeamRotations_R3Plastic")
        color_scheme = config.color_scheme if config else "blue_orange"

        populate_beam_rotations_table(window.beam_rotations_table, df, color_scheme)

        num_beams = df["Frame/Wall"].nunique() if "Frame/Wall" in df.columns else 0
        num_stories = df["Story"].nunique() if "Story" in df.columns else 0

        window.statusBar().showMessage(
            f"Loaded beam rotations table: {num_rows} hinge locations across {num_beams} beams and {num_stories} stories"
        )

    except Exception as exc:
        window.beam_rotations_table.clear()
        window.statusBar().showMessage(f"Error loading beam rotations table: {str(exc)}")
        import traceback
        traceback.print_exc()


def load_all_soil_pressures(window: "ProjectDetailWindow", result_set_id: int) -> None:
    """Load and display all soil pressures as bar chart."""
    try:
        dataset = window.result_service.get_joint_dataset("SoilPressures_Min", result_set_id)

        if not dataset or dataset.data.empty:
            window.soil_pressure_plot_widget.clear_data()
            window.content_title.setText("> Soil Pressures (Min)")
            window.statusBar().showMessage("No soil pressure data available")
            return

        df = dataset.data
        load_cases = dataset.load_case_columns

        window.soil_pressure_plot_widget.load_dataset(df, load_cases)
        window.content_title.setText("> Soil Pressures (Min) - Distribution by Load Case")

        num_elements = len(df)
        num_load_cases = len(load_cases)

        window.statusBar().showMessage(
            f"Loaded soil pressure distribution: {num_elements} foundation elements across {num_load_cases} load cases"
        )

    except Exception as exc:
        window.soil_pressure_plot_widget.clear_data()
        window.statusBar().showMessage(f"Error loading soil pressures: {str(exc)}")
        import traceback
        traceback.print_exc()


def load_soil_pressures_table(window: "ProjectDetailWindow", result_set_id: int) -> None:
    """Load and display soil pressures table in wide format."""
    try:
        logger.debug(
            "load_soil_pressures_table called with result_set_id=%s, active_context=%s",
            result_set_id,
            window.controller.get_active_context().value,
        )

        dataset = window.result_service.get_joint_dataset("SoilPressures_Min", result_set_id)

        if not dataset or dataset.data.empty:
            window.beam_rotations_table.clear()
            window.content_title.setText("> Soil Pressures (Min)")
            window.beam_rotations_table.setRowCount(1)
            window.beam_rotations_table.setColumnCount(1)
            window.beam_rotations_table.setHorizontalHeaderLabels(["Message"])
            message_item = QTableWidgetItem("No soil pressure data available")
            window.beam_rotations_table.setItem(0, 0, message_item)
            window.statusBar().showMessage("No soil pressure data available")
            return

        df = dataset.data

        window.beam_rotations_table.clear()
        window.content_title.setText(f"> {dataset.meta.display_name}")

        num_rows = len(df)
        num_cols = len(df.columns)
        window.beam_rotations_table.setRowCount(num_rows)
        window.beam_rotations_table.setColumnCount(num_cols)

        load_case_cols = list(dataset.load_case_columns)
        column_names = df.columns.tolist()
        display_names = window.view_controller.apply_mapping_to_headers(column_names, result_set_id)
        apply_headers(window.beam_rotations_table, display_names)

        populate_foundation_table(
            table=window.beam_rotations_table,
            df=df,
            load_case_cols=load_case_cols,
            summary_cols=dataset.summary_columns,
            color_scheme=dataset.config.color_scheme,
        )

        num_elements = len(df)
        num_load_cases = len(load_case_cols)

        window.statusBar().showMessage(
            f"Loaded soil pressures table: {num_elements} foundation elements across {num_load_cases} load cases"
        )

    except Exception as exc:
        window.beam_rotations_table.clear()
        window.statusBar().showMessage(f"Error loading soil pressures table: {str(exc)}")
        import traceback
        traceback.print_exc()


def load_all_vertical_displacements(window: "ProjectDetailWindow", result_set_id: int) -> None:
    """Load and display all vertical displacements as scatter plot."""
    try:
        dataset = window.result_service.get_joint_dataset("VerticalDisplacements_Min", result_set_id)

        if not dataset or dataset.data.empty:
            window.soil_pressure_plot_widget.clear_data()
            window.content_title.setText("> Vertical Displacements (Min)")
            window.statusBar().showMessage("No vertical displacement data available")
            return

        df = dataset.data
        load_cases = dataset.load_case_columns

        window.soil_pressure_plot_widget.load_dataset(df, load_cases)
        window.content_title.setText("> Vertical Displacements (Min) - Distribution by Load Case")

        num_joints = len(df)
        num_load_cases = len(load_cases)

        window.statusBar().showMessage(
            f"Loaded vertical displacement distribution: {num_joints} foundation joints across {num_load_cases} load cases"
        )

    except Exception as exc:
        window.soil_pressure_plot_widget.clear_data()
        window.statusBar().showMessage(f"Error loading vertical displacements: {str(exc)}")
        import traceback
        traceback.print_exc()


def load_vertical_displacements_table(window: "ProjectDetailWindow", result_set_id: int) -> None:
    """Load and display vertical displacements table in wide format."""
    try:
        logger.debug(
            "load_vertical_displacements_table called with result_set_id=%s, active_context=%s",
            result_set_id,
            window.controller.get_active_context().value,
        )

        dataset = window.result_service.get_joint_dataset("VerticalDisplacements_Min", result_set_id)

        if not dataset or dataset.data.empty:
            window.beam_rotations_table.clear()
            window.content_title.setText("> Vertical Displacements (Min)")
            window.beam_rotations_table.setRowCount(1)
            window.beam_rotations_table.setColumnCount(1)
            window.beam_rotations_table.setHorizontalHeaderLabels(["Message"])
            message_item = QTableWidgetItem("No vertical displacement data available")
            window.beam_rotations_table.setItem(0, 0, message_item)
            window.statusBar().showMessage("No vertical displacement data available")
            return

        df = dataset.data

        window.beam_rotations_table.clear()
        window.content_title.setText(f"> {dataset.meta.display_name}")

        num_rows = len(df)
        num_cols = len(df.columns)
        window.beam_rotations_table.setRowCount(num_rows)
        window.beam_rotations_table.setColumnCount(num_cols)

        load_case_cols = list(dataset.load_case_columns)
        column_names = df.columns.tolist()
        display_names = window.view_controller.apply_mapping_to_headers(column_names, result_set_id)
        apply_headers(window.beam_rotations_table, display_names)

        populate_foundation_table(
            table=window.beam_rotations_table,
            df=df,
            load_case_cols=load_case_cols,
            summary_cols=dataset.summary_columns,
            color_scheme=dataset.config.color_scheme,
        )

        num_joints = len(df)
        num_load_cases = len(load_case_cols)

        window.statusBar().showMessage(
            f"Loaded vertical displacements table: {num_joints} foundation joints across {num_load_cases} load cases"
        )

    except Exception as exc:
        window.beam_rotations_table.clear()
        window.statusBar().showMessage(f"Error loading vertical displacements table: {str(exc)}")
        import traceback
        traceback.print_exc()


def load_pushover_curve(window: "ProjectDetailWindow", case_name: str) -> None:
    """Load and display a pushover curve."""
    from database.repository import PushoverCaseRepository

    try:
        window._hide_all_views()
        window.pushover_curve_view.show()

        pushover_repo = PushoverCaseRepository(window.session)
        case = pushover_repo.get_by_name(
            window.project_id,
            window.controller.selection.result_set_id,
            case_name,
        )

        if not case:
            window.statusBar().showMessage(f"Pushover case '{case_name}' not found")
            return

        curve_points = pushover_repo.get_curve_data(case.id)

        if not curve_points:
            window.statusBar().showMessage(f"No data points found for '{case_name}'")
            return

        step_numbers = [pt.step_number for pt in curve_points]
        displacements = [pt.displacement for pt in curve_points]
        base_shears = [pt.base_shear for pt in curve_points]

        window.pushover_curve_view.display_curve(
            case_name=case_name,
            step_numbers=step_numbers,
            displacements=displacements,
            base_shears=base_shears,
        )

        window.content_title.setText(f"Pushover Curve: {case_name}")

        window.statusBar().showMessage(
            f"Loaded pushover curve: {case_name} ({len(curve_points)} points)"
        )

    except Exception as e:
        window.statusBar().showMessage(f"Error loading pushover curve: {str(e)}")
        import traceback
        traceback.print_exc()


def load_all_pushover_curves(window: "ProjectDetailWindow", direction: str) -> None:
    """Load and display all pushover curves for a given direction."""
    from database.repository import PushoverCaseRepository

    try:
        window._hide_all_views()
        window.pushover_curve_view.show()

        pushover_repo = PushoverCaseRepository(window.session)
        all_cases = pushover_repo.get_by_result_set(window.controller.selection.result_set_id)

        direction_cases = [c for c in all_cases if c.direction == direction]

        if not direction_cases:
            window.statusBar().showMessage(f"No {direction} direction curves found")
            return

        curves_data = []
        for case in direction_cases:
            curve_points = pushover_repo.get_curve_data(case.id)

            if curve_points:
                curves_data.append({
                    "case_name": case.name,
                    "displacements": [pt.displacement for pt in curve_points],
                    "base_shears": [pt.base_shear for pt in curve_points],
                })

        if not curves_data:
            window.statusBar().showMessage(f"No curve data found for {direction} direction")
            return

        window.pushover_curve_view.display_all_curves(curves_data)

        window.content_title.setText(f"All Pushover Curves - {direction} Direction")

        window.statusBar().showMessage(
            f"Loaded {len(curves_data)} pushover curves for {direction} direction"
        )

    except Exception as e:
        window.statusBar().showMessage(f"Error loading all pushover curves: {str(e)}")
        import traceback
        traceback.print_exc()
