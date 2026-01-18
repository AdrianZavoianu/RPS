"""A4 page preview widget for report generation."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, List
import logging

import numpy as np
import pandas as pd
from PyQt6.QtWidgets import (
    QWidget,
    QScrollArea,
    QVBoxLayout,
    QLabel,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QPainter, QColor, QFont, QPixmap, QPen, QImage

from gui.styles import COLORS
from gui.icon_utils import ICONS_DIR

logger = logging.getLogger(__name__)

# A4 dimensions in mm at 2.5 scale = pixels
A4_WIDTH_PX = 525   # 210mm * 2.5
A4_HEIGHT_PX = 743  # 297mm * 2.5

# Page layout in pixels (direct values for precision)
PAGE_MARGIN = 20
HEADER_HEIGHT = 34
FOOTER_HEIGHT = 18
SECTION_GAP = 8

# Colors for print (light background)
PRINT_COLORS = {
    "text": "#1f2937",
    "text_muted": "#6b7280",
    "border": "#d1d5db",
    "grid": "#e5e7eb",
    "header_bg": "#f3f4f6",
    "row_alt": "#f9fafb",
    "plot_bg": "#f8f9fa",
}

# Plot colors - high contrast for light background
PLOT_COLORS = (
    "#dc2626", "#2563eb", "#16a34a", "#ea580c", "#7c3aed",
    "#0891b2", "#ca8a04", "#db2777", "#4f46e5", "#059669",
    "#0284c7", "#be185d",
)
AVERAGE_COLOR = "#92400e"


class ReportPageWidget(QWidget):
    """Widget representing a single A4 page in the preview."""

    def __init__(self, project_name: str, page_number: int = 1, parent=None):
        super().__init__(parent)
        self.project_name = project_name
        self.page_number = page_number
        self.sections: List = []

        self.setFixedSize(A4_WIDTH_PX, A4_HEIGHT_PX)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        # Load and colorize logo mask (like main window)
        logo_path = ICONS_DIR / "RPS_Logo.png"
        self._logo = self._load_colorized_logo(logo_path)

    def _load_colorized_logo(self, logo_path: Path) -> QPixmap:
        """Load logo mask and colorize it for print (dark color on light background)."""
        if not logo_path.exists():
            return QPixmap()

        image = QImage(str(logo_path))
        if image.isNull():
            return QPixmap()

        # Use dark teal color for print
        logo_color = QColor("#1f5c6a")
        image = image.convertToFormat(QImage.Format.Format_ARGB32)

        # Colorize each pixel based on alpha
        for y in range(image.height()):
            for x in range(image.width()):
                pixel = image.pixelColor(x, y)
                if pixel.alpha() > 0:
                    new_color = QColor(logo_color)
                    new_color.setAlpha(pixel.alpha())
                    image.setPixelColor(x, y, new_color)

        return QPixmap.fromImage(image)

    @classmethod
    def estimate_section_height(cls, section, available_width: int = 485) -> int:
        """Estimate height for a section."""
        height = 20  # Title

        # Check for element results (beam/column rotations)
        if section.category == "Element" and hasattr(section, 'element_data') and section.element_data is not None:
            # Table: top 10 rows
            rows = min(len(section.element_data.get("top_10", [])), 10)
            height += 16 + rows * 14 + 8  # header + rows + gap
            # Plot
            height += 150
            return height

        # Check for joint results (soil pressures)
        if section.category == "Joint" and hasattr(section, 'joint_data') and section.joint_data is not None:
            # Table: top 10 rows
            rows = min(len(section.joint_data.get("top_10", [])), 10)
            height += 16 + rows * 14 + 8  # header + rows + gap
            # Plot
            height += 150
            return height

        # Standard global results
        # Table
        if hasattr(section, 'dataset') and section.dataset is not None:
            df = section.dataset.data
            if df is not None and not df.empty:
                rows = min(len(df), 20)
                height += 18 + rows * 14 + 4

        # Plot - use remaining space, minimum 200px
        height += 200
        return height

    @classmethod
    def get_content_height(cls) -> int:
        """Available content height."""
        return A4_HEIGHT_PX - 2 * PAGE_MARGIN - HEADER_HEIGHT - FOOTER_HEIGHT - 10

    def set_sections(self, sections: list) -> None:
        self.sections = sections
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        # White background
        painter.fillRect(self.rect(), QColor("#ffffff"))

        # Page border
        painter.setPen(QPen(QColor(COLORS['border']), 1))
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))

        content_x = PAGE_MARGIN
        content_width = A4_WIDTH_PX - 2 * PAGE_MARGIN
        content_top = PAGE_MARGIN + HEADER_HEIGHT + 4
        content_bottom = A4_HEIGHT_PX - PAGE_MARGIN - FOOTER_HEIGHT

        # Header
        self._draw_header(painter, content_x, PAGE_MARGIN, content_width)

        # Calculate available height for sections
        available_height = content_bottom - content_top
        num_sections = len(self.sections)

        if num_sections > 0:
            # Distribute space evenly among sections
            section_height = (available_height - (num_sections - 1) * SECTION_GAP) // num_sections
            y = content_top

            for section in self.sections:
                self._draw_section(painter, content_x, y, content_width, section_height, section)
                y += section_height + SECTION_GAP

        # Footer
        self._draw_footer(painter, content_x, A4_HEIGHT_PX - PAGE_MARGIN - FOOTER_HEIGHT, content_width)

        painter.end()

    def _draw_header(self, painter: QPainter, x: int, y: int, width: int) -> None:
        """Draw compact header with logo and project name."""
        # Logo - 22px height, positioned at top
        logo_h = 22
        if not self._logo.isNull():
            scaled = self._logo.scaledToHeight(logo_h, Qt.TransformationMode.SmoothTransformation)
            painter.drawPixmap(x, y, scaled)
            logo_w = scaled.width()
        else:
            logo_w = 0

        # Project name - aligned with logo
        painter.setPen(QColor(PRINT_COLORS["text"]))
        painter.setFont(QFont("Segoe UI", 9))
        text_rect = QRectF(x + logo_w + 10, y, width - logo_w - 10, logo_h)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, self.project_name)

        # Separator - small gap below logo
        painter.setPen(QPen(QColor(PRINT_COLORS["grid"]), 1))
        painter.drawLine(x, y + HEADER_HEIGHT, x + width, y + HEADER_HEIGHT)

    def _draw_section(self, painter: QPainter, x: int, y: int, width: int, total_height: int, section) -> None:
        """Draw a section with table and plot filling the allocated height."""
        # Title
        painter.setPen(QColor(PRINT_COLORS["text"]))
        painter.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
        title_h = 18
        title_gap = 6  # Space below title
        painter.drawText(x, y, width, title_h, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, section.title)

        current_y = y + title_h + title_gap

        # Check if this is an element section (Beam/Column Rotations)
        if section.category == "Element" and hasattr(section, 'element_data') and section.element_data is not None:
            if section.result_type == "BeamRotations":
                self._draw_beam_rotations_section(painter, x, current_y, width, total_height - title_h - title_gap, section)
            elif section.result_type == "ColumnRotations":
                self._draw_column_rotations_section(painter, x, current_y, width, total_height - title_h - title_gap, section)
            return

        # Check if this is a joint section (Soil Pressures)
        if section.category == "Joint" and hasattr(section, 'joint_data') and section.joint_data is not None:
            if section.result_type == "SoilPressures_Min":
                self._draw_soil_pressures_section(painter, x, current_y, width, total_height - title_h - title_gap, section)
            return

        # Standard global results section
        # Check if this is Pushover analysis
        is_pushover = getattr(section, 'analysis_context', 'NLTHA') == 'Pushover'
        
        # Table
        table_h = 0
        if hasattr(section, 'dataset') and section.dataset is not None and section.dataset.data is not None:
            df = section.dataset.data
            if not df.empty:
                table_h = self._draw_table(painter, x, current_y, width, section.dataset, is_pushover)
                current_y += table_h + 4

        # Plot fills remaining space
        remaining = total_height - title_h - title_gap - table_h - 8
        if remaining > 50:
            self._draw_plot(painter, x, current_y, width, remaining, section, is_pushover)

    def _draw_table(self, painter: QPainter, x: int, y: int, width: int, dataset, is_pushover: bool = False) -> int:
        """Draw table, return height used."""
        df = dataset.data
        config = dataset.config
        decimals = getattr(config, 'decimal_places', 3)

        row_h = 14
        header_h = 16
        max_rows = min(len(df), 20)

        # Columns - exclude Avg for Pushover analysis
        if is_pushover:
            summary = [c for c in df.columns if c in {'Max', 'Min'}]
        else:
            summary = [c for c in df.columns if c in {'Avg', 'Max', 'Min'}]
        load_cases = [c for c in df.columns if c not in {'Story', 'Avg', 'Max', 'Min', 'Average', 'Maximum', 'Minimum'}]
        data_cols = load_cases[:11] + summary[:3]

        if not data_cols:
            return 0

        # Column widths
        story_w = 45
        col_w = (width - story_w) // len(data_cols)

        # Header
        painter.fillRect(x, y, width, header_h, QColor(PRINT_COLORS["header_bg"]))
        painter.setPen(QColor(PRINT_COLORS["text"]))
        painter.setFont(QFont("Segoe UI", 6, QFont.Weight.DemiBold))

        painter.drawText(x, y, story_w, header_h, Qt.AlignmentFlag.AlignCenter, "Story")
        for i, col in enumerate(data_cols):
            cx = x + story_w + i * col_w
            label = str(col)[:6]
            painter.drawText(cx, y, col_w, header_h, Qt.AlignmentFlag.AlignCenter, label)

        # Rows
        painter.setFont(QFont("Segoe UI", 6))
        for row_i in range(max_rows):
            ry = y + header_h + row_i * row_h

            if row_i % 2 == 1:
                painter.fillRect(x, ry, width, row_h, QColor(PRINT_COLORS["row_alt"]))

            # Story
            story = str(df['Story'].iloc[row_i])[:8] if 'Story' in df.columns else str(df.index[row_i])[:8]
            painter.setPen(QColor(PRINT_COLORS["text"]))
            painter.drawText(x, ry, story_w, row_h, Qt.AlignmentFlag.AlignCenter, story)

            # Values
            for col_i, col in enumerate(data_cols):
                cx = x + story_w + col_i * col_w
                val = df[col].iloc[row_i]
                if pd.isna(val):
                    txt = "-"
                elif isinstance(val, (int, float)):
                    txt = f"{val:.{decimals}f}"
                else:
                    txt = str(val)[:6]
                painter.drawText(cx, ry, col_w, row_h, Qt.AlignmentFlag.AlignCenter, txt)

        # Border and grid
        total_h = header_h + max_rows * row_h
        painter.setPen(QPen(QColor(PRINT_COLORS["border"]), 1))
        painter.drawRect(x, y, width, total_h)
        painter.drawLine(x + story_w, y, x + story_w, y + total_h)
        for i in range(1, len(data_cols)):
            lx = x + story_w + i * col_w
            painter.drawLine(lx, y, lx, y + total_h)
        for i in range(max_rows + 1):
            ly = y + header_h + i * row_h
            painter.drawLine(x, ly, x + width, ly)

        return total_h

    def _draw_plot(self, painter: QPainter, x: int, y: int, width: int, height: int, section, is_pushover: bool = False) -> None:
        """Draw building profile plot filling the given area."""
        if not hasattr(section, 'dataset') or section.dataset is None:
            self._draw_placeholder(painter, x, y, width, height, section.title)
            return

        df = section.dataset.data
        if df is None or df.empty:
            self._draw_placeholder(painter, x, y, width, height, section.title)
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
        stories = df['Story'].tolist() if 'Story' in df.columns else df.index.tolist()
        load_cols = [c for c in df.columns if c not in {'Story', 'Avg', 'Max', 'Min', 'Average', 'Maximum', 'Minimum'}]

        if not load_cols or not stories:
            self._draw_placeholder(painter, x, y, width, height, section.title)
            return

        numeric_df = df[load_cols].apply(pd.to_numeric, errors='coerce')
        values = numeric_df.values.flatten()
        values = values[~np.isnan(values)]

        if len(values) == 0:
            self._draw_placeholder(painter, x, y, width, height, section.title)
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
                painter.drawLine(int(to_px_x(vals[i])), int(to_px_y(i)),
                               int(to_px_x(vals[i + 1])), int(to_px_y(i + 1)))

        # Draw average line only for NLTHA (not Pushover)
        if len(drawn_cols) > 1 and not is_pushover:
            # Average
            avg = numeric_df.mean(axis=1, skipna=True).fillna(0).tolist()
            painter.setPen(QPen(QColor(AVERAGE_COLOR), 2, Qt.PenStyle.DashLine))
            for i in range(len(avg) - 1):
                painter.drawLine(int(to_px_x(avg[i])), int(to_px_y(i)),
                               int(to_px_x(avg[i + 1])), int(to_px_y(i + 1)))

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
            painter.drawText(x + 12, py - 6, left_m - 16, 12,
                           Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, str(s)[:8])

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
                painter.drawText(px - 25, plot_y + plot_h + 1, 50, 12,
                               Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, label)

        # X axis label - below tick labels (use y_label from config which has units)
        painter.setFont(QFont("Segoe UI", 7, QFont.Weight.DemiBold))
        x_label = getattr(section.dataset.config, 'y_label', None)
        if not x_label:
            unit = getattr(section.dataset.config, 'unit', '')
            x_label = f"{section.result_type} ({unit})" if unit else section.result_type
        painter.drawText(plot_x, plot_y + plot_h + 11, plot_w, 14,
                        Qt.AlignmentFlag.AlignCenter, x_label)

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
            painter.drawText(lx + 12, ly, item_w - 14, item_h,
                           Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, label)

    def _draw_placeholder(self, painter: QPainter, x: int, y: int, w: int, h: int, title: str) -> None:
        painter.fillRect(x, y, w, h, QColor("#f8fafc"))
        painter.setPen(QPen(QColor(PRINT_COLORS["border"]), 1))
        painter.drawRect(x, y, w, h)
        painter.setPen(QColor(PRINT_COLORS["text_muted"]))
        painter.setFont(QFont("Segoe UI", 8))
        painter.drawText(x, y, w, h, Qt.AlignmentFlag.AlignCenter, f"No data\n{title}")

    def _draw_beam_rotations_section(self, painter: QPainter, x: int, y: int, width: int, available_height: int, section) -> None:
        """Draw beam rotations section with top 10 table and scatter plot of all data."""
        element_data = section.element_data
        top_10_df = element_data["top_10"]
        load_cases = element_data["load_cases"]
        stories = element_data.get("stories", [])
        plot_data_max = element_data.get("plot_data_max", [])
        plot_data_min = element_data.get("plot_data_min", [])

        # Table for top 10 elements (by absolute average)
        table_h = self._draw_beam_rotations_table(painter, x, y, width, top_10_df, load_cases)
        current_y = y + table_h + 8

        # Plot for all data (scatter) - pass both Max and Min data separately
        remaining = available_height - table_h - 12
        if remaining > 60:
            self._draw_beam_rotations_plot(painter, x, current_y, width, remaining, plot_data_max, plot_data_min, stories)

    def _draw_beam_rotations_table(self, painter: QPainter, x: int, y: int, width: int, df, load_cases: list) -> int:
        """Draw beam rotations table showing top 10 elements by absolute average.

        Returns height used.
        """
        row_h = 14
        header_h = 16
        max_rows = min(len(df), 10)

        if max_rows == 0:
            return 0

        # Columns: Element | Story | Hinge | ALL Load Cases | Avg | Max | Min
        # Show all load cases, no limit
        displayed_load_cases = load_cases
        num_load_cases = len(displayed_load_cases)

        # Determine which summary columns are present
        summary_cols = [c for c in ["Avg", "Max", "Min"] if c in df.columns]

        # Calculate column widths to fit within available width
        elem_w = 36
        story_w = 36
        hinge_w = 28
        summary_w = 30  # For Avg, Max, Min columns
        num_summary = len(summary_cols)

        # Calculate load case column width - ensure everything fits within width
        fixed_cols_w = elem_w + story_w + hinge_w + (summary_w * num_summary)
        remaining_w = width - fixed_cols_w
        lc_w = max(24, remaining_w // num_load_cases) if num_load_cases > 0 else 24

        # Recalculate actual table width used
        actual_table_w = fixed_cols_w + (lc_w * num_load_cases)

        # Header
        painter.fillRect(x, y, width, header_h, QColor(PRINT_COLORS["header_bg"]))
        painter.setPen(QColor(PRINT_COLORS["text"]))
        painter.setFont(QFont("Segoe UI", 5, QFont.Weight.DemiBold))

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
        painter.setFont(QFont("Segoe UI", 5))
        for row_i in range(max_rows):
            ry = y + header_h + row_i * row_h

            if row_i % 2 == 1:
                painter.fillRect(x, ry, width, row_h, QColor(PRINT_COLORS["row_alt"]))

            painter.setPen(QColor(PRINT_COLORS["text"]))
            cx = x

            # Element name
            elem_name = str(df["Frame/Wall"].iloc[row_i])[:5] if "Frame/Wall" in df.columns else ""
            painter.drawText(cx, ry, elem_w, row_h, Qt.AlignmentFlag.AlignCenter, elem_name)
            cx += elem_w

            # Story
            story = str(df["Story"].iloc[row_i])[:5] if "Story" in df.columns else ""
            painter.drawText(cx, ry, story_w, row_h, Qt.AlignmentFlag.AlignCenter, story)
            cx += story_w

            # Hinge
            hinge = str(df["Hinge"].iloc[row_i])[:4] if "Hinge" in df.columns else ""
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

            # Summary columns
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
        for _ in range(num_summary - 1):  # -1 because last line is the border
            cx += summary_w
            painter.drawLine(cx, y, cx, y + total_h)

        # Horizontal lines
        for i in range(max_rows + 1):
            ly = y + header_h + i * row_h
            painter.drawLine(x, ly, x + actual_table_w, ly)

        return total_h

    def _draw_beam_rotations_plot(self, painter: QPainter, x: int, y: int, width: int, height: int, plot_data_max: list, plot_data_min: list, stories: list = None) -> None:
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
            self._draw_placeholder(painter, x, y, width, height, "No rotation values")
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
            painter.drawText(x + 4, py - 5, left_m - 8, 10,
                           Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, label)

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
            painter.drawText(px - 15, plot_y + plot_h + 2, 30, 10,
                           Qt.AlignmentFlag.AlignCenter, label)

        # X-axis label
        painter.setFont(QFont("Segoe UI", 6, QFont.Weight.DemiBold))
        painter.drawText(plot_x, plot_y + plot_h + 12, plot_w, 12,
                        Qt.AlignmentFlag.AlignCenter, "Beam Rotation [%]")

    def _draw_column_rotations_section(self, painter: QPainter, x: int, y: int, width: int, available_height: int, section) -> None:
        """Draw column rotations section with top 10 table and scatter plot of all data."""
        element_data = section.element_data
        top_10_df = element_data["top_10"]
        load_cases = element_data["load_cases"]
        stories = element_data.get("stories", [])
        plot_data_max = element_data.get("plot_data_max", [])
        plot_data_min = element_data.get("plot_data_min", [])

        # Table for top 10 elements (by absolute average)
        table_h = self._draw_column_rotations_table(painter, x, y, width, top_10_df, load_cases)
        current_y = y + table_h + 8

        # Plot for all data (scatter) - pass both Max and Min data separately
        remaining = available_height - table_h - 12
        if remaining > 60:
            self._draw_column_rotations_plot(painter, x, current_y, width, remaining, plot_data_max, plot_data_min, stories)

    def _draw_column_rotations_table(self, painter: QPainter, x: int, y: int, width: int, df, load_cases: list) -> int:
        """Draw column rotations table showing top 10 elements by absolute average.

        Returns height used.
        """
        row_h = 14
        header_h = 16
        max_rows = min(len(df), 10)

        if max_rows == 0:
            return 0

        # Columns: Column | Story | Dir | ALL Load Cases | Avg | Max | Min
        displayed_load_cases = load_cases
        num_load_cases = len(displayed_load_cases)

        # Determine which summary columns are present
        summary_cols = [c for c in ["Avg", "Max", "Min"] if c in df.columns]

        # Calculate column widths to fit within available width
        col_w = 36
        story_w = 36
        dir_w = 22
        summary_w = 30  # For Avg, Max, Min columns
        num_summary = len(summary_cols)

        # Calculate load case column width - ensure everything fits within width
        fixed_cols_w = col_w + story_w + dir_w + (summary_w * num_summary)
        remaining_w = width - fixed_cols_w
        lc_w = max(24, remaining_w // num_load_cases) if num_load_cases > 0 else 24

        # Recalculate actual table width used
        actual_table_w = fixed_cols_w + (lc_w * num_load_cases)

        # Header
        painter.fillRect(x, y, width, header_h, QColor(PRINT_COLORS["header_bg"]))
        painter.setPen(QColor(PRINT_COLORS["text"]))
        painter.setFont(QFont("Segoe UI", 5, QFont.Weight.DemiBold))

        cx = x
        painter.drawText(cx, y, col_w, header_h, Qt.AlignmentFlag.AlignCenter, "Column")
        cx += col_w
        painter.drawText(cx, y, story_w, header_h, Qt.AlignmentFlag.AlignCenter, "Story")
        cx += story_w
        painter.drawText(cx, y, dir_w, header_h, Qt.AlignmentFlag.AlignCenter, "Dir")
        cx += dir_w
        for lc in displayed_load_cases:
            label = str(lc)[:4]  # Truncate to 4 chars
            painter.drawText(cx, y, lc_w, header_h, Qt.AlignmentFlag.AlignCenter, label)
            cx += lc_w

            cx += lc_w

        # Draw dynamic summary columns
        for col in summary_cols:
            painter.drawText(cx, y, summary_w, header_h, Qt.AlignmentFlag.AlignCenter, col)
            cx += summary_w

        # Rows
        painter.setFont(QFont("Segoe UI", 5))
        for row_i in range(max_rows):
            ry = y + header_h + row_i * row_h

            if row_i % 2 == 1:
                painter.fillRect(x, ry, width, row_h, QColor(PRINT_COLORS["row_alt"]))

            painter.setPen(QColor(PRINT_COLORS["text"]))
            cx = x

            # Column name
            col_name = str(df["Column"].iloc[row_i])[:5] if "Column" in df.columns else ""
            painter.drawText(cx, ry, col_w, row_h, Qt.AlignmentFlag.AlignCenter, col_name)
            cx += col_w

            # Story
            story = str(df["Story"].iloc[row_i])[:5] if "Story" in df.columns else ""
            painter.drawText(cx, ry, story_w, row_h, Qt.AlignmentFlag.AlignCenter, story)
            cx += story_w

            # Direction (R2/R3)
            direction = str(df["Dir"].iloc[row_i])[:3] if "Dir" in df.columns else ""
            painter.drawText(cx, ry, dir_w, row_h, Qt.AlignmentFlag.AlignCenter, direction)
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

            # Summary columns
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
        cx = x + col_w
        painter.drawLine(cx, y, cx, y + total_h)
        cx += story_w
        painter.drawLine(cx, y, cx, y + total_h)
        cx += dir_w
        painter.drawLine(cx, y, cx, y + total_h)
        for _ in displayed_load_cases:
            cx += lc_w
            painter.drawLine(cx, y, cx, y + total_h)
        # Summary column separators
        for _ in range(num_summary - 1):  # -1 because last line is the border
            cx += summary_w
            painter.drawLine(cx, y, cx, y + total_h)

        # Horizontal lines
        for i in range(max_rows + 1):
            ly = y + header_h + i * row_h
            painter.drawLine(x, ly, x + actual_table_w, ly)

        return total_h

    def _draw_column_rotations_plot(self, painter: QPainter, x: int, y: int, width: int, height: int, plot_data_max: list, plot_data_min: list, stories: list = None) -> None:
        """Draw scatter plot showing all column rotation values (both Max and Min).

        Plot orientation matches the app:
        - Y-axis: Story (bottom floors at bottom, top floors at top)
        - X-axis: Rotation [%] (centered around 0)
        - Single blue color for all markers (suitable for light page background)
        """
        if not plot_data_max and not plot_data_min:
            self._draw_placeholder(painter, x, y, width, height, "No column data")
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
            self._draw_placeholder(painter, x, y, width, height, "No rotation values")
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
            painter.drawText(x + 4, py - 5, left_m - 8, 10,
                           Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, label)

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
            painter.drawText(px - 15, plot_y + plot_h + 2, 30, 10,
                           Qt.AlignmentFlag.AlignCenter, label)

        # X-axis label
        painter.setFont(QFont("Segoe UI", 6, QFont.Weight.DemiBold))
        painter.drawText(plot_x, plot_y + plot_h + 12, plot_w, 12,
                        Qt.AlignmentFlag.AlignCenter, "Column Rotation [%]")

    def _draw_soil_pressures_section(self, painter: QPainter, x: int, y: int, width: int, available_height: int, section) -> None:
        """Draw soil pressures section with top 10 table and scatter plot."""
        joint_data = section.joint_data
        top_10_df = joint_data["top_10"]
        load_cases = joint_data["load_cases"]
        plot_data = joint_data.get("plot_data", [])

        # Table for top 10 elements (by absolute average)
        table_h = self._draw_soil_pressures_table(painter, x, y, width, top_10_df, load_cases)
        current_y = y + table_h + 8

        # Plot for all data (scatter)
        remaining = available_height - table_h - 12
        if remaining > 60:
            self._draw_soil_pressures_plot(painter, x, current_y, width, remaining, plot_data, load_cases)

    def _draw_soil_pressures_table(self, painter: QPainter, x: int, y: int, width: int, df, load_cases: list) -> int:
        """Draw soil pressures table showing top 10 elements by absolute average.

        Returns height used.
        """
        row_h = 14
        header_h = 16
        max_rows = min(len(df), 10)

        if max_rows == 0:
            return 0

        # Columns: Shell Object | Unique Name | Load Cases | Avg | Max | Min
        displayed_load_cases = load_cases
        num_load_cases = len(displayed_load_cases)

        # Determine which summary columns are present
        summary_cols = [c for c in ["Avg", "Max", "Min"] if c in df.columns]

        # Calculate column widths
        shell_w = 42
        name_w = 42
        summary_w = 32  # For Avg, Max, Min columns
        num_summary = len(summary_cols)

        # Calculate load case column width
        fixed_cols_w = shell_w + name_w + (summary_w * num_summary)
        remaining_w = width - fixed_cols_w
        lc_w = max(26, remaining_w // num_load_cases) if num_load_cases > 0 else 26

        # Recalculate actual table width used
        actual_table_w = fixed_cols_w + (lc_w * num_load_cases)

        # Header
        painter.fillRect(x, y, width, header_h, QColor(PRINT_COLORS["header_bg"]))
        painter.setPen(QColor(PRINT_COLORS["text"]))
        painter.setFont(QFont("Segoe UI", 5, QFont.Weight.DemiBold))

        cx = x
        painter.drawText(cx, y, shell_w, header_h, Qt.AlignmentFlag.AlignCenter, "Shell")
        cx += shell_w
        painter.drawText(cx, y, name_w, header_h, Qt.AlignmentFlag.AlignCenter, "Name")
        cx += name_w
        for lc in displayed_load_cases:
            label = str(lc)[:4]  # Truncate to 4 chars
            painter.drawText(cx, y, lc_w, header_h, Qt.AlignmentFlag.AlignCenter, label)
            cx += lc_w
            
        # Draw dynamic summary columns
        for col in summary_cols:
            painter.drawText(cx, y, summary_w, header_h, Qt.AlignmentFlag.AlignCenter, col)
            cx += summary_w

        # Rows
        painter.setFont(QFont("Segoe UI", 5))
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
                    txt = f"{abs(val):.0f}"  # Show absolute, no decimals for kN/m²
                painter.drawText(cx, ry, lc_w, row_h, Qt.AlignmentFlag.AlignCenter, txt)
                cx += lc_w

            # Summary columns
            for col in summary_cols:
                val = df[col].iloc[row_i] if col in df.columns else 0
                if pd.isna(val):
                    txt = "-"
                else:
                    txt = f"{abs(val):.0f}"  # Show absolute
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
        cx = x + shell_w + name_w + (lc_w * num_load_cases)
        for _ in range(num_summary):
             cx += summary_w
             if cx < x + actual_table_w:
                painter.drawLine(cx, y, cx, y + total_h)

        # Horizontal lines
        for i in range(max_rows + 1):
            ly = y + header_h + i * row_h
            painter.drawLine(x, ly, x + actual_table_w, ly)

        return total_h

    def _draw_soil_pressures_plot(self, painter: QPainter, x: int, y: int, width: int, height: int, plot_data: list, load_cases: list) -> None:
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
            self._draw_placeholder(painter, x, y, width, height, "No pressure values")
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
            painter.drawText(x + 8, py - 5, left_m - 12, 10,
                           Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, label)

        # Y-axis label
        painter.save()
        painter.setFont(QFont("Segoe UI", 6, QFont.Weight.DemiBold))
        painter.setPen(QColor(PRINT_COLORS["text"]))
        painter.translate(x + 2, plot_y + plot_h // 2)
        painter.rotate(-90)
        painter.drawText(-35, 0, 70, 10, Qt.AlignmentFlag.AlignCenter, "Pressure (kN/m²)")
        painter.restore()

        # X-axis labels (load case names)
        painter.setFont(QFont("Segoe UI", 5))
        for i, lc in enumerate(load_cases):
            px = int(to_px_x(i))
            label = str(lc)[:4]
            painter.drawText(px - 15, plot_y + plot_h + 2, 30, 10,
                           Qt.AlignmentFlag.AlignCenter, label)

        # X-axis label
        painter.setFont(QFont("Segoe UI", 6, QFont.Weight.DemiBold))
        painter.drawText(plot_x, plot_y + plot_h + 12, plot_w, 12,
                        Qt.AlignmentFlag.AlignCenter, "Load Case")

    def _draw_footer(self, painter: QPainter, x: int, y: int, width: int) -> None:
        painter.setPen(QColor(PRINT_COLORS["text_muted"]))
        painter.setFont(QFont("Segoe UI", 7))
        painter.drawText(x, y, width, FOOTER_HEIGHT,
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, f"Page {self.page_number}")


class ReportPreviewWidget(QScrollArea):
    """Scrollable container for A4 page previews."""

    def __init__(self, project_name: str, parent=None):
        super().__init__(parent)
        self.project_name = project_name
        self._pages: List[ReportPageWidget] = []

        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setStyleSheet(f"""
            QScrollArea {{
                background-color: {COLORS['card']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
            }}
        """)

        self._container = QWidget()
        self._container.setStyleSheet(f"background-color: {COLORS['card']};")
        self._layout = QVBoxLayout(self._container)
        self._layout.setContentsMargins(20, 20, 20, 20)
        self._layout.setSpacing(20)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)

        self.setWidget(self._container)
        self._show_empty_state()

    def _show_empty_state(self) -> None:
        self._clear_pages()
        label = QLabel("Select sections from the tree to preview")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet(f"color: {COLORS['muted']}; font-size: 14px; padding: 40px;")
        self._layout.addWidget(label)

    def _clear_pages(self) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._pages.clear()

    def set_sections(self, sections: list) -> None:
        self._clear_pages()

        if not sections:
            self._show_empty_state()
            return

        # Distribute sections across pages
        max_height = ReportPageWidget.get_content_height()
        current_sections = []
        current_h = 0
        page_num = 1

        for section in sections:
            section_h = ReportPageWidget.estimate_section_height(section)

            if current_h + section_h > max_height and current_sections:
                page = ReportPageWidget(self.project_name, page_number=page_num)
                page.set_sections(current_sections)
                self._layout.addWidget(page)
                self._pages.append(page)
                page_num += 1
                current_sections = []
                current_h = 0

            current_sections.append(section)
            current_h += section_h + SECTION_GAP

        if current_sections:
            page = ReportPageWidget(self.project_name, page_number=page_num)
            page.set_sections(current_sections)
            self._layout.addWidget(page)
            self._pages.append(page)

        self._layout.addStretch()

    def clear_preview(self) -> None:
        self._clear_pages()
        self._show_empty_state()
