"""Shared plot rendering logic for PDF and Preview."""

from __future__ import annotations

from typing import List, Tuple, Optional
import numpy as np
import pandas as pd

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QColor, QFont, QPen

from ..constants import PRINT_COLORS, PLOT_COLORS, AVERAGE_COLOR
from .context import RenderContext


class PlotRenderer:
    """Renders plots for reports (building profiles, scatter plots, etc.)."""
    
    def __init__(self, painter: QPainter, ctx: RenderContext):
        self.painter = painter
        self.ctx = ctx
    
    def draw_placeholder(self, x: int, y: int, width: int, height: int, title: str) -> None:
        """Draw a placeholder for missing data."""
        self.painter.fillRect(x, y, width, height, QColor(PRINT_COLORS["plot_bg"]))
        self.painter.setPen(QPen(QColor(PRINT_COLORS["border"]), 1))
        self.painter.drawRect(x, y, width, height)
        
        self.painter.setPen(QColor(PRINT_COLORS["text_muted"]))
        self.painter.setFont(QFont("Segoe UI", self.ctx.font_size_normal))
        self.painter.drawText(x, y, width, height, 
                             Qt.AlignmentFlag.AlignCenter, f"No data: {title}")
    
    def draw_building_profile(
        self,
        x: int, y: int, width: int, height: int,
        df: pd.DataFrame,
        x_label: str = "",
        is_pushover: bool = False,
    ) -> None:
        """Draw a building profile plot (story vs value).
        
        Y-axis: Stories (categorical)
        X-axis: Values (numeric)
        """
        if df is None or df.empty:
            self.draw_placeholder(x, y, width, height, "No data")
            return
        
        # Margins
        left_m = self.ctx.plot_margin_left
        right_m = self.ctx.plot_margin_right
        top_m = self.ctx.plot_margin_top
        bottom_m = self.ctx.plot_margin_bottom
        
        plot_x = x + left_m
        plot_y = y + top_m
        plot_w = width - left_m - right_m
        plot_h = height - top_m - bottom_m
        
        min_plot_w = self.ctx.mm(20) if self.ctx.is_pdf else 50
        min_plot_h = self.ctx.mm(15) if self.ctx.is_pdf else 50
        
        if plot_w < min_plot_w or plot_h < min_plot_h:
            return
        
        # Plot background
        self.painter.fillRect(plot_x, plot_y, plot_w, plot_h, QColor(PRINT_COLORS["plot_bg"]))
        self.painter.setPen(QPen(QColor(PRINT_COLORS["border"]), 1))
        self.painter.drawRect(plot_x, plot_y, plot_w, plot_h)
        
        # Data extraction
        stories = df['Story'].tolist() if 'Story' in df.columns else df.index.tolist()
        load_cols = [c for c in df.columns 
                    if c not in {'Story', 'Avg', 'Max', 'Min', 'Average', 'Maximum', 'Minimum'}]
        
        if not load_cols or not stories:
            self.draw_placeholder(x, y, width, height, "No data columns")
            return
        
        numeric_df = df[load_cols].apply(pd.to_numeric, errors='coerce')
        values = numeric_df.values.flatten()
        values = values[~np.isnan(values)]
        
        if len(values) == 0:
            self.draw_placeholder(x, y, width, height, "No numeric values")
            return
        
        # Calculate ranges and nice ticks
        v_min, v_max = float(np.min(values)), float(np.max(values))
        n_stories = len(stories)
        tick_values, adj_min, adj_max = self._nice_ticks(v_min, v_max, 5)
        
        # Coordinate transforms
        def to_px_x(v):
            if adj_max == adj_min:
                return plot_x + plot_w / 2
            return plot_x + (v - adj_min) / (adj_max - adj_min) * plot_w
        
        def to_px_y(i):
            if n_stories <= 1:
                return plot_y + plot_h / 2
            return plot_y + plot_h - (i / (n_stories - 1)) * plot_h
        
        # Grid lines
        self.painter.setPen(QPen(QColor(PRINT_COLORS["grid"]), 1, Qt.PenStyle.DotLine))
        for i in range(n_stories):
            py = int(to_px_y(i))
            self.painter.drawLine(plot_x, py, plot_x + plot_w, py)
        for v in tick_values:
            px = int(to_px_x(v))
            if plot_x <= px <= plot_x + plot_w:
                self.painter.drawLine(px, plot_y, px, plot_y + plot_h)
        
        # Draw load case lines
        line_width = max(1, self.ctx.mm(0.4) if self.ctx.is_pdf else 1)
        drawn_cols = load_cols[:12]  # Limit to 12 colors
        
        for idx, col in enumerate(drawn_cols):
            vals = numeric_df[col].fillna(0).tolist()
            color = QColor(PLOT_COLORS[idx % len(PLOT_COLORS)])
            self.painter.setPen(QPen(color, line_width))
            for i in range(len(vals) - 1):
                self.painter.drawLine(
                    int(to_px_x(vals[i])), int(to_px_y(i)),
                    int(to_px_x(vals[i + 1])), int(to_px_y(i + 1))
                )
        
        # Draw average line (NLTHA only)
        if not is_pushover and len(load_cols) > 1:
            avg = numeric_df.mean(axis=1, skipna=True).fillna(0).tolist()
            avg_width = max(3, self.ctx.mm(1.0) if self.ctx.is_pdf else 3)
            self.painter.setPen(QPen(QColor(AVERAGE_COLOR), avg_width, Qt.PenStyle.DashLine))
            for i in range(len(avg) - 1):
                self.painter.drawLine(
                    int(to_px_x(avg[i])), int(to_px_y(i)),
                    int(to_px_x(avg[i + 1])), int(to_px_y(i + 1))
                )
        
        # Reset brush after drawing
        self.painter.setBrush(Qt.BrushStyle.NoBrush)
        
        # Legend
        legend_items = [(col[:6], PLOT_COLORS[i % len(PLOT_COLORS)]) for i, col in enumerate(drawn_cols)]
        if not is_pushover and len(load_cols) > 1:
            legend_items.append(("Avg", AVERAGE_COLOR))
        
        self._draw_legend(x, plot_y + plot_h, width, legend_items)
        
        # Axes
        self.painter.setPen(QPen(QColor(PRINT_COLORS["text"]), 1))
        self.painter.drawLine(plot_x, plot_y, plot_x, plot_y + plot_h)
        self.painter.drawLine(plot_x, plot_y + plot_h, plot_x + plot_w, plot_y + plot_h)
        
        # Y-axis labels (stories)
        self._draw_y_axis_labels(x, plot_y, left_m, plot_h, stories, to_px_y)
        
        # X-axis labels (tick values)
        self._draw_x_axis_labels(plot_x, plot_y + plot_h, plot_w, tick_values, to_px_x, x_label)
    
    def draw_scatter_plot(
        self,
        x: int, y: int, width: int, height: int,
        scatter_points: List[Tuple[float, float]],
        stories: List[str],
        x_label: str = "Value",
        symmetric_x: bool = False,
    ) -> None:
        """Draw a scatter plot (story vs value) with jittered points.
        
        Args:
            scatter_points: List of (value, story_index_with_jitter) tuples
            stories: List of story names for Y-axis
            symmetric_x: If True, make X-axis symmetric around zero
        """
        if not scatter_points or not stories:
            self.draw_placeholder(x, y, width, height, "No data")
            return
        
        # Margins
        left_m = self.ctx.mm(18) if self.ctx.is_pdf else 55
        right_m = self.ctx.mm(3) if self.ctx.is_pdf else 10
        top_m = self.ctx.mm(3) if self.ctx.is_pdf else 10
        bottom_m = self.ctx.mm(10) if self.ctx.is_pdf else 35
        
        plot_x = x + left_m
        plot_y = y + top_m
        plot_w = width - left_m - right_m
        plot_h = height - top_m - bottom_m
        
        min_plot_w = self.ctx.mm(30) if self.ctx.is_pdf else 80
        min_plot_h = self.ctx.mm(20) if self.ctx.is_pdf else 60
        
        if plot_w < min_plot_w or plot_h < min_plot_h:
            return
        
        # Background
        self.painter.fillRect(plot_x, plot_y, plot_w, plot_h, QColor(PRINT_COLORS["plot_bg"]))
        self.painter.setPen(QPen(QColor(PRINT_COLORS["border"]), 1))
        self.painter.drawRect(plot_x, plot_y, plot_w, plot_h)
        
        num_stories = len(stories)
        all_values = [p[0] for p in scatter_points]
        
        # X-axis range
        if symmetric_x:
            abs_max = max(abs(min(all_values)), abs(max(all_values)))
            if abs_max == 0:
                abs_max = 1
            x_min, x_max = -abs_max * 1.1, abs_max * 1.1
        else:
            x_min = min(0, min(all_values))
            x_max = max(all_values) * 1.1
        
        # Y-axis range
        y_min, y_max = -0.5, num_stories - 0.5
        
        def to_px_x(v):
            if x_max == x_min:
                return plot_x + plot_w / 2
            return plot_x + (v - x_min) / (x_max - x_min) * plot_w
        
        def to_px_y(v):
            return plot_y + plot_h - (v - y_min) / (y_max - y_min) * plot_h
        
        # Grid lines
        grid_ticks, _, _ = self._nice_ticks(x_min, x_max, 6)
        self.painter.setPen(QPen(QColor(PRINT_COLORS["grid"]), 1, Qt.PenStyle.DotLine))
        for tick in grid_ticks:
            if tick != 0:
                gx = int(to_px_x(tick))
                self.painter.drawLine(gx, plot_y, gx, plot_y + plot_h)
        
        # Horizontal story lines
        for idx in range(num_stories):
            gy = int(to_px_y(idx))
            self.painter.drawLine(plot_x, gy, plot_x + plot_w, gy)
        
        # Zero line (if in range)
        if x_min <= 0 <= x_max:
            zero_x = int(to_px_x(0))
            self.painter.setPen(QPen(QColor("#4a7d89"), 1, Qt.PenStyle.DashLine))
            self.painter.drawLine(zero_x, plot_y, zero_x, plot_y + plot_h)
        
        # Draw scatter points
        blue_color = QColor("#2563eb")
        self.painter.setPen(QPen(blue_color.darker(110), 1))
        self.painter.setBrush(blue_color)
        point_radius = max(1, self.ctx.mm(0.5) if self.ctx.is_pdf else 2)
        
        for val, story_y in scatter_points:
            px = int(to_px_x(val))
            py = int(to_px_y(story_y))
            self.painter.drawEllipse(px - point_radius, py - point_radius, 
                                    point_radius * 2, point_radius * 2)
        
        # Reset brush
        self.painter.setBrush(Qt.BrushStyle.NoBrush)
        
        # Axes
        self.painter.setPen(QPen(QColor(PRINT_COLORS["text"]), 1))
        self.painter.drawLine(plot_x, plot_y, plot_x, plot_y + plot_h)
        self.painter.drawLine(plot_x, plot_y + plot_h, plot_x + plot_w, plot_y + plot_h)
        
        # Y-axis labels
        self.painter.setPen(QColor(PRINT_COLORS["text"]))
        self.painter.setFont(QFont("Segoe UI", self.ctx.font_size_small))
        for idx, story_name in enumerate(stories):
            py = int(to_px_y(idx))
            label = str(story_name)[:7]
            label_w = left_m - self.ctx.mm(3) if self.ctx.is_pdf else left_m - 8
            label_h = self.ctx.mm(3) if self.ctx.is_pdf else 10
            self.painter.drawText(
                x + (self.ctx.mm(1) if self.ctx.is_pdf else 4), 
                py - label_h // 2, 
                label_w, label_h,
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, 
                label
            )
        
        # Y-axis title
        self._draw_rotated_label(x, plot_y, plot_h, "Story")
        
        # X-axis labels
        self.painter.setFont(QFont("Segoe UI", self.ctx.font_size_small))
        for tick_val in grid_ticks:
            px = int(to_px_x(tick_val))
            label = f"{tick_val:.1f}" if abs(tick_val) < 10 else f"{tick_val:.0f}"
            label_w = self.ctx.mm(10) if self.ctx.is_pdf else 30
            label_h = self.ctx.mm(3) if self.ctx.is_pdf else 10
            self.painter.drawText(
                px - label_w // 2, 
                plot_y + plot_h + (self.ctx.mm(0.5) if self.ctx.is_pdf else 2),
                label_w, label_h,
                Qt.AlignmentFlag.AlignCenter, 
                label
            )
        
        # X-axis title
        self.painter.setFont(QFont("Segoe UI", self.ctx.font_size_header, QFont.Weight.DemiBold))
        title_y = plot_y + plot_h + (self.ctx.mm(4) if self.ctx.is_pdf else 12)
        title_h = self.ctx.mm(4) if self.ctx.is_pdf else 12
        self.painter.drawText(plot_x, title_y, plot_w, title_h, 
                             Qt.AlignmentFlag.AlignCenter, x_label)
    
    def _nice_ticks(self, vmin: float, vmax: float, n_ticks: int = 5) -> Tuple[List[float], float, float]:
        """Generate nicely rounded tick values."""
        if vmax <= vmin:
            return [vmin], vmin, vmax
        
        raw_step = (vmax - vmin) / (n_ticks - 1)
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
        
        nice_min = np.floor(vmin / nice_step) * nice_step
        nice_max = np.ceil(vmax / nice_step) * nice_step
        
        ticks = []
        t = nice_min
        while t <= nice_max + nice_step * 0.5:
            ticks.append(t)
            t += nice_step
        
        return ticks, nice_min, nice_max
    
    def _draw_legend(self, x: int, y: int, width: int, items: List[Tuple[str, str]]) -> None:
        """Draw a legend below the plot."""
        item_w = self.ctx.mm(12) if self.ctx.is_pdf else 42
        max_cols = min(len(items), width // item_w)
        if max_cols == 0:
            return
        
        item_h = self.ctx.mm(3) if self.ctx.is_pdf else 9
        total_w = max_cols * item_w
        start_x = x + (width - total_w) // 2
        legend_y = y + (self.ctx.mm(7) if self.ctx.is_pdf else 22)
        
        self.painter.setFont(QFont("Segoe UI", self.ctx.font_size_normal))
        
        for i, (label, color) in enumerate(items):
            row = i // max_cols
            col = i % max_cols
            lx = start_x + col * item_w
            ly = legend_y + row * item_h
            
            # Line sample
            line_len = self.ctx.mm(3) if self.ctx.is_pdf else 10
            self.painter.setPen(QPen(QColor(color), 2))
            self.painter.drawLine(lx, ly + item_h // 2, lx + line_len, ly + item_h // 2)
            
            # Label
            self.painter.setPen(QColor(PRINT_COLORS["text"]))
            label_x = lx + line_len + (self.ctx.mm(1) if self.ctx.is_pdf else 3)
            self.painter.drawText(label_x, ly, item_w - line_len - 4, item_h,
                                 Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, 
                                 label)
    
    def _draw_y_axis_labels(self, x: int, plot_y: int, left_m: int, plot_h: int, 
                           stories: List[str], to_px_y) -> None:
        """Draw Y-axis story labels."""
        self.painter.setPen(QColor(PRINT_COLORS["text"]))
        self.painter.setFont(QFont("Segoe UI", self.ctx.font_size_normal))
        
        for i, s in enumerate(stories):
            py = int(to_px_y(i))
            label = str(s)[:8]
            label_w = left_m - (self.ctx.mm(5) if self.ctx.is_pdf else 15)
            label_h = self.ctx.mm(3) if self.ctx.is_pdf else 10
            self.painter.drawText(
                x + (self.ctx.mm(3) if self.ctx.is_pdf else 8), 
                py - label_h // 2,
                label_w, label_h,
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, 
                label
            )
        
        # Y-axis title
        self._draw_rotated_label(x, plot_y, plot_h, "Story")
    
    def _draw_x_axis_labels(self, plot_x: int, bottom_y: int, plot_w: int,
                           tick_values: List[float], to_px_x, x_label: str) -> None:
        """Draw X-axis tick labels and title."""
        self.painter.setPen(QColor(PRINT_COLORS["text"]))
        self.painter.setFont(QFont("Segoe UI", self.ctx.font_size_normal))
        
        for v in tick_values:
            px = int(to_px_x(v))
            if plot_x <= px <= plot_x + plot_w:
                if v == int(v):
                    label = f"{int(v)}"
                else:
                    label = f"{v:.2f}"
                label_w = self.ctx.mm(12) if self.ctx.is_pdf else 36
                label_h = self.ctx.mm(3) if self.ctx.is_pdf else 10
                self.painter.drawText(
                    px - label_w // 2, 
                    bottom_y + (self.ctx.mm(0.5) if self.ctx.is_pdf else 2),
                    label_w, label_h,
                    Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, 
                    label
                )
        
        # X-axis title
        if x_label:
            self.painter.setFont(QFont("Segoe UI", self.ctx.font_size_title, QFont.Weight.DemiBold))
            title_y = bottom_y + (self.ctx.mm(3.5) if self.ctx.is_pdf else 12)
            title_h = self.ctx.mm(3) if self.ctx.is_pdf else 12
            self.painter.drawText(plot_x, title_y, plot_w, title_h,
                                 Qt.AlignmentFlag.AlignCenter, x_label)
    
    def _draw_rotated_label(self, x: int, plot_y: int, plot_h: int, label: str) -> None:
        """Draw a rotated label (for Y-axis title)."""
        self.painter.save()
        self.painter.setFont(QFont("Segoe UI", self.ctx.font_size_title, QFont.Weight.DemiBold))
        self.painter.setPen(QColor(PRINT_COLORS["text"]))
        
        offset_x = self.ctx.mm(1) if self.ctx.is_pdf else 2
        label_w = self.ctx.mm(16) if self.ctx.is_pdf else 30
        label_h = self.ctx.mm(3) if self.ctx.is_pdf else 10
        
        self.painter.translate(x + offset_x, plot_y + plot_h // 2)
        self.painter.rotate(-90)
        self.painter.drawText(-label_w // 2, 0, label_w, label_h, 
                             Qt.AlignmentFlag.AlignCenter, label)
        self.painter.restore()
