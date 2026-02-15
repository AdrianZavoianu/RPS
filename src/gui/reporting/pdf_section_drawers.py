"""Section-specific PDF drawing helpers."""

from __future__ import annotations

from typing import Callable

import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QPen

from .constants import PRINT_COLORS


class PushoverSectionDrawer:
    """Draw specialized pushover sections (element/joint plots and tables)."""

    def __init__(self, draw_placeholder: Callable) -> None:
        self._placeholder_drawer = draw_placeholder

    def _draw_placeholder(self, painter, x: int, y: int, w: int, h: int, title: str) -> None:
        self._placeholder_drawer(painter, x, y, w, h, title)

    def _draw_beam_rotations_section(self, painter: QPainter, x: int, y: int, width: int,
                                     available_height: int, section, mm_to_px: float) -> None:
        """Draw beam rotations section with top 10 table and scatter plot."""
        element_data = section.element_data
        top_10_df = element_data["top_10"]
        load_cases = element_data["load_cases"]
        stories = element_data.get("stories", [])
        plot_data_max = element_data.get("plot_data_max", [])
        plot_data_min = element_data.get("plot_data_min", [])

        # Table for top 10 elements
        table_h = self._draw_beam_rotations_table(painter, x, y, width, top_10_df, load_cases, mm_to_px)
        current_y = y + table_h + int(3 * mm_to_px)

        # Plot for all data (both Max and Min)
        remaining = available_height - table_h - int(5 * mm_to_px)
        if remaining > int(25 * mm_to_px):
            self._draw_beam_rotations_plot(painter, x, current_y, width, remaining, plot_data_max, plot_data_min, mm_to_px, stories)

    def _draw_beam_rotations_table(self, painter: QPainter, x: int, y: int, width: int,
                                   df, load_cases: list, mm_to_px: float) -> int:
        """Draw beam rotations table showing top 10 elements. Returns height used."""
        import pandas as pd

        row_h = int(4 * mm_to_px)
        header_h = int(5 * mm_to_px)
        max_rows = min(len(df), 10)

        if max_rows == 0:
            return 0

        # Show ALL load cases, no limit
        displayed_load_cases = load_cases
        num_load_cases = len(displayed_load_cases)

        # Determine which summary columns are present (Avg may be excluded for Pushover)
        summary_cols = [c for c in ["Avg", "Max", "Min"] if c in df.columns]

        # Column widths - calculated to fit within available width
        elem_w = int(11 * mm_to_px)
        story_w = int(11 * mm_to_px)
        hinge_w = int(8 * mm_to_px)
        summary_w = int(10 * mm_to_px)  # For Avg, Max, Min columns
        num_summary = len(summary_cols)

        # Calculate load case column width - ensure everything fits
        fixed_cols_w = elem_w + story_w + hinge_w + (summary_w * num_summary)
        remaining_w = width - fixed_cols_w
        lc_w = max(int(7 * mm_to_px), remaining_w // num_load_cases) if num_load_cases > 0 else int(8 * mm_to_px)

        # Recalculate actual table width used
        actual_table_w = fixed_cols_w + (lc_w * num_load_cases)

        # Header
        painter.fillRect(x, y, width, header_h, QColor(PRINT_COLORS["header_bg"]))
        painter.setPen(QColor(PRINT_COLORS["text"]))
        painter.setFont(QFont("Segoe UI", 7, QFont.Weight.DemiBold))

        cx = x
        painter.drawText(cx, y, elem_w, header_h, Qt.AlignmentFlag.AlignCenter, "Beam")
        cx += elem_w
        painter.drawText(cx, y, story_w, header_h, Qt.AlignmentFlag.AlignCenter, "Story")
        cx += story_w
        painter.drawText(cx, y, hinge_w, header_h, Qt.AlignmentFlag.AlignCenter, "Hinge")
        cx += hinge_w
        for lc in displayed_load_cases:
            label = str(lc)[:4]  # Truncate to 4 chars
            painter.drawText(cx, y, lc_w, header_h, Qt.AlignmentFlag.AlignCenter, label)
            cx += lc_w
        # Draw dynamic summary columns
        for col in summary_cols:
            painter.drawText(cx, y, summary_w, header_h, Qt.AlignmentFlag.AlignCenter, col)
            cx += summary_w

        # Rows
        painter.setFont(QFont("Segoe UI", 7))
        for row_i in range(max_rows):
            ry = y + header_h + row_i * row_h

            if row_i % 2 == 1:
                painter.fillRect(x, ry, width, row_h, QColor(PRINT_COLORS["row_alt"]))

            painter.setPen(QColor(PRINT_COLORS["text"]))
            cx = x

            # Element name
            elem_name = str(df["Frame/Wall"].iloc[row_i])[:6] if "Frame/Wall" in df.columns else ""
            painter.drawText(cx, ry, elem_w, row_h, Qt.AlignmentFlag.AlignCenter, elem_name)
            cx += elem_w

            # Story
            story = str(df["Story"].iloc[row_i])[:6] if "Story" in df.columns else ""
            painter.drawText(cx, ry, story_w, row_h, Qt.AlignmentFlag.AlignCenter, story)
            cx += story_w

            # Hinge
            hinge = str(df["Hinge"].iloc[row_i])[:5] if "Hinge" in df.columns else ""
            painter.drawText(cx, ry, hinge_w, row_h, Qt.AlignmentFlag.AlignCenter, hinge)
            cx += hinge_w

            # Load case values
            for lc in displayed_load_cases:
                val = df[lc].iloc[row_i] if lc in df.columns else 0
                if pd.isna(val):
                    txt = "-"
                else:
                    txt = f"{val:.2f}"
                painter.drawText(cx, ry, lc_w, row_h, Qt.AlignmentFlag.AlignCenter, txt)
                cx += lc_w

            # Summary columns (dynamic based on what's in the dataframe)
            for col in summary_cols:
                val = df[col].iloc[row_i] if col in df.columns else 0
                if pd.isna(val):
                    txt = "-"
                else:
                    txt = f"{val:.2f}"
                painter.drawText(cx, ry, summary_w, row_h, Qt.AlignmentFlag.AlignCenter, txt)
                cx += summary_w

        # Border and grid - use actual_table_w to stay within bounds
        total_h = header_h + max_rows * row_h
        painter.setPen(QPen(QColor(PRINT_COLORS["border"]), 1))
        painter.drawRect(x, y, actual_table_w, total_h)

        # Vertical lines
        cx = x + elem_w
        painter.drawLine(cx, y, cx, y + total_h)
        cx += story_w
        painter.drawLine(cx, y, cx, y + total_h)
        cx += hinge_w
        painter.drawLine(cx, y, cx, y + total_h)
        for _ in displayed_load_cases:
            cx += lc_w
            painter.drawLine(cx, y, cx, y + total_h)
        # Summary column separators
        for _ in range(len(summary_cols) - 1):  # -1 because last line is the border
            cx += summary_w
            painter.drawLine(cx, y, cx, y + total_h)

        # Horizontal lines
        for i in range(max_rows + 1):
            ly = y + header_h + i * row_h
            painter.drawLine(x, ly, x + actual_table_w, ly)

        return total_h

    def _draw_beam_rotations_plot(self, painter: QPainter, x: int, y: int, width: int, height: int,
                                  plot_data_max: list, plot_data_min: list, mm_to_px: float, stories: list = None) -> None:
        """Draw scatter plot showing all beam rotation values (both Max and Min).

        Plot orientation matches the app:
        - Y-axis: Story (bottom floors at bottom, top floors at top)
        - X-axis: Rotation [%] (centered around 0)
        - Single blue color for all markers (suitable for light page background)
        """
        if not plot_data_max and not plot_data_min:
            self._draw_placeholder(painter, x, y, width, height, "No beam data")
            return

        # Margins
        left_m = int(18 * mm_to_px)  # More space for story labels
        right_m = int(3 * mm_to_px)
        top_m = int(3 * mm_to_px)
        bottom_m = int(10 * mm_to_px)

        plot_x = x + left_m
        plot_y = y + top_m
        plot_w = width - left_m - right_m
        plot_h = height - top_m - bottom_m

        if plot_w < int(30 * mm_to_px) or plot_h < int(20 * mm_to_px):
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
            self._draw_placeholder(painter, x, y, width, height, "No story data")
            return

        num_stories = len(stories)
        story_to_idx = {name: idx for idx, name in enumerate(stories)}

        # Get all rotation values for X-axis range
        all_values = [v for _, _, v in plot_data_max] + [v for _, _, v in plot_data_min]

        if not all_values:
            self._draw_placeholder(painter, x, y, width, height, "No rotation values")
            return

        # X-axis range: symmetric around zero
        abs_max = max(abs(min(all_values)), abs(max(all_values)))
        if abs_max == 0:
            abs_max = 1
        x_data_min, x_data_max = -abs_max * 1.1, abs_max * 1.1

        # Y-axis range: story indices
        y_data_min, y_data_max = -0.5, num_stories - 0.5

        def to_px_x(v):
            return plot_x + (v - x_data_min) / (x_data_max - x_data_min) * plot_w

        def to_px_y(v):
            return plot_y + plot_h - (v - y_data_min) / (y_data_max - y_data_min) * plot_h

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

        grid_ticks = nice_ticks(x_data_min, x_data_max, 6)
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
            self._draw_placeholder(painter, x, y, width, height, "No rotation values")
            return

        # Draw scatter points - single blue color (good for light background)
        blue_color = QColor("#2563eb")
        painter.setPen(QPen(blue_color.darker(110), 1))
        painter.setBrush(blue_color)
        point_radius = max(1, int(0.5 * mm_to_px))

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
        painter.setFont(QFont("Segoe UI", 7))
        for idx, story_name in enumerate(stories):
            py = int(to_px_y(idx))
            label = str(story_name)[:7]
            painter.drawText(x + int(1 * mm_to_px), py - int(1.5 * mm_to_px), left_m - int(3 * mm_to_px), int(3 * mm_to_px),
                           Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, label)

        # Y-axis label
        painter.save()
        painter.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
        painter.setPen(QColor(PRINT_COLORS["text"]))
        painter.translate(x + int(0.5 * mm_to_px), plot_y + plot_h // 2)
        painter.rotate(-90)
        painter.drawText(int(-6 * mm_to_px), 0, int(12 * mm_to_px), int(3 * mm_to_px), Qt.AlignmentFlag.AlignCenter, "Story")
        painter.restore()

        # X-axis tick labels - use the calculated nice ticks
        painter.setFont(QFont("Segoe UI", 7))
        for tick_val in grid_ticks:
            px = int(to_px_x(tick_val))
            label = f"{tick_val:.1f}" if abs(tick_val) < 10 else f"{tick_val:.0f}"
            painter.drawText(px - int(5 * mm_to_px), plot_y + plot_h + int(0.5 * mm_to_px), int(10 * mm_to_px), int(3 * mm_to_px),
                           Qt.AlignmentFlag.AlignCenter, label)

        # X-axis label
        painter.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
        painter.drawText(plot_x, plot_y + plot_h + int(4 * mm_to_px), plot_w, int(4 * mm_to_px),
                        Qt.AlignmentFlag.AlignCenter, "Beam Rotation [%]")

    def _draw_column_rotations_section(self, painter: QPainter, x: int, y: int, width: int,
                                       available_height: int, section, mm_to_px: float) -> None:
        """Draw column rotations section with top 10 table and scatter plot."""
        element_data = section.element_data
        top_10_df = element_data["top_10"]
        load_cases = element_data["load_cases"]
        stories = element_data.get("stories", [])
        plot_data_max = element_data.get("plot_data_max", [])
        plot_data_min = element_data.get("plot_data_min", [])

        # Table for top 10 elements
        table_h = self._draw_column_rotations_table(painter, x, y, width, top_10_df, load_cases, mm_to_px)
        current_y = y + table_h + int(3 * mm_to_px)

        # Plot for all data (both Max and Min)
        remaining = available_height - table_h - int(5 * mm_to_px)
        if remaining > int(25 * mm_to_px):
            self._draw_column_rotations_plot(painter, x, current_y, width, remaining, plot_data_max, plot_data_min, mm_to_px, stories)

    def _draw_column_rotations_table(self, painter: QPainter, x: int, y: int, width: int,
                                     df, load_cases: list, mm_to_px: float) -> int:
        """Draw column rotations table showing top 10 elements. Returns height used."""
        import pandas as pd

        row_h = int(4 * mm_to_px)
        header_h = int(5 * mm_to_px)
        max_rows = min(len(df), 10)

        if max_rows == 0:
            return 0

        # Show ALL load cases, no limit
        displayed_load_cases = load_cases
        num_load_cases = len(displayed_load_cases)

        # Determine which summary columns are present (Avg may be excluded for Pushover)
        summary_cols = [c for c in ["Avg", "Max", "Min"] if c in df.columns]

        # Column widths - includes Dir column for R2/R3
        col_w = int(10 * mm_to_px)  # Column name
        story_w = int(10 * mm_to_px)
        dir_w = int(6 * mm_to_px)  # R2 or R3
        summary_w = int(10 * mm_to_px)
        num_summary = len(summary_cols)

        # Calculate load case column width
        fixed_cols_w = col_w + story_w + dir_w + (summary_w * num_summary)
        remaining_w = width - fixed_cols_w
        lc_w = max(int(7 * mm_to_px), remaining_w // num_load_cases) if num_load_cases > 0 else int(8 * mm_to_px)

        # Recalculate actual table width used
        actual_table_w = fixed_cols_w + (lc_w * num_load_cases)

        # Header
        painter.fillRect(x, y, width, header_h, QColor(PRINT_COLORS["header_bg"]))
        painter.setPen(QColor(PRINT_COLORS["text"]))
        painter.setFont(QFont("Segoe UI", 7, QFont.Weight.DemiBold))

        cx = x
        painter.drawText(cx, y, col_w, header_h, Qt.AlignmentFlag.AlignCenter, "Column")
        cx += col_w
        painter.drawText(cx, y, story_w, header_h, Qt.AlignmentFlag.AlignCenter, "Story")
        cx += story_w
        painter.drawText(cx, y, dir_w, header_h, Qt.AlignmentFlag.AlignCenter, "Dir")
        cx += dir_w
        for lc in displayed_load_cases:
            label = str(lc)[:4]
            painter.drawText(cx, y, lc_w, header_h, Qt.AlignmentFlag.AlignCenter, label)
            cx += lc_w
        # Draw dynamic summary columns
        for col in summary_cols:
            painter.drawText(cx, y, summary_w, header_h, Qt.AlignmentFlag.AlignCenter, col)
            cx += summary_w

        # Rows
        painter.setFont(QFont("Segoe UI", 7))
        for row_i in range(max_rows):
            ry = y + header_h + row_i * row_h

            if row_i % 2 == 1:
                painter.fillRect(x, ry, width, row_h, QColor(PRINT_COLORS["row_alt"]))

            painter.setPen(QColor(PRINT_COLORS["text"]))
            cx = x

            # Column name
            col_name = str(df["Column"].iloc[row_i])[:6] if "Column" in df.columns else ""
            painter.drawText(cx, ry, col_w, row_h, Qt.AlignmentFlag.AlignCenter, col_name)
            cx += col_w

            # Story
            story = str(df["Story"].iloc[row_i])[:6] if "Story" in df.columns else ""
            painter.drawText(cx, ry, story_w, row_h, Qt.AlignmentFlag.AlignCenter, story)
            cx += story_w

            # Direction (R2/R3)
            dir_val = str(df["Dir"].iloc[row_i])[:3] if "Dir" in df.columns else ""
            painter.drawText(cx, ry, dir_w, row_h, Qt.AlignmentFlag.AlignCenter, dir_val)
            cx += dir_w

            # Load case values
            for lc in displayed_load_cases:
                val = df[lc].iloc[row_i] if lc in df.columns else 0
                if pd.isna(val):
                    txt = "-"
                else:
                    txt = f"{val:.2f}"
                painter.drawText(cx, ry, lc_w, row_h, Qt.AlignmentFlag.AlignCenter, txt)
                cx += lc_w

            # Summary columns (dynamic based on what's in the dataframe)
            for col in summary_cols:
                val = df[col].iloc[row_i] if col in df.columns else 0
                if pd.isna(val):
                    txt = "-"
                else:
                    txt = f"{val:.2f}"
                painter.drawText(cx, ry, summary_w, row_h, Qt.AlignmentFlag.AlignCenter, txt)
                cx += summary_w

        # Border and grid
        total_h = header_h + max_rows * row_h
        painter.setPen(QPen(QColor(PRINT_COLORS["border"]), 1))
        painter.drawRect(x, y, actual_table_w, total_h)

        # Vertical lines
        cx = x + col_w
        painter.drawLine(cx, y, cx, y + total_h)
        cx += story_w
        painter.drawLine(cx, y, cx, y + total_h)
        cx += dir_w
        painter.drawLine(cx, y, cx, y + total_h)
        for _ in displayed_load_cases:
            cx += lc_w
            painter.drawLine(cx, y, cx, y + total_h)
        for _ in range(len(summary_cols) - 1):
            cx += summary_w
            painter.drawLine(cx, y, cx, y + total_h)

        # Horizontal lines
        for i in range(max_rows + 1):
            ly = y + header_h + i * row_h
            painter.drawLine(x, ly, x + actual_table_w, ly)

        return total_h

    def _draw_column_rotations_plot(self, painter: QPainter, x: int, y: int, width: int, height: int,
                                    plot_data_max: list, plot_data_min: list, mm_to_px: float, stories: list = None) -> None:
        """Draw scatter plot showing all column rotation values (both Max and Min).

        Plot orientation matches beam rotations:
        - Y-axis: Story (bottom floors at bottom, top floors at top)
        - X-axis: Rotation [%] (centered around 0)
        - Single blue color for all markers
        """
        if not plot_data_max and not plot_data_min:
            self._draw_placeholder(painter, x, y, width, height, "No column data")
            return

        # Margins
        left_m = int(18 * mm_to_px)
        right_m = int(3 * mm_to_px)
        top_m = int(3 * mm_to_px)
        bottom_m = int(10 * mm_to_px)

        plot_x = x + left_m
        plot_y = y + top_m
        plot_w = width - left_m - right_m
        plot_h = height - top_m - bottom_m

        if plot_w < int(30 * mm_to_px) or plot_h < int(20 * mm_to_px):
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
            self._draw_placeholder(painter, x, y, width, height, "No story data")
            return

        num_stories = len(stories)
        story_to_idx = {name: idx for idx, name in enumerate(stories)}

        # Get all rotation values for X-axis range
        all_values = [v for _, _, v in plot_data_max] + [v for _, _, v in plot_data_min]

        if not all_values:
            self._draw_placeholder(painter, x, y, width, height, "No rotation values")
            return

        # X-axis range: symmetric around zero
        abs_max = max(abs(min(all_values)), abs(max(all_values)))
        if abs_max == 0:
            abs_max = 1
        x_data_min, x_data_max = -abs_max * 1.1, abs_max * 1.1

        # Y-axis range: story indices
        y_data_min, y_data_max = -0.5, num_stories - 0.5

        def to_px_x(v):
            return plot_x + (v - x_data_min) / (x_data_max - x_data_min) * plot_w

        def to_px_y(v):
            return plot_y + plot_h - (v - y_data_min) / (y_data_max - y_data_min) * plot_h

        # Vertical gridlines
        def nice_ticks(data_min, data_max, num_ticks=5):
            data_range = data_max - data_min
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

        grid_ticks = nice_ticks(x_data_min, x_data_max, 6)
        painter.setPen(QPen(QColor(PRINT_COLORS["grid"]), 1, Qt.PenStyle.DotLine))
        for tick in grid_ticks:
            if tick != 0:
                gx = int(to_px_x(tick))
                painter.drawLine(gx, plot_y, gx, plot_y + plot_h)

        # Zero line
        zero_x = int(to_px_x(0))
        painter.setPen(QPen(QColor("#4a7d89"), 1, Qt.PenStyle.DashLine))
        painter.drawLine(zero_x, plot_y, zero_x, plot_y + plot_h)

        # Horizontal gridlines for each story
        painter.setPen(QPen(QColor(PRINT_COLORS["grid"]), 1, Qt.PenStyle.DotLine))
        for idx in range(num_stories):
            gy = int(to_px_y(idx))
            painter.drawLine(plot_x, gy, plot_x + plot_w, gy)

        # Collect scatter points with jitter
        scatter_points = []
        np.random.seed(44)

        for story_name, _, rot_val in plot_data_max:
            if story_name not in story_to_idx:
                continue
            story_idx = story_to_idx[story_name]
            jitter = np.random.uniform(-0.25, 0.25)
            scatter_points.append((rot_val, story_idx + jitter))

        np.random.seed(45)
        for story_name, _, rot_val in plot_data_min:
            if story_name not in story_to_idx:
                continue
            story_idx = story_to_idx[story_name]
            jitter = np.random.uniform(-0.25, 0.25)
            scatter_points.append((rot_val, story_idx + jitter))

        if not scatter_points:
            self._draw_placeholder(painter, x, y, width, height, "No rotation values")
            return

        # Draw scatter points - blue color
        blue_color = QColor("#2563eb")
        painter.setPen(QPen(blue_color.darker(110), 1))
        painter.setBrush(blue_color)
        point_radius = max(1, int(0.5 * mm_to_px))

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
        painter.setFont(QFont("Segoe UI", 7))
        for idx, story_name in enumerate(stories):
            py = int(to_px_y(idx))
            label = str(story_name)[:7]
            painter.drawText(x + int(1 * mm_to_px), py - int(1.5 * mm_to_px), left_m - int(3 * mm_to_px), int(3 * mm_to_px),
                           Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, label)

        # Y-axis label
        painter.save()
        painter.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
        painter.setPen(QColor(PRINT_COLORS["text"]))
        painter.translate(x + int(0.5 * mm_to_px), plot_y + plot_h // 2)
        painter.rotate(-90)
        painter.drawText(int(-6 * mm_to_px), 0, int(12 * mm_to_px), int(3 * mm_to_px), Qt.AlignmentFlag.AlignCenter, "Story")
        painter.restore()

        # X-axis tick labels
        painter.setFont(QFont("Segoe UI", 7))
        for tick_val in grid_ticks:
            px = int(to_px_x(tick_val))
            label = f"{tick_val:.1f}" if abs(tick_val) < 10 else f"{tick_val:.0f}"
            painter.drawText(px - int(5 * mm_to_px), plot_y + plot_h + int(0.5 * mm_to_px), int(10 * mm_to_px), int(3 * mm_to_px),
                           Qt.AlignmentFlag.AlignCenter, label)

        # X-axis label
        painter.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
        painter.drawText(plot_x, plot_y + plot_h + int(4 * mm_to_px), plot_w, int(4 * mm_to_px),
                        Qt.AlignmentFlag.AlignCenter, "Column Rotation [%]")

    def _draw_soil_pressures_section(self, painter: QPainter, x: int, y: int, width: int,
                                     available_height: int, section, mm_to_px: float) -> None:
        """Draw soil pressures section with top 10 table and scatter plot."""
        joint_data = section.joint_data
        top_10_df = joint_data["top_10"]
        load_cases = joint_data["load_cases"]
        plot_data = joint_data.get("plot_data", [])

        # Table for top 10 elements
        table_h = self._draw_soil_pressures_table(painter, x, y, width, top_10_df, load_cases, mm_to_px)
        current_y = y + table_h + int(3 * mm_to_px)

        # Plot for all data
        remaining = available_height - table_h - int(5 * mm_to_px)
        if remaining > int(25 * mm_to_px):
            self._draw_soil_pressures_plot(painter, x, current_y, width, remaining, plot_data, load_cases, mm_to_px)

    def _draw_soil_pressures_table(self, painter: QPainter, x: int, y: int, width: int,
                                   df, load_cases: list, mm_to_px: float) -> int:
        """Draw soil pressures table showing top 10 elements. Returns height used."""
        import pandas as pd

        row_h = int(4 * mm_to_px)
        header_h = int(5 * mm_to_px)
        max_rows = min(len(df), 10)

        if max_rows == 0:
            return 0

        displayed_load_cases = load_cases
        num_load_cases = len(displayed_load_cases)

        # Determine which summary columns are present (Avg may be excluded for Pushover)
        summary_cols = [c for c in ["Avg", "Max", "Min"] if c in df.columns]

        # Column widths
        shell_w = int(12 * mm_to_px)
        name_w = int(12 * mm_to_px)
        summary_w = int(10 * mm_to_px)
        num_summary = len(summary_cols)

        # Calculate load case column width
        fixed_cols_w = shell_w + name_w + (summary_w * num_summary)
        remaining_w = width - fixed_cols_w
        lc_w = max(int(8 * mm_to_px), remaining_w // num_load_cases) if num_load_cases > 0 else int(8 * mm_to_px)

        actual_table_w = fixed_cols_w + (lc_w * num_load_cases)

        # Header
        painter.fillRect(x, y, width, header_h, QColor(PRINT_COLORS["header_bg"]))
        painter.setPen(QColor(PRINT_COLORS["text"]))
        painter.setFont(QFont("Segoe UI", 7, QFont.Weight.DemiBold))

        cx = x
        painter.drawText(cx, y, shell_w, header_h, Qt.AlignmentFlag.AlignCenter, "Shell")
        cx += shell_w
        painter.drawText(cx, y, name_w, header_h, Qt.AlignmentFlag.AlignCenter, "Name")
        cx += name_w
        for lc in displayed_load_cases:
            label = str(lc)[:4]
            painter.drawText(cx, y, lc_w, header_h, Qt.AlignmentFlag.AlignCenter, label)
            cx += lc_w
        # Draw dynamic summary columns
        for col in summary_cols:
            painter.drawText(cx, y, summary_w, header_h, Qt.AlignmentFlag.AlignCenter, col)
            cx += summary_w

        # Rows
        painter.setFont(QFont("Segoe UI", 7))
        for row_i in range(max_rows):
            ry = y + header_h + row_i * row_h

            if row_i % 2 == 1:
                painter.fillRect(x, ry, width, row_h, QColor(PRINT_COLORS["row_alt"]))

            painter.setPen(QColor(PRINT_COLORS["text"]))
            cx = x

            # Shell Object
            shell_obj = str(df["Shell Object"].iloc[row_i])[:6] if "Shell Object" in df.columns else ""
            painter.drawText(cx, ry, shell_w, row_h, Qt.AlignmentFlag.AlignCenter, shell_obj)
            cx += shell_w

            # Unique Name
            unique_name = str(df["Unique Name"].iloc[row_i])[:6] if "Unique Name" in df.columns else ""
            painter.drawText(cx, ry, name_w, row_h, Qt.AlignmentFlag.AlignCenter, unique_name)
            cx += name_w

            # Load case values (display absolute values)
            for lc in displayed_load_cases:
                val = df[lc].iloc[row_i] if lc in df.columns else 0
                if pd.isna(val):
                    txt = "-"
                else:
                    txt = f"{abs(val):.0f}"
                painter.drawText(cx, ry, lc_w, row_h, Qt.AlignmentFlag.AlignCenter, txt)
                cx += lc_w

            # Summary columns (dynamic based on what's in the dataframe)
            for col in summary_cols:
                val = df[col].iloc[row_i] if col in df.columns else 0
                if pd.isna(val):
                    txt = "-"
                else:
                    txt = f"{abs(val):.0f}"
                painter.drawText(cx, ry, summary_w, row_h, Qt.AlignmentFlag.AlignCenter, txt)
                cx += summary_w

        # Border and grid
        total_h = header_h + max_rows * row_h
        painter.setPen(QPen(QColor(PRINT_COLORS["border"]), 1))
        painter.drawRect(x, y, actual_table_w, total_h)

        # Vertical lines
        cx = x + shell_w
        painter.drawLine(cx, y, cx, y + total_h)
        cx += name_w
        painter.drawLine(cx, y, cx, y + total_h)
        for _ in displayed_load_cases:
            cx += lc_w
            painter.drawLine(cx, y, cx, y + total_h)
        for _ in range(len(summary_cols) - 1):
            cx += summary_w
            painter.drawLine(cx, y, cx, y + total_h)

        # Horizontal lines
        for i in range(max_rows + 1):
            ly = y + header_h + i * row_h
            painter.drawLine(x, ly, x + actual_table_w, ly)

        return total_h

    def _draw_soil_pressures_plot(self, painter: QPainter, x: int, y: int, width: int, height: int,
                                  plot_data: list, load_cases: list, mm_to_px: float) -> None:
        """Draw scatter plot showing all soil pressure values by load case.

        Plot matches app window style but with blue theme:
        - X-axis: Load Case (categorical)
        - Y-axis: Soil Pressure (kN/m²)
        - Blue color for markers
        """
        if not plot_data:
            self._draw_placeholder(painter, x, y, width, height, "No soil pressure data")
            return

        # Margins
        left_m = int(18 * mm_to_px)
        right_m = int(3 * mm_to_px)
        top_m = int(3 * mm_to_px)
        bottom_m = int(10 * mm_to_px)

        plot_x = x + left_m
        plot_y = y + top_m
        plot_w = width - left_m - right_m
        plot_h = height - top_m - bottom_m

        if plot_w < int(30 * mm_to_px) or plot_h < int(20 * mm_to_px):
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
            return

        y_min = 0
        y_max = max(all_values) * 1.1

        def to_px_x(lc_idx):
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
                return [data_min]
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

        # Draw scatter points - blue color
        blue_color = QColor("#2563eb")
        painter.setPen(QPen(blue_color.darker(110), 1))
        painter.setBrush(blue_color)
        point_radius = max(1, int(0.5 * mm_to_px))

        np.random.seed(46)
        for lc_idx, pressure in plot_data:
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
        painter.setFont(QFont("Segoe UI", 7))
        for tick in y_ticks:
            py = int(to_px_y(tick))
            label = f"{tick:.0f}"
            painter.drawText(x + int(2 * mm_to_px), py - int(1.5 * mm_to_px), left_m - int(4 * mm_to_px), int(3 * mm_to_px),
                           Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, label)

        # Y-axis label
        painter.save()
        painter.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
        painter.setPen(QColor(PRINT_COLORS["text"]))
        painter.translate(x + int(0.5 * mm_to_px), plot_y + plot_h // 2)
        painter.rotate(-90)
        painter.drawText(int(-15 * mm_to_px), 0, int(30 * mm_to_px), int(3 * mm_to_px), Qt.AlignmentFlag.AlignCenter, "Pressure (kN/m²)")
        painter.restore()

        # X-axis labels (load case names)
        painter.setFont(QFont("Segoe UI", 7))
        for i, lc in enumerate(load_cases):
            px = int(to_px_x(i))
            label = str(lc)[:4]
            painter.drawText(px - int(5 * mm_to_px), plot_y + plot_h + int(0.5 * mm_to_px), int(10 * mm_to_px), int(3 * mm_to_px),
                           Qt.AlignmentFlag.AlignCenter, label)

        # X-axis label
        painter.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
        painter.drawText(plot_x, plot_y + plot_h + int(4 * mm_to_px), plot_w, int(4 * mm_to_px),
                        Qt.AlignmentFlag.AlignCenter, "Load Case")

