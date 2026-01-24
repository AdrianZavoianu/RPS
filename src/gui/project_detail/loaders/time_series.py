"""Time series view loaders."""

from __future__ import annotations

from typing import TYPE_CHECKING

from utils.error_handling import log_exception

if TYPE_CHECKING:
    from ..window import ProjectDetailWindow
    from ..content import ContentArea


def load_time_series_global(
    window: "ProjectDetailWindow",
    direction: str,
    load_case_name: str,
    area: "ContentArea",
) -> None:
    """Load and display animated time series global results (4 plots).

    Args:
        window: The project detail window
        direction: 'X' or 'Y'
        load_case_name: Name of the load case to display (e.g., 'TH02')
        area: Content area to display in
    """
    import numpy as np
    from gui.result_views.time_series_animated_view import TimeSeriesPlotData

    try:
        # Show the time series view
        area.show_time_series()

        result_set_id = window.controller.selection.result_set_id
        data_service = getattr(window, "data_service", None)
        if data_service is None:
            from services.data_access import DataAccessService

            data_service = DataAccessService(window.context.session)

        # Use specified load case or fall back to first available
        if not load_case_name:
            load_cases_map = data_service.get_time_series_load_cases(
                window.project_id,
                [result_set_id],
            )
            load_cases = load_cases_map.get(result_set_id, [])
            if not load_cases:
                area.content_title.setText(f"No Time Series Data for {direction} Direction")
                window.statusBar().showMessage("No time series data available for this result set")
                return
            load_case_name = load_cases[0]

        current_load_case = load_case_name

        # Get story lookup for names
        stories = data_service.get_stories(window.project_id)
        story_lookup = {s.id: s.name for s in stories}

        # Helper function to build TimeSeriesPlotData from cache entries
        def build_plot_data(result_type: str, unit: str) -> TimeSeriesPlotData | None:
            entries = data_service.get_time_series_entries(
                window.project_id,
                result_set_id,
                current_load_case,
                result_type,
                direction,
            )

            if not entries:
                return None

            story_names = []
            values_list = []
            time_steps = None

            for entry in entries:
                story_name = story_lookup.get(entry.story_id, f"Story {entry.story_id}")
                story_names.append(story_name)

                if time_steps is None:
                    time_steps = entry.time_steps

                values_list.append(entry.values)

            if not values_list:
                return None

            # Ensure all value arrays have the same length (pad if needed)
            max_len = max(len(v) for v in values_list)
            normalized_values = []
            for v in values_list:
                if len(v) < max_len:
                    # Pad with the last value to maintain continuity
                    padded = list(v) + [v[-1]] * (max_len - len(v))
                    normalized_values.append(padded)
                else:
                    normalized_values.append(v)

            # Also ensure time_steps matches the normalized length
            if time_steps and len(time_steps) < max_len:
                # Extrapolate time steps
                dt = time_steps[-1] - time_steps[-2] if len(time_steps) > 1 else 0.01
                extended_time = list(time_steps)
                for _ in range(max_len - len(time_steps)):
                    extended_time.append(extended_time[-1] + dt)
                time_steps = extended_time

            # Convert to numpy matrix (num_stories x num_time_steps)
            values_matrix = np.array(normalized_values)

            return TimeSeriesPlotData(
                result_type=result_type,
                direction=direction,
                stories=story_names,
                time_steps=time_steps,
                values_matrix=values_matrix,
                unit=unit,
            )

        # Build data for each result type
        displacements = build_plot_data("Displacements", "mm")
        drifts = build_plot_data("Drifts", "%")
        accelerations = build_plot_data("Accelerations", "g")
        forces = build_plot_data("Forces", "kN")

        # Convert accelerations from mm/s² to g (1g = 9810 mm/s²)
        if accelerations is not None:
            accelerations.values_matrix = accelerations.values_matrix / 9810.0

        # Set data on the animated view
        area.time_series_view.set_data(
            direction=direction,
            displacements=displacements,
            drifts=drifts,
            accelerations=accelerations,
            forces=forces,
        )

        area.content_title.setText(
            f"Time-Series Global Results - {direction} Direction ({current_load_case})"
        )

        # Count available result types
        available_count = sum(
            1 for d in [displacements, drifts, accelerations, forces] if d is not None
        )
        window.statusBar().showMessage(
            f"Loaded time series data: {available_count} result types for {direction} direction"
        )

    except Exception as exc:
        window.statusBar().showMessage(f"Error loading time series data: {str(exc)}")
        log_exception(exc, "Error loading data")
