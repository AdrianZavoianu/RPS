"""PDF generator using PyQt6's QPrinter."""

from __future__ import annotations

from typing import List, Optional
from pathlib import Path
import logging

import numpy as np
import pandas as pd
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QRectF, QMarginsF, QSizeF
from PyQt6.QtGui import (
    QPainter,
    QColor,
    QFont,
    QPen,
    QPixmap,
    QImage,
    QPageSize,
    QPageLayout,
)
from PyQt6.QtPrintSupport import QPrinter, QPrintDialog

from gui.icon_utils import ICONS_DIR
from .constants import PRINT_COLORS, PLOT_COLORS, AVERAGE_COLOR
from .pdf_section_drawers import PushoverSectionDrawer

logger = logging.getLogger(__name__)


# A4 dimensions in mm
A4_WIDTH_MM = 210
A4_HEIGHT_MM = 297

# Page margins in mm
PAGE_MARGIN_MM = 15
HEADER_HEIGHT_MM = 9
FOOTER_HEIGHT_MM = 10
SECTION_SPACING_MM = 4


class PDFGenerator:
    """Generate PDF reports using QPrinter.

    Renders report sections with:
    - Page header (logo + project name)
    - Section titles
    - Data tables
    - Building profile plots
    - Page numbers
    """

    def __init__(self, project_name: str):
        self.project_name = project_name
        self._logo_pixmap = self._load_colorized_logo()
        self._section_drawer = PushoverSectionDrawer(self._draw_placeholder)

    def _load_colorized_logo(self) -> QPixmap:
        """Load logo mask and colorize it for print."""
        logo_path = ICONS_DIR / "RPS_Logo.png"
        if not logo_path.exists():
            return QPixmap()

        image = QImage(str(logo_path))
        if image.isNull():
            return QPixmap()

        # Use dark teal color for print
        logo_color = QColor("#1f5c6a")
        image = image.convertToFormat(QImage.Format.Format_ARGB32)

        for y in range(image.height()):
            for x in range(image.width()):
                pixel = image.pixelColor(x, y)
                if pixel.alpha() > 0:
                    new_color = QColor(logo_color)
                    new_color.setAlpha(pixel.alpha())
                    image.setPixelColor(x, y, new_color)

        return QPixmap.fromImage(image)

    def generate(self, sections: list, output_path: str) -> None:
        """Generate PDF file from sections."""
        printer = self._setup_printer(output_path)

        painter = QPainter()
        if not painter.begin(printer):
            raise RuntimeError("Failed to initialize PDF painter")

        try:
            self._render_pages(painter, printer, sections)
        finally:
            painter.end()

    def show_print_dialog(self, sections: list, parent: QWidget) -> bool:
        """Show print dialog and print sections."""
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        printer.setPageOrientation(QPageLayout.Orientation.Portrait)

        dialog = QPrintDialog(printer, parent)
        dialog.setWindowTitle("Print Report")

        if dialog.exec() != QPrintDialog.DialogCode.Accepted:
            return False

        painter = QPainter()
        if not painter.begin(printer):
            return False

        try:
            self._render_pages(painter, printer, sections)
        finally:
            painter.end()

        return True

    def _setup_printer(self, output_path: str) -> QPrinter:
        """Configure QPrinter for PDF output."""
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(output_path)
        printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        printer.setPageOrientation(QPageLayout.Orientation.Portrait)
        printer.setResolution(300)

        # Left, Top, Right, Bottom margins - reduced top margin for tighter header
        margins = QMarginsF(PAGE_MARGIN_MM, 8, PAGE_MARGIN_MM, PAGE_MARGIN_MM)
        printer.setPageMargins(margins, QPageLayout.Unit.Millimeter)

        return printer

    def _render_pages(self, painter: QPainter, printer: QPrinter, sections: list) -> None:
        """Render all sections across pages - one section per page for clarity."""
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        page_rect = printer.pageRect(QPrinter.Unit.DevicePixel)
        page_width = int(page_rect.width())
        page_height = int(page_rect.height())

        dpi = printer.resolution()
        mm_to_px = dpi / 25.4

        header_height = int(HEADER_HEIGHT_MM * mm_to_px)
        footer_height = int(FOOTER_HEIGHT_MM * mm_to_px)

        content_top = header_height + int(1 * mm_to_px)
        content_height = page_height - content_top - footer_height - int(4 * mm_to_px)

        # One section per page for proper sizing
        for page_number, section in enumerate(sections, start=1):
            if page_number > 1:
                printer.newPage()

            self._draw_header(painter, 0, 0, page_width, header_height, mm_to_px)
            self._draw_section(painter, 0, content_top, page_width, content_height, section, mm_to_px)
            self._draw_footer(painter, 0, page_height - footer_height, page_width, footer_height, page_number, mm_to_px)

    def _render_page(self, painter: QPainter, page_width: int, page_height: int,
                    header_height: int, footer_height: int, page_number: int,
                    sections: list, mm_to_px: float) -> None:
        """Render a single page."""
        self._draw_header(painter, 0, 0, page_width, header_height, mm_to_px)

        for y_offset, section_height, section in sections:
            self._draw_section(painter, 0, y_offset, page_width, section_height, section, mm_to_px)

        self._draw_footer(painter, 0, page_height - footer_height, page_width, footer_height, page_number, mm_to_px)

    def _draw_header(self, painter: QPainter, x: int, y: int, width: int, height: int, mm_to_px: float) -> None:
        """Draw page header with logo and project name."""
        logo_h = int(8 * mm_to_px)

        if not self._logo_pixmap.isNull():
            scaled_logo = self._logo_pixmap.scaledToHeight(logo_h, Qt.TransformationMode.SmoothTransformation)
            painter.drawPixmap(x, y, scaled_logo)
            logo_w = scaled_logo.width()
        else:
            logo_w = 0

        painter.setPen(QColor(PRINT_COLORS["text"]))
        font = QFont("Segoe UI", 12)
        painter.setFont(font)

        text_rect = QRectF(x + logo_w + int(3 * mm_to_px), y, width - logo_w - int(3 * mm_to_px), logo_h)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                        self.project_name)

        painter.setPen(QPen(QColor(PRINT_COLORS["grid"]), 1))
        painter.drawLine(x, y + height, x + width, y + height)

    def _draw_section(self, painter: QPainter, x: int, y: int, width: int, total_height: int,
                     section, mm_to_px: float) -> None:
        """Draw a report section with table and plot."""
        # Title
        painter.setPen(QColor(PRINT_COLORS["text"]))
        title_font = QFont("Segoe UI", 11, QFont.Weight.DemiBold)
        painter.setFont(title_font)

        title_h = int(5 * mm_to_px)
        title_gap = int(2 * mm_to_px)
        painter.drawText(x, y, width, title_h,
                        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                        section.title)

        current_y = y + title_h + title_gap
        
        # Check if this is Pushover analysis
        is_pushover = getattr(section, 'analysis_context', 'NLTHA') == 'Pushover'

        # Check if this is an element section (BeamRotations or ColumnRotations)
        if section.category == "Element" and hasattr(section, 'element_data') and section.element_data is not None:
            if section.result_type == "BeamRotations":
                self._section_drawer._draw_beam_rotations_section(
                    painter,
                    x,
                    current_y,
                    width,
                    total_height - title_h - title_gap,
                    section,
                    mm_to_px,
                )
            elif section.result_type == "ColumnRotations":
                self._section_drawer._draw_column_rotations_section(
                    painter,
                    x,
                    current_y,
                    width,
                    total_height - title_h - title_gap,
                    section,
                    mm_to_px,
                )
            return

        # Check if this is a joint section (SoilPressures)
        if section.category == "Joint" and hasattr(section, 'joint_data') and section.joint_data is not None:
            if section.result_type == "SoilPressures_Min":
                self._section_drawer._draw_soil_pressures_section(
                    painter,
                    x,
                    current_y,
                    width,
                    total_height - title_h - title_gap,
                    section,
                    mm_to_px,
                )
            return

        # Standard global results section
        # Table
        table_h = 0
        if hasattr(section, 'dataset') and section.dataset is not None and section.dataset.data is not None:
            df = section.dataset.data
            if not df.empty:
                table_h = self._draw_table(painter, x, current_y, width, section.dataset, mm_to_px, is_pushover)
                current_y += table_h + int(2 * mm_to_px)

        # Plot fills remaining space
        remaining = total_height - title_h - title_gap - table_h - int(4 * mm_to_px)
        if remaining > int(20 * mm_to_px):
            self._draw_plot(painter, x, current_y, width, remaining, section, mm_to_px, is_pushover)

    def _draw_table(self, painter: QPainter, x: int, y: int, width: int,
                   dataset, mm_to_px: float, is_pushover: bool = False) -> int:
        """Draw data table. Returns height used."""
        df = dataset.data
        config = dataset.config
        decimals = getattr(config, 'decimal_places', 3)

        row_h = int(4 * mm_to_px)
        header_h = int(5 * mm_to_px)
        max_rows = min(len(df), 20)

        # Exclude Avg for Pushover analysis
        if is_pushover:
            summary = [c for c in df.columns if c in {'Max', 'Min'}]
        else:
            summary = [c for c in df.columns if c in {'Avg', 'Max', 'Min'}]
        load_cases = [c for c in df.columns if c not in {'Story', 'Avg', 'Max', 'Min', 'Average', 'Maximum', 'Minimum'}]
        data_cols = load_cases[:11] + summary[:3]

        if not data_cols:
            return 0

        story_w = int(12 * mm_to_px)
        col_w = (width - story_w) // len(data_cols)

        # Header
        painter.fillRect(x, y, width, header_h, QColor(PRINT_COLORS["header_bg"]))
        painter.setPen(QColor(PRINT_COLORS["text"]))
        painter.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))

        painter.drawText(x, y, story_w, header_h, Qt.AlignmentFlag.AlignCenter, "Story")
        for i, col in enumerate(data_cols):
            cx = x + story_w + i * col_w
            label = str(col)[:6]
            painter.drawText(cx, y, col_w, header_h, Qt.AlignmentFlag.AlignCenter, label)

        # Rows
        painter.setFont(QFont("Segoe UI", 8))
        for row_i in range(max_rows):
            ry = y + header_h + row_i * row_h

            if row_i % 2 == 1:
                painter.fillRect(x, ry, width, row_h, QColor(PRINT_COLORS["row_alt"]))

            story = str(df['Story'].iloc[row_i])[:8] if 'Story' in df.columns else str(df.index[row_i])[:8]
            painter.setPen(QColor(PRINT_COLORS["text"]))
            painter.drawText(x, ry, story_w, row_h, Qt.AlignmentFlag.AlignCenter, story)

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

    def _draw_plot(self, painter: QPainter, x: int, y: int, width: int, height: int,
                  section, mm_to_px: float, is_pushover: bool = False) -> None:
        """Draw building profile plot."""
        if not hasattr(section, 'dataset') or section.dataset is None:
            self._draw_placeholder(painter, x, y, width, height, section.title)
            return

        df = section.dataset.data
        if df is None or df.empty:
            self._draw_placeholder(painter, x, y, width, height, section.title)
            return

        # Margins
        left_m = int(15 * mm_to_px)
        right_m = int(3 * mm_to_px)
        top_m = int(3 * mm_to_px)
        bottom_m = int(12 * mm_to_px)

        plot_x = x + left_m
        plot_y = y + top_m
        plot_w = width - left_m - right_m
        plot_h = height - top_m - bottom_m

        if plot_w < int(20 * mm_to_px) or plot_h < int(15 * mm_to_px):
            return

        # Plot background
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

        tick_values, x_min, x_max = self._nice_ticks(v_min, v_max)

        def to_px_x(v):
            if x_max == x_min:
                return plot_x + plot_w / 2
            return plot_x + (v - x_min) / (x_max - x_min) * plot_w

        def to_px_y(i):
            return plot_y + plot_h - (i + 0.5) / n_stories * plot_h

        # Grid
        painter.setPen(QPen(QColor(PRINT_COLORS["grid"]), 1, Qt.PenStyle.DotLine))
        for i in range(n_stories):
            py = int(to_px_y(i))
            painter.drawLine(plot_x, py, plot_x + plot_w, py)
        for v in tick_values:
            px = int(to_px_x(v))
            if plot_x <= px <= plot_x + plot_w:
                painter.drawLine(px, plot_y, px, plot_y + plot_h)

        # Lines
        drawn_cols = load_cols[:12]
        line_width = max(1, int(0.4 * mm_to_px))
        for idx, col in enumerate(drawn_cols):
            vals = numeric_df[col].fillna(0).tolist()
            color = QColor(PLOT_COLORS[idx % len(PLOT_COLORS)])
            painter.setPen(QPen(color, line_width))
            for i in range(len(vals) - 1):
                painter.drawLine(int(to_px_x(vals[i])), int(to_px_y(i)),
                               int(to_px_x(vals[i + 1])), int(to_px_y(i + 1)))

        # Draw average line only for NLTHA (not Pushover)
        if not is_pushover:
            avg = numeric_df.mean(axis=1, skipna=True).fillna(0).tolist()
            avg_width = max(3, int(1.0 * mm_to_px))  # Thicker for prominence
            painter.setPen(QPen(QColor(AVERAGE_COLOR), avg_width, Qt.PenStyle.DashLine))
            for i in range(len(avg) - 1):
                painter.drawLine(int(to_px_x(avg[i])), int(to_px_y(i)),
                               int(to_px_x(avg[i + 1])), int(to_px_y(i + 1)))

        # Legend setup
        legend_items = [(col[:6], PLOT_COLORS[i % len(PLOT_COLORS)]) for i, col in enumerate(drawn_cols)]
        # Add Avg to legend only for NLTHA (not Pushover)
        if not is_pushover:
            legend_items.append(("Avg", AVERAGE_COLOR))

        item_w = int(12 * mm_to_px)
        max_cols = min(len(legend_items), plot_w // item_w)
        item_h = int(3 * mm_to_px)
        total_legend_w = max_cols * item_w
        legend_start_x = plot_x + (plot_w - total_legend_w) // 2

        # Axes
        painter.setPen(QPen(QColor(PRINT_COLORS["text"]), 1))
        painter.drawLine(plot_x, plot_y, plot_x, plot_y + plot_h)
        painter.drawLine(plot_x, plot_y + plot_h, plot_x + plot_w, plot_y + plot_h)

        # Y labels (stories)
        painter.setPen(QColor(PRINT_COLORS["text"]))
        painter.setFont(QFont("Segoe UI", 8))
        for i, s in enumerate(stories):
            py = int(to_px_y(i))
            painter.drawText(x + int(3 * mm_to_px), py - int(1.5 * mm_to_px), left_m - int(5 * mm_to_px), int(3 * mm_to_px),
                           Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, str(s)[:8])

        # Y axis label
        painter.save()
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        painter.setPen(QColor(PRINT_COLORS["text"]))
        painter.translate(x + int(1 * mm_to_px), plot_y + plot_h // 2)
        painter.rotate(-90)
        painter.drawText(int(-8 * mm_to_px), 0, int(16 * mm_to_px), int(3 * mm_to_px), Qt.AlignmentFlag.AlignCenter, "Story")
        painter.restore()

        # X tick labels
        painter.setPen(QColor(PRINT_COLORS["text"]))
        painter.setFont(QFont("Segoe UI", 8))
        for v in tick_values:
            px = int(to_px_x(v))
            if plot_x <= px <= plot_x + plot_w:
                if v == int(v):
                    label = f"{int(v)}"
                else:
                    label = f"{v:.2f}"
                painter.drawText(px - int(6 * mm_to_px), plot_y + plot_h + int(0.5 * mm_to_px), int(12 * mm_to_px), int(3 * mm_to_px),
                               Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, label)

        # X axis label (use y_label from config which has units)
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        x_label = getattr(section.dataset.config, 'y_label', None)
        if not x_label:
            unit = getattr(section.dataset.config, 'unit', '')
            x_label = f"{section.result_type} ({unit})" if unit else section.result_type
        painter.drawText(plot_x, plot_y + plot_h + int(3.5 * mm_to_px), plot_w, int(3 * mm_to_px),
                        Qt.AlignmentFlag.AlignCenter, x_label)

        # Legend - below axis name
        legend_y_final = plot_y + plot_h + int(7 * mm_to_px)
        painter.setFont(QFont("Segoe UI", 8))
        for i, (label, color) in enumerate(legend_items):
            row = i // max_cols
            col = i % max_cols
            lx = legend_start_x + col * item_w
            ly = legend_y_final + row * item_h

            painter.setPen(QPen(QColor(color), 2))
            painter.drawLine(lx, ly + int(1 * mm_to_px), lx + int(3 * mm_to_px), ly + int(1 * mm_to_px))

            painter.setPen(QColor(PRINT_COLORS["text"]))
            painter.drawText(lx + int(4 * mm_to_px), ly, item_w - int(4 * mm_to_px), item_h,
                           Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, label)

    def _nice_ticks(self, vmin: float, vmax: float, n_ticks: int = 5):
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
        v = nice_min
        while v <= nice_max + nice_step * 0.01:
            ticks.append(round(v, 10))
            v += nice_step
        return ticks, nice_min, nice_max

    def _draw_placeholder(self, painter: QPainter, x: int, y: int, w: int, h: int, title: str) -> None:
        """Draw placeholder for missing data."""
        painter.fillRect(x, y, w, h, QColor("#f8fafc"))
        painter.setPen(QPen(QColor(PRINT_COLORS["border"]), 1))
        painter.drawRect(x, y, w, h)
        painter.setPen(QColor(PRINT_COLORS["text_muted"]))
        painter.setFont(QFont("Segoe UI", 8))
        painter.drawText(x, y, w, h, Qt.AlignmentFlag.AlignCenter, f"No data\n{title}")

    def _draw_footer(self, painter: QPainter, x: int, y: int, width: int,
                    height: int, page_number: int, mm_to_px: float) -> None:
        """Draw page footer with page number aligned right."""
        painter.setPen(QColor(PRINT_COLORS["text_muted"]))
        font = QFont("Segoe UI", 9)
        painter.setFont(font)
        painter.drawText(x, y, width, height,
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                        f"Page {page_number}")

    def _estimate_section_height(self, section, page_width: int, mm_to_px: float) -> int:
        """Estimate the height needed for a section."""
        title_h = int(5 * mm_to_px)
        title_gap = int(2 * mm_to_px)

        # Check for element results (beam/column rotations)
        if section.category == "Element" and hasattr(section, 'element_data') and section.element_data is not None:
            # Table: top 10 rows
            rows = min(len(section.element_data.get("top_10", [])), 10)
            row_h = int(4 * mm_to_px)
            header_h = int(5 * mm_to_px)
            table_h = header_h + rows * row_h
            # Plot
            plot_h = int(40 * mm_to_px)
            return title_h + title_gap + table_h + int(3 * mm_to_px) + plot_h

        # Check for joint results (soil pressures)
        if section.category == "Joint" and hasattr(section, 'joint_data') and section.joint_data is not None:
            # Table: top 10 rows
            rows = min(len(section.joint_data.get("top_10", [])), 10)
            row_h = int(4 * mm_to_px)
            header_h = int(5 * mm_to_px)
            table_h = header_h + rows * row_h
            # Plot
            plot_h = int(40 * mm_to_px)
            return title_h + title_gap + table_h + int(3 * mm_to_px) + plot_h

        # Standard global results
        # Table height
        table_h = 0
        if hasattr(section, 'dataset') and section.dataset is not None:
            df = section.dataset.data
            if df is not None and not df.empty:
                num_rows = min(len(df), 20)
                row_h = int(4 * mm_to_px)
                header_h = int(5 * mm_to_px)
                table_h = header_h + num_rows * row_h

        # Plot height - minimum 50mm
        plot_h = int(50 * mm_to_px)

        return title_h + title_gap + table_h + int(2 * mm_to_px) + plot_h
