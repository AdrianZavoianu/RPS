"""Shared element section rendering (beam/column rotations, soil pressures)."""

from __future__ import annotations

from typing import List, Tuple, Optional
import numpy as np
import pandas as pd

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QColor, QFont, QPen

from ..constants import PRINT_COLORS, PLOT_COLORS
from .context import RenderContext
from .table_renderer import TableRenderer
from .plot_renderer import PlotRenderer


class ElementSectionRenderer:
    """Renders element-based report sections (rotations, soil pressures)."""
    
    def __init__(self, painter: QPainter, ctx: RenderContext):
        self.painter = painter
        self.ctx = ctx
        self.table_renderer = TableRenderer(painter, ctx)
        self.plot_renderer = PlotRenderer(painter, ctx)
    
    def draw_beam_rotations_section(
        self,
        x: int, y: int, width: int, available_height: int,
        element_data: dict,
    ) -> None:
        """Draw beam rotations section with table and scatter plot."""
        top_10_df = element_data["top_10"]
        load_cases = element_data["load_cases"]
        stories = element_data.get("stories", [])
        plot_data_max = element_data.get("plot_data_max", [])
        plot_data_min = element_data.get("plot_data_min", [])
        
        # Table columns config
        columns_config = [
            {"name": "Beam", "width_mm": 10, "field": "Element", "max_chars": 6},
            {"name": "Story", "width_mm": 10, "field": "Story", "max_chars": 6},
            {"name": "Hinge", "width_mm": 6, "field": "Hinge", "max_chars": 5},
        ]
        
        # Draw table
        table_h = self.table_renderer.draw_element_table(
            x, y, width, top_10_df, load_cases, columns_config
        )
        current_y = y + table_h + (self.ctx.mm(3) if self.ctx.is_pdf else 8)
        
        # Draw scatter plot
        remaining = available_height - table_h - (self.ctx.mm(5) if self.ctx.is_pdf else 15)
        min_plot_h = self.ctx.mm(25) if self.ctx.is_pdf else 80
        
        if remaining > min_plot_h:
            scatter_points = self._build_rotation_scatter_points(
                plot_data_max, plot_data_min, stories
            )
            self.plot_renderer.draw_scatter_plot(
                x, current_y, width, remaining,
                scatter_points, stories,
                x_label="Beam Rotation [%]",
                symmetric_x=True,
            )
    
    def draw_column_rotations_section(
        self,
        x: int, y: int, width: int, available_height: int,
        element_data: dict,
    ) -> None:
        """Draw column rotations section with table and scatter plot."""
        top_10_df = element_data["top_10"]
        load_cases = element_data["load_cases"]
        stories = element_data.get("stories", [])
        plot_data_max = element_data.get("plot_data_max", [])
        plot_data_min = element_data.get("plot_data_min", [])
        
        # Table columns config (includes Dir for R2/R3)
        columns_config = [
            {"name": "Column", "width_mm": 10, "field": "Column", "max_chars": 6},
            {"name": "Story", "width_mm": 10, "field": "Story", "max_chars": 6},
            {"name": "Dir", "width_mm": 6, "field": "Dir", "max_chars": 3},
        ]
        
        # Draw table
        table_h = self.table_renderer.draw_element_table(
            x, y, width, top_10_df, load_cases, columns_config
        )
        current_y = y + table_h + (self.ctx.mm(3) if self.ctx.is_pdf else 8)
        
        # Draw scatter plot
        remaining = available_height - table_h - (self.ctx.mm(5) if self.ctx.is_pdf else 15)
        min_plot_h = self.ctx.mm(25) if self.ctx.is_pdf else 80
        
        if remaining > min_plot_h:
            scatter_points = self._build_rotation_scatter_points(
                plot_data_max, plot_data_min, stories
            )
            self.plot_renderer.draw_scatter_plot(
                x, current_y, width, remaining,
                scatter_points, stories,
                x_label="Column Rotation [%]",
                symmetric_x=True,
            )
    
    def draw_soil_pressures_section(
        self,
        x: int, y: int, width: int, available_height: int,
        joint_data: dict,
    ) -> None:
        """Draw soil pressures section with table and scatter plot."""
        top_10_df = joint_data["top_10"]
        load_cases = joint_data["load_cases"]
        plot_data = joint_data.get("plot_data", [])
        
        # Table columns config
        columns_config = [
            {"name": "Shell", "width_mm": 10, "field": "Shell", "max_chars": 6},
            {"name": "Name", "width_mm": 12, "field": "Name", "max_chars": 8},
        ]
        
        # Draw table
        table_h = self.table_renderer.draw_element_table(
            x, y, width, top_10_df, load_cases, columns_config
        )
        current_y = y + table_h + (self.ctx.mm(3) if self.ctx.is_pdf else 8)
        
        # Draw scatter plot (by load case)
        remaining = available_height - table_h - (self.ctx.mm(5) if self.ctx.is_pdf else 15)
        min_plot_h = self.ctx.mm(25) if self.ctx.is_pdf else 80
        
        if remaining > min_plot_h and plot_data:
            self._draw_soil_pressure_scatter(
                x, current_y, width, remaining, plot_data, load_cases
            )
    
    def _build_rotation_scatter_points(
        self,
        plot_data_max: List[Tuple],
        plot_data_min: List[Tuple],
        stories: List[str],
    ) -> List[Tuple[float, float]]:
        """Build scatter points with jitter for rotation plots."""
        story_to_idx = {name: idx for idx, name in enumerate(stories)}
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
        
        return scatter_points
    
    def _draw_soil_pressure_scatter(
        self,
        x: int, y: int, width: int, height: int,
        plot_data: List[Tuple[int, float]],
        load_cases: List[str],
    ) -> None:
        """Draw scatter plot for soil pressures (by load case index)."""
        if not plot_data or not load_cases:
            self.plot_renderer.draw_placeholder(x, y, width, height, "No soil pressure data")
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
        
        num_load_cases = len(load_cases)
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
        
        # Y-axis ticks
        y_ticks, _, _ = self.plot_renderer._nice_ticks(y_min, y_max, 5)
        
        # Horizontal grid
        self.painter.setPen(QPen(QColor(PRINT_COLORS["grid"]), 1, Qt.PenStyle.DotLine))
        for tick in y_ticks:
            gy = int(to_px_y(tick))
            self.painter.drawLine(plot_x, gy, plot_x + plot_w, gy)
        
        # Vertical grid (load case boundaries)
        for i in range(num_load_cases + 1):
            gx = int(plot_x + i * plot_w / num_load_cases)
            self.painter.drawLine(gx, plot_y, gx, plot_y + plot_h)
        
        # Scatter points
        blue_color = QColor("#2563eb")
        self.painter.setPen(QPen(blue_color.darker(110), 1))
        self.painter.setBrush(blue_color)
        point_radius = max(1, self.ctx.mm(0.5) if self.ctx.is_pdf else 2)
        
        np.random.seed(46)
        for lc_idx, pressure in plot_data:
            slot_w = plot_w / num_load_cases
            jitter = np.random.uniform(-slot_w * 0.35, slot_w * 0.35)
            px = int(to_px_x(lc_idx) + jitter)
            py = int(to_px_y(pressure))
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
        for tick in y_ticks:
            py = int(to_px_y(tick))
            label = f"{tick:.0f}"
            label_w = left_m - (self.ctx.mm(4) if self.ctx.is_pdf else 12)
            label_h = self.ctx.mm(3) if self.ctx.is_pdf else 10
            self.painter.drawText(
                x + (self.ctx.mm(2) if self.ctx.is_pdf else 8),
                py - label_h // 2,
                label_w, label_h,
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                label
            )
        
        # Y-axis title
        self.plot_renderer._draw_rotated_label(x, plot_y, plot_h, "Pressure (kN/m²)")
        
        # X-axis labels (load case names)
        self.painter.setFont(QFont("Segoe UI", self.ctx.font_size_small))
        for i, lc in enumerate(load_cases):
            px = int(to_px_x(i))
            label = str(lc)[:4]
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
                             Qt.AlignmentFlag.AlignCenter, "Load Case")
