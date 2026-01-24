"""Plot rendering logic for report preview pages."""

from __future__ import annotations

import numpy as np
import pandas as pd
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QColor, QFont, QPen

from .constants import PRINT_COLORS, PLOT_COLORS, AVERAGE_COLOR


class ReportPlotRenderer:
    """Renders plots for report preview sections."""

    def draw_placeholder(self, painter: QPainter, x: int, y: int, w: int, h: int, title: str) -> None:
        painter.fillRect(x, y, w, h, QColor("#f8fafc"))
        painter.setPen(QPen(QColor(PRINT_COLORS["border"]), 1))
        painter.drawRect(x, y, w, h)
        painter.setPen(QColor(PRINT_COLORS["text_muted"]))
        painter.setFont(QFont("Segoe UI", 8))
        painter.drawText(x, y, w, h, Qt.AlignmentFlag.AlignCenter, f"No data\n{title}")

    def draw_plot(self, painter: QPainter, x: int, y: int, width: int, height: int, section, is_pushover: bool = False) -> None:
        """Draw building profile plot filling the given area."""
        if not hasattr(section, "dataset") or section.dataset is None:
            self.draw_placeholder(painter, x, y, width, height, section.title)
            return

        df = section.dataset.data
        if df is None or df.empty:
            self.draw_placeholder(painter, x, y, width, height, section.title)
            return

        # Margins for axis labels and legend
        left_m = 50
        right_m = 10
        top_m = 10
        bottom_m = 38  # Extra space for legend below plot

        plot_x = x + left_m
        plot_y = y + top_m
        plot_w = width - left_m - right_m
        plot_h = height - top_m - bottom_m

        if plot_w < 50 or plot_h < 50:
            return

        # Light gray background for plot area
        painter.fillRect(plot_x, plot_y, plot_w, plot_h, QColor(PRINT_COLORS["plot_bg"]))
        painter.setPen(QPen(QColor(PRINT_COLORS["border"]), 1))
        painter.drawRect(plot_x, plot_y, plot_w, plot_h)

        # Data
        stories = df["Story"].tolist() if "Story" in df.columns else df.index.tolist()
        load_cols = [
            c
            for c in df.columns
            if c not in {"Story", "Avg", "Max", "Min", "Average", "Maximum", "Minimum"}
        ]

        if not load_cols or not stories:
            self.draw_placeholder(painter, x, y, width, height, section.title)
            return

        numeric_df = df[load_cols].apply(pd.to_numeric, errors="coerce")
        values = numeric_df.values.flatten()
        values = values[~np.isnan(values)]

        if len(values) == 0:
            self.draw_placeholder(painter, x, y, width, height, section.title)
            return

        # Ranges with nice tick values
        v_min, v_max = float(np.min(values)), float(np.max(values))
        n_stories = len(stories)

        # Calculate nice tick values (round numbers)
        def nice_ticks(vmin, vmax, n_ticks=5):
            """Generate nicely rounded tick values."""
            if vmax <= vmin:
                return [vmin], vmin, vmax
            raw_step = (vmax - vmin) / (n_ticks - 1)
            # Round to nice values: 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5...
            magnitude = 10 ** np.floor(np.log10(raw_step))
            residual = raw_step / magnitude
            if residual <= 1.5:
                nice_step = magnitude
            elif residual <= 3:
                nice_step = 2 * magnitude
            elif residual <= 7:
                nice_step = 5 * magnitude
            else:
                nice_step = 10 * magnitude
            # Extend range to include nice boundaries
            nice_min = np.floor(vmin / nice_step) * nice_step
            nice_max = np.ceil(vmax / nice_step) * nice_step
            ticks = []
            v = nice_min
            while v <= nice_max + nice_step * 0.01:
                ticks.append(round(v, 10))
                v += nice_step
            return ticks, nice_min, nice_max

        tick_values, x_min, x_max = nice_ticks(v_min, v_max)

        def to_px_x(v):
            if x_max == x_min:
                return plot_x + plot_w / 2
            return plot_x + (v - x_min) / (x_max - x_min) * plot_w

        def to_px_y(i):
            return plot_y + plot_h - (i + 0.5) / n_stories * plot_h

        # Grid - horizontal lines for stories
        painter.setPen(QPen(QColor(PRINT_COLORS["grid"]), 1, Qt.PenStyle.DotLine))
        for i in range(n_stories):
            py = int(to_px_y(i))
            painter.drawLine(plot_x, py, plot_x + plot_w, py)
        # Vertical grid lines at nice tick values
        for v in tick_values:
            px = int(to_px_x(v))
            if plot_x <= px <= plot_x + plot_w:
                painter.drawLine(px, plot_y, px, plot_y + plot_h)

        # Lines
        drawn_cols = load_cols[:12]
        for idx, col in enumerate(drawn_cols):
            vals = numeric_df[col].fillna(0).tolist()
            color = QColor(PLOT_COLORS[idx % len(PLOT_COLORS)])
            painter.setPen(QPen(color, 1.5))
            for i in range(len(vals) - 1):
                painter.drawLine(
                    int(to_px_x(vals[i])),
                    int(to_px_y(i)),
                    int(to_px_x(vals[i + 1])),
                    int(to_px_y(i + 1)),
                )

        # Draw average line only for NLTHA (not Pushover)
        if len(drawn_cols) > 1 and not is_pushover:
            # Average - thicker line for prominence
            avg = numeric_df.mean(axis=1, skipna=True).fillna(0).tolist()
            painter.setPen(QPen(QColor(AVERAGE_COLOR), 3, Qt.PenStyle.DashLine))
            for i in range(len(avg) - 1):
                painter.drawLine(
                    int(to_px_x(avg[i])),
                    int(to_px_y(i)),
                    int(to_px_x(avg[i + 1])),
                    int(to_px_y(i + 1)),
                )

        # Legend setup - calculate layout for later drawing
        legend_items = [(col[:6], PLOT_COLORS[i % len(PLOT_COLORS)]) for i, col in enumerate(drawn_cols)]
        # Add Avg to legend only for NLTHA (not Pushover)
        if len(drawn_cols) > 1 and not is_pushover:
            legend_items.append(("Avg", AVERAGE_COLOR))

        item_w = 42
        max_cols = min(len(legend_items), plot_w // item_w)
        item_h = 9
        total_legend_w = max_cols * item_w
        legend_start_x = plot_x + (plot_w - total_legend_w) // 2

        # Axes
        painter.setPen(QPen(QColor(PRINT_COLORS["text"]), 1))
        painter.drawLine(plot_x, plot_y, plot_x, plot_y + plot_h)
        painter.drawLine(plot_x, plot_y + plot_h, plot_x + plot_w, plot_y + plot_h)

        # Y labels (stories) - more prominent
        painter.setPen(QColor(PRINT_COLORS["text"]))
        painter.setFont(QFont("Segoe UI", 6))
        for i, s in enumerate(stories):
            py = int(to_px_y(i))
            painter.drawText(
                x + 12,
                py - 6,
                left_m - 16,
                12,
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                str(s)[:8],
            )

        # Y axis label ("Story") - rotated vertically, more prominent
        painter.save()
        painter.setFont(QFont("Segoe UI", 7, QFont.Weight.DemiBold))
        painter.setPen(QColor(PRINT_COLORS["text"]))
        painter.translate(x + 4, plot_y + plot_h // 2)
        painter.rotate(-90)
        painter.drawText(-30, 0, 60, 14, Qt.AlignmentFlag.AlignCenter, "Story")
        painter.restore()

        # X tick labels
        painter.setPen(QColor(PRINT_COLORS["text"]))
        painter.setFont(QFont("Segoe UI", 6))
        for v in tick_values:
            px = int(to_px_x(v))
            if plot_x <= px <= plot_x + plot_w:
                # Format: show integer if whole number, else 2 decimals
                if v == int(v):
                    label = f"{int(v)}"
                else:
                    label = f"{v:.2f}"
                painter.drawText(
                    px - 25,
                    plot_y + plot_h + 1,
                    50,
                    12,
                    Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                    label,
                )

        # X axis label - below tick labels (use y_label from config which has units)
        painter.setFont(QFont("Segoe UI", 7, QFont.Weight.DemiBold))
        x_label = getattr(section.dataset.config, "y_label", None)
        if not x_label:
            unit = getattr(section.dataset.config, "unit", "")
            x_label = f"{section.result_type} ({unit})" if unit else section.result_type
        painter.drawText(plot_x, plot_y + plot_h + 11, plot_w, 14, Qt.AlignmentFlag.AlignCenter, x_label)

        # Legend - below axis name
        legend_y_final = plot_y + plot_h + 24
        painter.setFont(QFont("Segoe UI", 5))
        for i, (label, color) in enumerate(legend_items):
            row = i // max_cols
            col = i % max_cols
            lx = legend_start_x + col * item_w
            ly = legend_y_final + row * item_h

            # Color line
            painter.setPen(QPen(QColor(color), 2))
            painter.drawLine(lx, ly + 4, lx + 10, ly + 4)

            # Label
            painter.setPen(QColor(PRINT_COLORS["text"]))
            painter.drawText(
                lx + 12,
                ly,
                item_w - 14,
                item_h,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                label,
            )

    def draw_beam_rotations_plot(
        self,
        painter: QPainter,
        x: int,
        y: int,
        width: int,
        height: int,
        plot_data_max: list,
        plot_data_min: list,
        stories: list | None = None,
    ) -> None:
        """Draw scatter plot showing all beam rotation values (both Max and Min).

        Plot orientation matches the app:
        - Y-axis: Story (bottom floors at bottom, top floors at top)
        - X-axis: Rotation [%] (centered around 0)
        - Single blue color for all markers (suitable for light page background)
        """
        if not plot_data_max and not plot_data_min:
            self.draw_placeholder(painter, x, y, width, height, "No beam data")
            return

        # Margins
        left_m = 50  # More space for story labels
        right_m = 10
        top_m = 10
        bottom_m = 25

        plot_x = x + left_m
        plot_y = y + top_m
        plot_w = width - left_m - right_m
        plot_h = height - top_m - bottom_m

        if plot_w < 50 or plot_h < 40:
            return

        # Background
        painter.fillRect(plot_x, plot_y, plot_w, plot_h, QColor(PRINT_COLORS["plot_bg"]))
        painter.setPen(QPen(QColor(PRINT_COLORS["border"]), 1))
        painter.drawRect(plot_x, plot_y, plot_w, plot_h)

        # Get stories from plot data if not provided
        if not stories:
            all_stories = {}
            for story_name, story_order, _ in plot_data_max + plot_data_min:
                if story_name not in all_stories:
                    all_stories[story_name] = story_order
            if all_stories:
                sorted_stories = sorted(all_stories.items(), key=lambda x: x[1])
                stories = list(reversed([s[0] for s in sorted_stories]))

        if not stories:
            self.draw_placeholder(painter, x, y, width, height, "No story data")
            return

        num_stories = len(stories)
        story_to_idx = {name: idx for idx, name in enumerate(stories)}

        # Get all rotation values for X-axis range
        all_values = [v for _, _, v in plot_data_max] + [v for _, _, v in plot_data_min]

        if not all_values:
            self.draw_placeholder(painter, x, y, width, height, "No rotation values")
            return

        # X-axis range: symmetric around zero
        abs_max = max(abs(min(all_values)), abs(max(all_values)))
        if abs_max == 0:
            abs_max = 1
        x_min, x_max = -abs_max * 1.1, abs_max * 1.1

        # Y-axis range: story indices
        y_min, y_max = -0.5, num_stories - 0.5

        def to_px_x(v):
            return plot_x + (v - x_min) / (x_max - x_min) * plot_w

        def to_px_y(v):
            return plot_y + plot_h - (v - y_min) / (y_max - y_min) * plot_h

        # Vertical gridlines - calculate nice tick values
        def nice_ticks(data_min, data_max, num_ticks=5):
            """Generate nice round tick values for the axis."""
            data_range = data_max - data_min
            rough_step = data_range / num_ticks
            # Round to nice value
            magnitude = 10 ** np.floor(np.log10(rough_step))
            residual = rough_step / magnitude
            if residual > 5:
                nice_step = 10 * magnitude
            elif residual > 2:
                nice_step = 5 * magnitude
            elif residual > 1:
                nice_step = 2 * magnitude
            else:
                nice_step = magnitude
            # Generate ticks
            start = np.ceil(data_min / nice_step) * nice_step
            ticks = []
            t = start
            while t <= data_max:
                ticks.append(t)
                t += nice_step
            return ticks

        grid_ticks = nice_ticks(x_min, x_max, 6)
        painter.setPen(QPen(QColor(PRINT_COLORS["grid"]), 1, Qt.PenStyle.DotLine))
        for tick in grid_ticks:
            if tick != 0:  # Skip zero, we'll draw it separately
                gx = int(to_px_x(tick))
                painter.drawLine(gx, plot_y, gx, plot_y + plot_h)

        # Zero line (vertical at x=0) - more prominent
        zero_x = int(to_px_x(0))
        painter.setPen(QPen(QColor("#4a7d89"), 1, Qt.PenStyle.DashLine))
        painter.drawLine(zero_x, plot_y, zero_x, plot_y + plot_h)

        # Horizontal gridlines for each story
        painter.setPen(QPen(QColor(PRINT_COLORS["grid"]), 1, Qt.PenStyle.DotLine))
        for idx in range(num_stories):
            gy = int(to_px_y(idx))
            painter.drawLine(plot_x, gy, plot_x + plot_w, gy)

        # Collect scatter points with jitter: (rotation_value, story_index_with_jitter)
        scatter_points = []
        np.random.seed(42)  # Reproducible jitter for Max data

        for story_name, _, rot_val in plot_data_max:
            if story_name not in story_to_idx:
                continue
            story_idx = story_to_idx[story_name]
            jitter = np.random.uniform(-0.25, 0.25)
            scatter_points.append((rot_val, story_idx + jitter))

        np.random.seed(43)  # Different seed for Min data
        for story_name, _, rot_val in plot_data_min:
            if story_name not in story_to_idx:
                continue
            story_idx = story_to_idx[story_name]
            jitter = np.random.uniform(-0.25, 0.25)
            scatter_points.append((rot_val, story_idx + jitter))

        if not scatter_points:
            self.draw_placeholder(painter, x, y, width, height, "No rotation values")
            return

        # Draw scatter points - single blue color (good for light background)
        blue_color = QColor("#2563eb")
        painter.setPen(QPen(blue_color.darker(110), 1))
        painter.setBrush(blue_color)
        point_radius = 2

        for rot_val, story_y in scatter_points:
            px = int(to_px_x(rot_val))
            py = int(to_px_y(story_y))
            painter.drawEllipse(px - point_radius, py - point_radius, point_radius * 2, point_radius * 2)

        # Reset brush to prevent blue fill on subsequent draws
        painter.setBrush(Qt.BrushStyle.NoBrush)

        # Axes
        painter.setPen(QPen(QColor(PRINT_COLORS["text"]), 1))
        painter.drawLine(plot_x, plot_y, plot_x, plot_y + plot_h)
        painter.drawLine(plot_x, plot_y + plot_h, plot_x + plot_w, plot_y + plot_h)

        # Y-axis story labels
        painter.setPen(QColor(PRINT_COLORS["text"]))
        painter.setFont(QFont("Segoe UI", 5))
        for idx, story_name in enumerate(stories):
            py = int(to_px_y(idx))
            label = str(story_name)[:6]
            painter.drawText(
                x + 4,
                py - 5,
                left_m - 8,
                10,
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                label,
            )

        # Y-axis label
        painter.save()
        painter.setFont(QFont("Segoe UI", 6, QFont.Weight.DemiBold))
        painter.setPen(QColor(PRINT_COLORS["text"]))
        painter.translate(x + 2, plot_y + plot_h // 2)
        painter.rotate(-90)
        painter.drawText(-15, 0, 30, 10, Qt.AlignmentFlag.AlignCenter, "Story")
        painter.restore()

        # X-axis tick labels - use the calculated nice ticks
        painter.setFont(QFont("Segoe UI", 5))
        for tick_val in grid_ticks:
            px = int(to_px_x(tick_val))
            label = f"{tick_val:.1f}" if abs(tick_val) < 10 else f"{tick_val:.0f}"
            painter.drawText(px - 15, plot_y + plot_h + 2, 30, 10, Qt.AlignmentFlag.AlignCenter, label)

        # X-axis label
        painter.setFont(QFont("Segoe UI", 6, QFont.Weight.DemiBold))
        painter.drawText(
            plot_x, plot_y + plot_h + 12, plot_w, 12, Qt.AlignmentFlag.AlignCenter, "Beam Rotation [%]"
        )

    def draw_column_rotations_plot(
        self,
        painter: QPainter,
        x: int,
        y: int,
        width: int,
        height: int,
        plot_data_max: list,
        plot_data_min: list,
        stories: list | None = None,
    ) -> None:
        """Draw scatter plot showing all column rotation values (both Max and Min).

        Plot orientation matches the app:
        - Y-axis: Story (bottom floors at bottom, top floors at top)
        - X-axis: Rotation [%] (centered around 0)
        - Single blue color for all markers (suitable for light page background)
        """
        if not plot_data_max and not plot_data_min:
            self.draw_placeholder(painter, x, y, width, height, "No column data")
            return

        # Margins
        left_m = 50  # More space for story labels
        right_m = 10
        top_m = 10
        bottom_m = 25

        plot_x = x + left_m
        plot_y = y + top_m
        plot_w = width - left_m - right_m
        plot_h = height - top_m - bottom_m

        if plot_w < 50 or plot_h < 40:
            return

        # Background
        painter.fillRect(plot_x, plot_y, plot_w, plot_h, QColor(PRINT_COLORS["plot_bg"]))
        painter.setPen(QPen(QColor(PRINT_COLORS["border"]), 1))
        painter.drawRect(plot_x, plot_y, plot_w, plot_h)

        # Get stories from plot data if not provided
        if not stories:
            all_stories = {}
            for story_name, story_order, _ in plot_data_max + plot_data_min:
                if story_name not in all_stories:
                    all_stories[story_name] = story_order
            if all_stories:
                sorted_stories = sorted(all_stories.items(), key=lambda x: x[1])
                stories = list(reversed([s[0] for s in sorted_stories]))

        if not stories:
            self.draw_placeholder(painter, x, y, width, height, "No story data")
            return

        num_stories = len(stories)
        story_to_idx = {name: idx for idx, name in enumerate(stories)}

        # Get all rotation values for X-axis range
        all_values = [v for _, _, v in plot_data_max] + [v for _, _, v in plot_data_min]

        if not all_values:
            self.draw_placeholder(painter, x, y, width, height, "No rotation values")
            return

        # X-axis range: symmetric around zero
        abs_max = max(abs(min(all_values)), abs(max(all_values)))
        if abs_max == 0:
            abs_max = 1
        x_min, x_max = -abs_max * 1.1, abs_max * 1.1

        # Y-axis range: story indices
        y_min, y_max = -0.5, num_stories - 0.5

        def to_px_x(v):
            return plot_x + (v - x_min) / (x_max - x_min) * plot_w

        def to_px_y(v):
            return plot_y + plot_h - (v - y_min) / (y_max - y_min) * plot_h

        # Vertical gridlines - calculate nice tick values
        def nice_ticks(data_min, data_max, num_ticks=5):
            """Generate nice round tick values for the axis."""
            data_range = data_max - data_min
            rough_step = data_range / num_ticks
            # Round to nice value
            magnitude = 10 ** np.floor(np.log10(rough_step))
            residual = rough_step / magnitude
            if residual > 5:
                nice_step = 10 * magnitude
            elif residual > 2:
                nice_step = 5 * magnitude
            elif residual > 1:
                nice_step = 2 * magnitude
            else:
                nice_step = magnitude
            # Generate ticks
            start = np.ceil(data_min / nice_step) * nice_step
            ticks = []
            t = start
            while t <= data_max:
                ticks.append(t)
                t += nice_step
            return ticks

        grid_ticks = nice_ticks(x_min, x_max, 6)
        painter.setPen(QPen(QColor(PRINT_COLORS["grid"]), 1, Qt.PenStyle.DotLine))
        for tick in grid_ticks:
            if tick != 0:  # Skip zero, we'll draw it separately
                gx = int(to_px_x(tick))
                painter.drawLine(gx, plot_y, gx, plot_y + plot_h)

        # Zero line (vertical at x=0) - more prominent
        zero_x = int(to_px_x(0))
        painter.setPen(QPen(QColor("#4a7d89"), 1, Qt.PenStyle.DashLine))
        painter.drawLine(zero_x, plot_y, zero_x, plot_y + plot_h)

        # Horizontal gridlines for each story
        painter.setPen(QPen(QColor(PRINT_COLORS["grid"]), 1, Qt.PenStyle.DotLine))
        for idx in range(num_stories):
            gy = int(to_px_y(idx))
            painter.drawLine(plot_x, gy, plot_x + plot_w, gy)

        # Collect scatter points with jitter: (rotation_value, story_index_with_jitter)
        scatter_points = []
        np.random.seed(44)  # Reproducible jitter for Max data

        for story_name, _, rot_val in plot_data_max:
            if story_name not in story_to_idx:
                continue
            story_idx = story_to_idx[story_name]
            jitter = np.random.uniform(-0.25, 0.25)
            scatter_points.append((rot_val, story_idx + jitter))

        np.random.seed(45)  # Different seed for Min data
        for story_name, _, rot_val in plot_data_min:
            if story_name not in story_to_idx:
                continue
            story_idx = story_to_idx[story_name]
            jitter = np.random.uniform(-0.25, 0.25)
            scatter_points.append((rot_val, story_idx + jitter))

        if not scatter_points:
            self.draw_placeholder(painter, x, y, width, height, "No rotation values")
            return

        # Draw scatter points - single blue color (good for light background)
        blue_color = QColor("#2563eb")
        painter.setPen(QPen(blue_color.darker(110), 1))
        painter.setBrush(blue_color)
        point_radius = 2

        for rot_val, story_y in scatter_points:
            px = int(to_px_x(rot_val))
            py = int(to_px_y(story_y))
            painter.drawEllipse(px - point_radius, py - point_radius, point_radius * 2, point_radius * 2)

        # Reset brush to prevent blue fill on subsequent draws
        painter.setBrush(Qt.BrushStyle.NoBrush)

        # Axes
        painter.setPen(QPen(QColor(PRINT_COLORS["text"]), 1))
        painter.drawLine(plot_x, plot_y, plot_x, plot_y + plot_h)
        painter.drawLine(plot_x, plot_y + plot_h, plot_x + plot_w, plot_y + plot_h)

        # Y-axis story labels
        painter.setPen(QColor(PRINT_COLORS["text"]))
        painter.setFont(QFont("Segoe UI", 5))
        for idx, story_name in enumerate(stories):
            py = int(to_px_y(idx))
            label = str(story_name)[:6]
            painter.drawText(
                x + 4,
                py - 5,
                left_m - 8,
                10,
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                label,
            )

        # Y-axis label
        painter.save()
        painter.setFont(QFont("Segoe UI", 6, QFont.Weight.DemiBold))
        painter.setPen(QColor(PRINT_COLORS["text"]))
        painter.translate(x + 2, plot_y + plot_h // 2)
        painter.rotate(-90)
        painter.drawText(-15, 0, 30, 10, Qt.AlignmentFlag.AlignCenter, "Story")
        painter.restore()

        # X-axis tick labels - use the calculated nice ticks
        painter.setFont(QFont("Segoe UI", 5))
        for tick_val in grid_ticks:
            px = int(to_px_x(tick_val))
            label = f"{tick_val:.1f}" if abs(tick_val) < 10 else f"{tick_val:.0f}"
            painter.drawText(px - 15, plot_y + plot_h + 2, 30, 10, Qt.AlignmentFlag.AlignCenter, label)

        # X-axis label
        painter.setFont(QFont("Segoe UI", 6, QFont.Weight.DemiBold))
        painter.drawText(
            plot_x, plot_y + plot_h + 12, plot_w, 12, Qt.AlignmentFlag.AlignCenter, "Column Rotation [%]"
        )

    def draw_soil_pressures_plot(
        self,
        painter: QPainter,
        x: int,
        y: int,
        width: int,
        height: int,
        plot_data: list,
        load_cases: list,
    ) -> None:
        """Draw scatter plot showing all soil pressure values by load case.

        Plot matches app window style but with blue theme:
        - X-axis: Load Case (categorical)
        - Y-axis: Soil Pressure (kN/m^2)
        - Blue color for markers
        """
        if not plot_data:
            self.draw_placeholder(painter, x, y, width, height, "No soil pressure data")
            return

        # Margins
        left_m = 50
        right_m = 10
        top_m = 10
        bottom_m = 25

        plot_x = x + left_m
        plot_y = y + top_m
        plot_w = width - left_m - right_m
        plot_h = height - top_m - bottom_m

        if plot_w < 50 or plot_h < 40:
            return

        # Background
        painter.fillRect(plot_x, plot_y, plot_w, plot_h, QColor(PRINT_COLORS["plot_bg"]))
        painter.setPen(QPen(QColor(PRINT_COLORS["border"]), 1))
        painter.drawRect(plot_x, plot_y, plot_w, plot_h)

        num_load_cases = len(load_cases)
        if num_load_cases == 0:
            return

        # Get all pressure values for Y-axis range
        all_values = [v for _, v in plot_data]
        if not all_values:
            self.draw_placeholder(painter, x, y, width, height, "No pressure values")
            return

        y_min = 0
        y_max = max(all_values) * 1.1

        def to_px_x(lc_idx):
            # Center each load case in its slot
            slot_w = plot_w / num_load_cases
            return plot_x + (lc_idx + 0.5) * slot_w

        def to_px_y(v):
            if y_max == y_min:
                return plot_y + plot_h / 2
            return plot_y + plot_h - (v - y_min) / (y_max - y_min) * plot_h

        # Calculate nice Y-axis tick values
        def nice_ticks(data_min, data_max, num_ticks=5):
            data_range = data_max - data_min
            if data_range == 0:
                return [data_min], data_min, data_max
            rough_step = data_range / num_ticks
            magnitude = 10 ** np.floor(np.log10(rough_step))
            residual = rough_step / magnitude
            if residual > 5:
                nice_step = 10 * magnitude
            elif residual > 2:
                nice_step = 5 * magnitude
            elif residual > 1:
                nice_step = 2 * magnitude
            else:
                nice_step = magnitude
            start = np.ceil(data_min / nice_step) * nice_step
            ticks = []
            t = start
            while t <= data_max:
                ticks.append(t)
                t += nice_step
            return ticks

        y_ticks = nice_ticks(y_min, y_max, 5)

        # Horizontal gridlines
        painter.setPen(QPen(QColor(PRINT_COLORS["grid"]), 1, Qt.PenStyle.DotLine))
        for tick in y_ticks:
            gy = int(to_px_y(tick))
            painter.drawLine(plot_x, gy, plot_x + plot_w, gy)

        # Vertical gridlines for load cases
        for i in range(num_load_cases + 1):
            gx = int(plot_x + i * plot_w / num_load_cases)
            painter.drawLine(gx, plot_y, gx, plot_y + plot_h)

        # Draw scatter points - blue color theme
        blue_color = QColor("#2563eb")
        painter.setPen(QPen(blue_color.darker(110), 1))
        painter.setBrush(blue_color)
        point_radius = 2

        np.random.seed(46)  # Reproducible jitter
        for lc_idx, pressure in plot_data:
            # Add horizontal jitter within load case slot
            slot_w = plot_w / num_load_cases
            jitter = np.random.uniform(-slot_w * 0.35, slot_w * 0.35)
            px = int(to_px_x(lc_idx) + jitter)
            py = int(to_px_y(pressure))
            painter.drawEllipse(px - point_radius, py - point_radius, point_radius * 2, point_radius * 2)

        # Reset brush to prevent blue fill on subsequent draws
        painter.setBrush(Qt.BrushStyle.NoBrush)

        # Axes
        painter.setPen(QPen(QColor(PRINT_COLORS["text"]), 1))
        painter.drawLine(plot_x, plot_y, plot_x, plot_y + plot_h)
        painter.drawLine(plot_x, plot_y + plot_h, plot_x + plot_w, plot_y + plot_h)

        # Y-axis tick labels
        painter.setPen(QColor(PRINT_COLORS["text"]))
        painter.setFont(QFont("Segoe UI", 5))
        for tick in y_ticks:
            py = int(to_px_y(tick))
            label = f"{tick:.0f}"
            painter.drawText(
                x + 8,
                py - 5,
                left_m - 12,
                10,
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                label,
            )

        # Y-axis label
        painter.save()
        painter.setFont(QFont("Segoe UI", 6, QFont.Weight.DemiBold))
        painter.setPen(QColor(PRINT_COLORS["text"]))
        painter.translate(x + 2, plot_y + plot_h // 2)
        painter.rotate(-90)
        painter.drawText(-35, 0, 70, 10, Qt.AlignmentFlag.AlignCenter, "Pressure (kN/m\u00b2)")
        painter.restore()

        # X-axis labels (load case names)
        painter.setFont(QFont("Segoe UI", 5))
        for i, lc in enumerate(load_cases):
            px = int(to_px_x(i))
            label = str(lc)[:4]
            painter.drawText(px - 15, plot_y + plot_h + 2, 30, 10, Qt.AlignmentFlag.AlignCenter, label)

        # X-axis label
        painter.setFont(QFont("Segoe UI", 6, QFont.Weight.DemiBold))
        painter.drawText(plot_x, plot_y + plot_h + 12, plot_w, 12, Qt.AlignmentFlag.AlignCenter, "Load Case")
