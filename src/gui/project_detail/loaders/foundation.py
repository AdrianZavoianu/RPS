"""Foundation (soil pressure / vertical displacement) view loaders."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QTableWidgetItem

from gui.controllers.table_builder import apply_headers, populate_foundation_table
from utils.error_handling import log_exception
from .common import _is_pushover_context

if TYPE_CHECKING:
    from ..window import ProjectDetailWindow
    from ..content import ContentArea

logger = logging.getLogger(__name__)


def load_all_soil_pressures(window: "ProjectDetailWindow", result_set_id: int, area: "ContentArea") -> None:
    """Load and display all soil pressures as bar chart."""
    try:
        dataset = window.result_service.get_joint_dataset(
            "SoilPressures_Min",
            result_set_id,
            is_pushover=_is_pushover_context(window),
        )

        if not dataset or dataset.data.empty:
            area.soil_pressure_plot_widget.clear_data()
            area.content_title.setText("> Soil Pressures (Min)")
            window.statusBar().showMessage("No soil pressure data available")
            return

        df = dataset.data
        load_cases = dataset.load_case_columns

        area.soil_pressure_plot_widget.load_dataset(df, load_cases)
        area.content_title.setText("> Soil Pressures (Min) - Distribution by Load Case")

        num_elements = len(df)
        num_load_cases = len(load_cases)

        window.statusBar().showMessage(
            f"Loaded soil pressure distribution: {num_elements} foundation elements across {num_load_cases} load cases"
        )

    except Exception as exc:
        area.soil_pressure_plot_widget.clear_data()
        window.statusBar().showMessage(f"Error loading soil pressures: {str(exc)}")
        log_exception(exc, "Error loading data")


def load_soil_pressures_table(window: "ProjectDetailWindow", result_set_id: int, area: "ContentArea") -> None:
    """Load and display soil pressures table in wide format."""
    try:
        logger.debug(
            "load_soil_pressures_table called with result_set_id=%s, active_context=%s",
            result_set_id,
            window.controller.get_active_context().value,
        )

        dataset = window.result_service.get_joint_dataset(
            "SoilPressures_Min",
            result_set_id,
            is_pushover=_is_pushover_context(window),
        )

        if not dataset or dataset.data.empty:
            area.beam_rotations_table.clear()
            area.content_title.setText("> Soil Pressures (Min)")
            area.beam_rotations_table.setRowCount(1)
            area.beam_rotations_table.setColumnCount(1)
            area.beam_rotations_table.setHorizontalHeaderLabels(["Message"])
            message_item = QTableWidgetItem("No soil pressure data available")
            area.beam_rotations_table.setItem(0, 0, message_item)
            window.statusBar().showMessage("No soil pressure data available")
            return

        df = dataset.data

        area.beam_rotations_table.clear()
        area.content_title.setText(f"> {dataset.meta.display_name}")

        num_rows = len(df)
        num_cols = len(df.columns)
        area.beam_rotations_table.setRowCount(num_rows)
        area.beam_rotations_table.setColumnCount(num_cols)

        load_case_cols = list(dataset.load_case_columns)
        column_names = df.columns.tolist()
        display_names = window.view_controller.apply_mapping_to_headers(column_names, result_set_id)
        apply_headers(area.beam_rotations_table, display_names)

        populate_foundation_table(
            table=area.beam_rotations_table,
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
        area.beam_rotations_table.clear()
        window.statusBar().showMessage(f"Error loading soil pressures table: {str(exc)}")
        log_exception(exc, "Error loading data")


def load_all_vertical_displacements(window: "ProjectDetailWindow", result_set_id: int, area: "ContentArea") -> None:
    """Load and display all vertical displacements as scatter plot."""
    try:
        dataset = window.result_service.get_joint_dataset(
            "VerticalDisplacements_Min",
            result_set_id,
            is_pushover=_is_pushover_context(window),
        )

        if not dataset or dataset.data.empty:
            area.soil_pressure_plot_widget.clear_data()
            area.content_title.setText("> Vertical Displacements (Min)")
            window.statusBar().showMessage("No vertical displacement data available")
            return

        df = dataset.data
        load_cases = dataset.load_case_columns

        area.soil_pressure_plot_widget.load_dataset(df, load_cases, result_type="VerticalDisplacements")
        area.content_title.setText("> Vertical Displacements (Min) - Distribution by Load Case")

        num_joints = len(df)
        num_load_cases = len(load_cases)

        window.statusBar().showMessage(
            f"Loaded vertical displacement distribution: {num_joints} foundation joints across {num_load_cases} load cases"
        )

    except Exception as exc:
        area.soil_pressure_plot_widget.clear_data()
        window.statusBar().showMessage(f"Error loading vertical displacements: {str(exc)}")
        log_exception(exc, "Error loading data")


def load_vertical_displacements_table(window: "ProjectDetailWindow", result_set_id: int, area: "ContentArea") -> None:
    """Load and display vertical displacements table in wide format."""
    try:
        logger.debug(
            "load_vertical_displacements_table called with result_set_id=%s, active_context=%s",
            result_set_id,
            window.controller.get_active_context().value,
        )

        dataset = window.result_service.get_joint_dataset(
            "VerticalDisplacements_Min",
            result_set_id,
            is_pushover=_is_pushover_context(window),
        )

        if not dataset or dataset.data.empty:
            area.beam_rotations_table.clear()
            area.content_title.setText("> Vertical Displacements (Min)")
            area.beam_rotations_table.setRowCount(1)
            area.beam_rotations_table.setColumnCount(1)
            area.beam_rotations_table.setHorizontalHeaderLabels(["Message"])
            message_item = QTableWidgetItem("No vertical displacement data available")
            area.beam_rotations_table.setItem(0, 0, message_item)
            window.statusBar().showMessage("No vertical displacement data available")
            return

        df = dataset.data

        area.beam_rotations_table.clear()
        area.content_title.setText(f"> {dataset.meta.display_name}")

        num_rows = len(df)
        num_cols = len(df.columns)
        area.beam_rotations_table.setRowCount(num_rows)
        area.beam_rotations_table.setColumnCount(num_cols)

        load_case_cols = list(dataset.load_case_columns)
        column_names = df.columns.tolist()
        display_names = window.view_controller.apply_mapping_to_headers(column_names, result_set_id)
        apply_headers(area.beam_rotations_table, display_names)

        populate_foundation_table(
            table=area.beam_rotations_table,
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
        area.beam_rotations_table.clear()
        window.statusBar().showMessage(f"Error loading vertical displacements table: {str(exc)}")
        log_exception(exc, "Error loading data")
