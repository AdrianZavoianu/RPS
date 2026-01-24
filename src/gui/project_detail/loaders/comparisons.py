"""Comparison view loaders for ProjectDetailWindow."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

from utils.error_handling import log_exception
from .common import _is_pushover_context

if TYPE_CHECKING:
    from ..window import ProjectDetailWindow
    from ..content import ContentArea

def _get_data_service(window: "ProjectDetailWindow"):
    data_service = getattr(window, "data_service", None)
    if data_service is None:
        from services.data_access import DataAccessService

        data_service = DataAccessService(window.context.session)
    return data_service


def load_comparison_all_rotations(window: "ProjectDetailWindow", comparison_set, area: "ContentArea") -> None:
    """Load and display all quad rotations comparison across multiple result sets."""
    try:
        area.show_comparison_rotations()
        datasets = []
        data_service = _get_data_service(window)

        for result_set_id in comparison_set.result_set_ids:
            result_set = data_service.get_result_set_by_id(result_set_id)
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
            area.comparison_all_rotations_widget.clear_data()
            area.content_title.setText("> All Rotations Comparison")
            window.statusBar().showMessage("No quad rotation data available for comparison")
            return

        area.comparison_all_rotations_widget.set_x_label("Quad Rotation (%)")
        area.comparison_all_rotations_widget.load_comparison_datasets(datasets)

        result_set_names = [name for name, _ in datasets]
        comparison_title = f"All Quad Rotations - {' vs '.join(result_set_names)} Comparison"
        area.content_title.setText(f"> {comparison_title}")

        total_points = sum(len(df) for _, df in datasets)
        window.statusBar().showMessage(
            f"Loaded {total_points} rotation data points across {len(datasets)} result sets"
        )

    except Exception as exc:
        area.comparison_all_rotations_widget.clear_data()
        window.statusBar().showMessage(f"Error loading comparison all rotations: {str(exc)}")
        log_exception(exc, "Error loading data")


def load_comparison_all_column_rotations(window: "ProjectDetailWindow", comparison_set, area: "ContentArea") -> None:
    """Load and display all column rotations comparison across multiple result sets."""
    try:
        area.show_comparison_rotations()
        datasets = []
        data_service = _get_data_service(window)

        for result_set_id in comparison_set.result_set_ids:
            result_set = data_service.get_result_set_by_id(result_set_id)
            if not result_set:
                continue

            df_max = window.result_service.get_all_column_rotations_dataset(result_set_id, "Max")
            df_min = window.result_service.get_all_column_rotations_dataset(result_set_id, "Min")

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
            area.comparison_all_rotations_widget.clear_data()
            area.content_title.setText("> All Column Rotations Comparison")
            window.statusBar().showMessage("No column rotation data available for comparison")
            return

        area.comparison_all_rotations_widget.set_x_label("Column Rotation (%)")
        area.comparison_all_rotations_widget.load_comparison_datasets(datasets)

        result_set_names = [name for name, _ in datasets]
        comparison_title = f"All Column Rotations - {' vs '.join(result_set_names)} Comparison"
        area.content_title.setText(f"> {comparison_title}")

        total_points = sum(len(df) for _, df in datasets)
        window.statusBar().showMessage(
            f"Loaded {total_points} column rotation data points across {len(datasets)} result sets"
        )

    except Exception as exc:
        area.comparison_all_rotations_widget.clear_data()
        window.statusBar().showMessage(f"Error loading comparison column rotations: {str(exc)}")
        log_exception(exc, "Error loading data")


def load_comparison_all_beam_rotations(window: "ProjectDetailWindow", comparison_set, area: "ContentArea") -> None:
    """Load and display all beam rotations comparison across multiple result sets."""
    try:
        area.show_comparison_rotations()
        datasets = []
        data_service = _get_data_service(window)

        for result_set_id in comparison_set.result_set_ids:
            result_set = data_service.get_result_set_by_id(result_set_id)
            if not result_set:
                continue

            df_max = window.result_service.get_all_beam_rotations_dataset(result_set_id, "Max")
            df_min = window.result_service.get_all_beam_rotations_dataset(result_set_id, "Min")

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
            area.comparison_all_rotations_widget.clear_data()
            area.content_title.setText("> All Beam Rotations Comparison")
            window.statusBar().showMessage("No beam rotation data available for comparison")
            return

        area.comparison_all_rotations_widget.set_x_label("R3 Plastic Rotation (%)")
        area.comparison_all_rotations_widget.load_comparison_datasets(datasets)

        result_set_names = [name for name, _ in datasets]
        comparison_title = f"All Beam Rotations - {' vs '.join(result_set_names)} Comparison"
        area.content_title.setText(f"> {comparison_title}")

        total_points = sum(len(df) for _, df in datasets)
        window.statusBar().showMessage(
            f"Loaded {total_points} beam rotation data points across {len(datasets)} result sets"
        )

    except Exception as exc:
        area.comparison_all_rotations_widget.clear_data()
        window.statusBar().showMessage(f"Error loading comparison beam rotations: {str(exc)}")
        log_exception(exc, "Error loading data")


def load_comparison_joint_scatter(
    window: "ProjectDetailWindow",
    comparison_set,
    result_type: str,
    area: "ContentArea",
) -> None:
    """Load and display joint results comparison scatter plot across multiple result sets."""
    from services.result_service.comparison_builder import build_all_joints_comparison
    from config.result_config import RESULT_CONFIGS

    try:
        result_type_cache = f"{result_type}_Min"
        config = RESULT_CONFIGS.get(result_type_cache)

        if not config:
            window.statusBar().showMessage(f"Unknown result type: {result_type}")
            return

        area.show_comparison_scatter()

        data_service = _get_data_service(window)

        class _ResultSetLookup:
            def __init__(self, service):
                self._service = service

            def get_by_id(self, result_set_id):
                return self._service.get_result_set_by_id(result_set_id)

        result_set_repo = _ResultSetLookup(data_service)
        datasets = build_all_joints_comparison(
            result_type=result_type_cache,
            result_set_ids=comparison_set.result_set_ids,
            config=config,
            get_dataset_func=lambda rt, rs_id: window.result_service.get_joint_dataset(
                rt, rs_id, is_pushover=_is_pushover_context(window)
            ),
            result_set_repo=result_set_repo,
        )

        if not datasets:
            area.comparison_joint_scatter_widget.clear_data()
            area.content_title.setText(f"> {result_type} Comparison")
            window.statusBar().showMessage(f"No {result_type} data available for comparison")
            return

        area.comparison_joint_scatter_widget.load_comparison_datasets(datasets, result_type)

        result_set_names = [name for name, _, _ in datasets]
        comparison_title = f"All {result_type} - {' vs '.join(result_set_names)} Comparison"
        area.content_title.setText(f"> {comparison_title}")

        total_points = sum(len(df) * len(lc) for _, df, lc in datasets)
        num_load_cases = len(datasets[0][2]) if datasets else 0
        window.statusBar().showMessage(
            f"Loaded {total_points} data points across {len(datasets)} result sets and {num_load_cases} load cases"
        )

    except Exception as exc:
        area.comparison_joint_scatter_widget.clear_data()
        window.statusBar().showMessage(f"Error loading comparison joint scatter: {str(exc)}")
        log_exception(exc, "Error loading data")
