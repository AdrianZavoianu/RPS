"""Rotation-related view loaders for ProjectDetailWindow."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from config.analysis_types import AnalysisType
from PyQt6.QtWidgets import QTableWidgetItem

from config.result_config import RESULT_CONFIGS
from gui.controllers.table_builder import (
    apply_headers,
    populate_beam_rotations_table,
    populate_foundation_table,
)
from utils.error_handling import log_exception

if TYPE_CHECKING:
    from ..window import ProjectDetailWindow
    from ..content import ContentArea

logger = logging.getLogger(__name__)


def _show_rotation_averages(window: "ProjectDetailWindow") -> bool:
    """Pushover all-rotation plots show raw points only."""
    return window.controller.get_active_context() != AnalysisType.PUSHOVER


def load_all_rotations(
    window: "ProjectDetailWindow", result_set_id: int, area: "ContentArea"
) -> None:
    """Load and display all quad rotations across all elements as scatter plot."""
    try:
        df_max = window.result_service.get_all_quad_rotations_dataset(result_set_id, "Max")
        df_min = window.result_service.get_all_quad_rotations_dataset(result_set_id, "Min")

        if (df_max is None or df_max.empty) and (df_min is None or df_min.empty):
            area.all_rotations_widget.clear_data()
            area.content_title.setText("> All Quad Rotations")
            window.statusBar().showMessage("No quad rotation data available")
            return

        area.all_rotations_widget.set_x_label("Quad Rotation (%)")
        area.all_rotations_widget.load_dataset(
            df_max, df_min, show_averages=_show_rotation_averages(window)
        )
        area.content_title.setText("> All Quad Rotations")

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
        area.all_rotations_widget.clear_data()
        window.statusBar().showMessage(f"Error loading all rotations: {str(exc)}")
        log_exception(exc, "Error loading data")


def load_all_column_rotations(
    window: "ProjectDetailWindow", result_set_id: int, area: "ContentArea"
) -> None:
    """Load and display all column rotations across all columns as scatter plot."""
    try:
        df_max = window.result_service.get_all_column_rotations_dataset(result_set_id, "Max")
        df_min = window.result_service.get_all_column_rotations_dataset(result_set_id, "Min")

        if (df_max is None or df_max.empty) and (df_min is None or df_min.empty):
            area.all_rotations_widget.clear_data()
            area.content_title.setText("> All Column Rotations")
            window.statusBar().showMessage("No column rotation data available")
            return

        area.all_rotations_widget.set_x_label("Column Rotation (%)")
        area.all_rotations_widget.load_dataset(
            df_max, df_min, show_averages=_show_rotation_averages(window)
        )
        area.content_title.setText("> All Column Rotations")

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
        area.all_rotations_widget.clear_data()
        window.statusBar().showMessage(f"Error loading all column rotations: {str(exc)}")
        log_exception(exc, "Error loading data")


def load_all_beam_rotations(
    window: "ProjectDetailWindow", result_set_id: int, area: "ContentArea"
) -> None:
    """Load and display all beam rotations across all beams as scatter plot."""
    try:
        df_max = window.result_service.get_all_beam_rotations_dataset(result_set_id, "Max")
        df_min = window.result_service.get_all_beam_rotations_dataset(result_set_id, "Min")

        if (df_max is None or df_max.empty) and (df_min is None or df_min.empty):
            area.all_rotations_widget.clear_data()
            area.content_title.setText("> All Beam Rotations")
            window.statusBar().showMessage("No beam rotation data available")
            return

        area.all_rotations_widget.set_x_label("R3 Plastic Rotation (%)")
        area.all_rotations_widget.load_dataset(
            df_max, df_min, show_averages=_show_rotation_averages(window)
        )
        area.content_title.setText("> All Beam Rotations")

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
        area.all_rotations_widget.clear_data()
        window.statusBar().showMessage(f"Error loading all beam rotations: {str(exc)}")
        log_exception(exc, "Error loading data")


def load_all_brace_axials(
    window: "ProjectDetailWindow", result_set_id: int, area: "ContentArea"
) -> None:
    """Load and display all brace axial force points across all braces."""
    try:
        df_max = window.result_service.get_all_brace_axials_dataset(result_set_id, "Max")
        df_min = window.result_service.get_all_brace_axials_dataset(result_set_id, "Min")

        if (df_max is None or df_max.empty) and (df_min is None or df_min.empty):
            area.all_rotations_widget.clear_data()
            area.content_title.setText("> All Brace Axial Forces")
            window.statusBar().showMessage("No brace axial data available")
            return

        area.all_rotations_widget.set_x_label("Brace Axial Force (kN)")
        area.all_rotations_widget.load_dataset(
            df_max, df_min, show_averages=_show_rotation_averages(window)
        )
        area.content_title.setText("> All Brace Axial Forces")

        num_points_max = len(df_max) if df_max is not None and not df_max.empty else 0
        num_points_min = len(df_min) if df_min is not None and not df_min.empty else 0
        total_points = num_points_max + num_points_min

        df_ref = df_max if df_max is not None and not df_max.empty else df_min
        num_elements = df_ref["Element"].nunique() if df_ref is not None else 0
        num_stories = df_ref["Story"].nunique() if df_ref is not None else 0

        window.statusBar().showMessage(
            f"Loaded {total_points} axial force points ({num_points_max} max, {num_points_min} min) "
            f"across {num_elements} braces and {num_stories} stories"
        )

    except Exception as exc:
        area.all_rotations_widget.clear_data()
        window.statusBar().showMessage(f"Error loading all brace axials: {str(exc)}")
        log_exception(exc, "Error loading data")


def load_beam_rotations_table(
    window: "ProjectDetailWindow", result_set_id: int, area: "ContentArea"
) -> None:
    """Load and display beam rotations table in wide format."""
    try:
        logger.debug(
            "load_beam_rotations_table called with result_set_id=%s, active_context=%s",
            result_set_id,
            window.controller.get_active_context().value,
        )

        df = window.result_service.get_beam_rotations_table_dataset(result_set_id)

        if df is None or df.empty:
            area.beam_rotations_table.clear()
            area.content_title.setText("> Beam Rotations - R3 Plastic")
            area.beam_rotations_table.setRowCount(1)
            area.beam_rotations_table.setColumnCount(1)
            area.beam_rotations_table.setHorizontalHeaderLabels(["Message"])
            message_item = QTableWidgetItem("No beam rotation data available")
            area.beam_rotations_table.setItem(0, 0, message_item)
            window.statusBar().showMessage("No beam rotation data available")
            return

        area.beam_rotations_table.clear()
        area.content_title.setText("> Beam Rotations - R3 Plastic (%)")

        num_rows = len(df)
        num_cols = len(df.columns)
        area.beam_rotations_table.setRowCount(num_rows)
        area.beam_rotations_table.setColumnCount(num_cols)

        column_names = df.columns.tolist()
        display_names = window.view_controller.apply_mapping_to_headers(column_names, result_set_id)
        apply_headers(area.beam_rotations_table, display_names)

        config = RESULT_CONFIGS.get("BeamRotations_R3Plastic")
        color_scheme = config.color_scheme if config else "blue_orange"

        populate_beam_rotations_table(area.beam_rotations_table, df, color_scheme)

        num_beams = df["Frame/Wall"].nunique() if "Frame/Wall" in df.columns else 0
        num_stories = df["Story"].nunique() if "Story" in df.columns else 0

        window.statusBar().showMessage(
            f"Loaded beam rotations table: {num_rows} hinge locations across {num_beams} beams and {num_stories} stories"
        )

    except Exception as exc:
        area.beam_rotations_table.clear()
        window.statusBar().showMessage(f"Error loading beam rotations table: {str(exc)}")
        log_exception(exc, "Error loading data")


def load_brace_axials_table(
    window: "ProjectDetailWindow", result_set_id: int, area: "ContentArea"
) -> None:
    """Load and display brace axial envelopes in wide table format."""
    try:
        df = window.result_service.get_brace_axials_table_dataset(result_set_id)

        if df is None or df.empty:
            area.beam_rotations_table.clear()
            area.content_title.setText("> Brace Axial Forces")
            area.beam_rotations_table.setRowCount(1)
            area.beam_rotations_table.setColumnCount(1)
            area.beam_rotations_table.setHorizontalHeaderLabels(["Message"])
            message_item = QTableWidgetItem("No brace axial data available")
            area.beam_rotations_table.setItem(0, 0, message_item)
            window.statusBar().showMessage("No brace axial data available")
            return

        area.beam_rotations_table.clear()
        area.content_title.setText("> Brace Axial Forces (kN)")

        column_names = df.columns.tolist()
        display_names = window.view_controller.apply_mapping_to_headers(column_names, result_set_id)
        apply_headers(area.beam_rotations_table, display_names)

        fixed_cols = {"Story", "Brace"}
        summary_cols = [col for col in ["Avg", "Max", "Min"] if col in df.columns]
        load_case_cols = [
            col for col in df.columns if col not in fixed_cols and col not in summary_cols
        ]

        config = RESULT_CONFIGS.get("BraceAxials")
        color_scheme = config.color_scheme if config else "blue_orange"
        populate_foundation_table(
            area.beam_rotations_table,
            df,
            load_case_cols,
            summary_cols,
            color_scheme,
        )

        num_braces = df["Brace"].nunique() if "Brace" in df.columns else 0
        num_stories = df["Story"].nunique() if "Story" in df.columns else 0
        window.statusBar().showMessage(
            f"Loaded brace axial table: {len(df)} rows across {num_braces} braces and {num_stories} stories"
        )

    except Exception as exc:
        area.beam_rotations_table.clear()
        window.statusBar().showMessage(f"Error loading brace axial table: {str(exc)}")
        log_exception(exc, "Error loading data")
