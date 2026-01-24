"""Plot construction helpers for max/min results."""

from __future__ import annotations

import pandas as pd
import pyqtgraph as pg
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from config.visual_config import AVERAGE_SERIES_COLOR, ZERO_LINE_COLOR, STORY_PADDING_MAXMIN, series_color
from gui.components.legend import InteractiveLegendItem, create_static_legend_item
from utils.plot_builder import PlotBuilder

from .maxmin_data_processor import MaxMinDataProcessor


class MaxMinPlotBuilder:
    """Builds plots and legends for max/min results."""

    def __init__(self, data_processor: MaxMinDataProcessor) -> None:
        self._data = data_processor

    def plot_maxmin_data(
        self,
        plot_widget,
        legend_layout,
        df: pd.DataFrame,
        max_cols: list[str],
        min_cols: list[str],
        story_names: list[str],
        direction: str,
        base_result_type: str,
        config,
        plot_items: dict,
        on_toggle,
        on_hover,
        on_leave,
    ) -> None:
        """Plot Max/Min drift data - horizontal orientation (drift on X, story on Y)."""
        plot_widget.clear()

        # Clear external legend
        self.clear_legend(legend_layout)
        plot_items.clear()

        if not story_names:
            return

        include_base_anchor = base_result_type == "Displacements"
        num_stories = len(story_names)
        story_indices = list(range(num_stories))
        if include_base_anchor:
            story_labels = ["Base"] + list(story_names)
            base_index = 0
            story_indices = [idx + 1 for idx in range(len(story_names))]
        else:
            story_labels = list(story_names)
            base_index = None
            story_indices = list(range(len(story_names)))

        # Collect all drift values for range calculation
        all_values = []

        # Detect whether Min columns already include sign (element-level forces/axials)
        signed_min_values = self._data.has_signed_min_values(df, min_cols)

        # Plot each load case - Max and Min with same color
        for idx, max_col in enumerate(max_cols):
            if max_col not in df.columns:
                continue

            load_case = self._data.extract_load_case_name(max_col, direction)

            # Find corresponding Min column
            if direction:
                load_case_full = max_col.replace(f"_{direction}", "").replace("Max_", "")
                min_col = f"Min_{load_case_full}_{direction}"
            else:
                load_case_full = max_col.replace("Max_", "")
                min_col = f"Min_{load_case_full}"

            if min_col not in min_cols:
                continue

            color = series_color(idx)

            # Get values
            max_values = df[max_col].values.tolist()
            if signed_min_values:
                min_values = df[min_col].values.tolist()
            else:
                # Magnitude-only datasets need to be mirrored to the negative side
                min_values = (-df[min_col].values).tolist()

            y_positions = list(story_indices)

            if include_base_anchor:
                # Anchor all series at the base so plotted lines originate at (0, 0)
                y_positions = [base_index] + y_positions
                max_values = [0.0] + max_values
                min_values = [0.0] + min_values

            # Collect values for range calculation
            all_values.extend(max_values)
            all_values.extend(min_values)

            # Plot Max values (positive drifts) - SOLID line
            max_item = plot_widget.plot(
                max_values,
                y_positions,
                pen=pg.mkPen(color=color, width=2),
                antialias=True,
            )

            # Plot Min values (negative drifts) - DASHED line, SAME COLOR
            min_item = plot_widget.plot(
                min_values,
                y_positions,
                pen=pg.mkPen(color=color, width=2, style=Qt.PenStyle.DashLine),
                antialias=True,
            )

            # Store plot items for highlighting
            plot_items[load_case] = {
                "max_item": max_item,
                "min_item": min_item,
                "color": color,
                "width": 2,
            }

            # Add to legend ONCE - just the load case name (no "Max" or "Min")
            self.add_legend_item(legend_layout, color, load_case, on_toggle, on_hover, on_leave)

        # Plot average envelopes (drawn last so they sit on top)
        max_avg_series = self._data.compute_average_series(df, max_cols)
        if max_avg_series is not None:
            avg_values = max_avg_series.tolist()
            y_positions = list(story_indices)
            if include_base_anchor:
                avg_values = [0.0] + avg_values
                y_positions = [base_index] + y_positions

            plot_widget.plot(
                avg_values,
                y_positions,
                pen=pg.mkPen(AVERAGE_SERIES_COLOR, width=5, style=Qt.PenStyle.SolidLine),
                antialias=True,
            )
            all_values.extend(avg_values)
            self.add_static_legend_item(legend_layout, AVERAGE_SERIES_COLOR, "Avg Max", Qt.PenStyle.SolidLine)

        min_avg_series = self._data.compute_average_series(df, min_cols, absolute=not signed_min_values)
        if min_avg_series is not None:
            raw_avg_values = min_avg_series.tolist()
            avg_values = raw_avg_values if signed_min_values else [-val for val in raw_avg_values]
            y_positions = list(story_indices)
            if include_base_anchor:
                avg_values = [0.0] + avg_values
                y_positions = [base_index] + y_positions

            plot_widget.plot(
                avg_values,
                y_positions,
                pen=pg.mkPen(AVERAGE_SERIES_COLOR, width=5, style=Qt.PenStyle.DashLine),
                antialias=True,
            )
            all_values.extend(avg_values)
            self.add_static_legend_item(legend_layout, AVERAGE_SERIES_COLOR, "Avg Min", Qt.PenStyle.DashLine)

        # Add zero drift line for symmetry (vertical line at x=0)
        plot_widget.addLine(x=0, pen=pg.mkPen(ZERO_LINE_COLOR, width=1, style=Qt.PenStyle.DotLine))

        # Use PlotBuilder for axis configuration (matching normal drift page)
        builder = PlotBuilder(plot_widget, config)

        # Configure axes with story labels (include base if needed)
        builder.setup_axes(story_labels)

        # Set y-axis range with tight padding
        builder.set_story_range(len(story_labels), padding=STORY_PADDING_MAXMIN)

        # Calculate x-axis range from all values
        all_values = [v for v in all_values if v != 0.0]
        if all_values:
            min_val = min(all_values)
            max_val = max(all_values)
            builder.set_value_range(min_val, max_val, left_padding=0.03, right_padding=0.05)

        # Set title
        builder.set_title(f"Max/Min {base_result_type} - {direction}")

        # Set dynamic tick spacing (6 intervals based on data range)
        if all_values:
            builder.set_dynamic_tick_spacing("bottom", min_val, max_val, num_intervals=6)

        # Lock the view ranges to prevent auto-scaling during pen updates
        view_box = plot_widget.getPlotItem().getViewBox()
        view_box.enableAutoRange(enable=False)

    @staticmethod
    def add_legend_item(legend_layout, color: str, label: str, on_toggle, on_hover, on_leave) -> None:
        """Add an interactive legend item to the external legend."""
        item_widget = InteractiveLegendItem(
            label=label,
            color=color,
            on_toggle=on_toggle,
            on_hover=on_hover,
            on_leave=on_leave,
        )
        legend_layout.addWidget(item_widget)

    @staticmethod
    def add_static_legend_item(legend_layout, color: str, label: str, pen_style: Qt.PenStyle) -> None:
        """Add a non-interactive legend item (for aggregate lines like averages)."""
        legend_layout.addWidget(create_static_legend_item(color, label, pen_style))

    @staticmethod
    def clear_legend(legend_layout) -> None:
        """Clear all items from the external legend."""
        while legend_layout.count():
            item = legend_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    @staticmethod
    def highlight_load_cases(plot_items: dict, selected_cases: list[str]) -> None:
        """Highlight selected load cases, dim others."""
        if not selected_cases:
            for case_data in plot_items.values():
                max_item = case_data["max_item"]
                min_item = case_data["min_item"]
                color = case_data["color"]
                width = case_data["width"]

                max_item.setPen(pg.mkPen(color, width=width))
                min_item.setPen(pg.mkPen(color, width=width, style=Qt.PenStyle.DashLine))
            return

        selected_set = set(selected_cases)
        for case_name, case_data in plot_items.items():
            max_item = case_data["max_item"]
            min_item = case_data["min_item"]
            color = case_data["color"]
            width = case_data["width"]

            if case_name in selected_set:
                max_item.setPen(pg.mkPen(color, width=width))
                min_item.setPen(pg.mkPen(color, width=width, style=Qt.PenStyle.DashLine))
            else:
                qcolor = QColor(color)
                qcolor.setAlpha(40)
                max_item.setPen(pg.mkPen(qcolor, width=width))
                min_item.setPen(pg.mkPen(qcolor, width=width, style=Qt.PenStyle.DashLine))

    def hover_load_case(self, plot_items: dict, current_selection: set, load_case: str) -> None:
        """Temporarily highlight a load case on hover."""
        if load_case not in plot_items:
            return

        for case_name, case_data in plot_items.items():
            max_item = case_data["max_item"]
            min_item = case_data["min_item"]
            color = case_data["color"]
            width = case_data["width"]

            if case_name == load_case:
                max_item.setPen(pg.mkPen(color, width=width))
                min_item.setPen(pg.mkPen(color, width=width, style=Qt.PenStyle.DashLine))
            elif case_name in current_selection:
                qcolor = QColor(color)
                qcolor.setAlpha(60)
                max_item.setPen(pg.mkPen(qcolor, width=width))
                min_item.setPen(pg.mkPen(qcolor, width=width, style=Qt.PenStyle.DashLine))
            else:
                qcolor = QColor(color)
                qcolor.setAlpha(25)
                max_item.setPen(pg.mkPen(qcolor, width=width))
                min_item.setPen(pg.mkPen(qcolor, width=width, style=Qt.PenStyle.DashLine))

    def clear_hover(self, plot_items: dict, current_selection: set) -> None:
        """Clear hover effect and restore to selected state."""
        self.highlight_load_cases(plot_items, list(current_selection))

    def toggle_load_case_selection(
        self,
        plot_items: dict,
        current_selection: set,
        load_case: str,
        legend_layout,
    ) -> None:
        """Toggle selection of a load case."""
        if load_case in current_selection:
            current_selection.remove(load_case)
        else:
            current_selection.add(load_case)

        self.highlight_load_cases(plot_items, list(current_selection))

        for i in range(legend_layout.count()):
            item = legend_layout.itemAt(i).widget()
            if isinstance(item, InteractiveLegendItem):
                item.set_selected(item.label in current_selection)
