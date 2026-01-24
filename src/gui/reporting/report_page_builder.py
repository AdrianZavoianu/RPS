"""Page layout and section rendering orchestration for report previews."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QColor, QFont

from .constants import PRINT_COLORS
from .report_header_footer import ReportHeaderFooter
from .report_layout import (
    A4_HEIGHT_PX,
    A4_WIDTH_PX,
    FOOTER_HEIGHT,
    HEADER_HEIGHT,
    PAGE_MARGIN,
    SECTION_GAP,
)
from .report_plot_renderer import ReportPlotRenderer
from .report_table_renderer import ReportTableRenderer


class ReportPageBuilder:
    """Handles page layout, section positioning, and delegating rendering."""

    def __init__(
        self,
        header_footer: ReportHeaderFooter,
        table_renderer: ReportTableRenderer,
        plot_renderer: ReportPlotRenderer,
    ) -> None:
        self._header_footer = header_footer
        self._table_renderer = table_renderer
        self._plot_renderer = plot_renderer

    @staticmethod
    def estimate_section_height(section, available_width: int = 485) -> int:
        """Estimate height for a section."""
        height = 20  # Title

        # Check for element results (beam/column rotations)
        if section.category == "Element" and hasattr(section, "element_data") and section.element_data is not None:
            # Table: top 10 rows
            rows = min(len(section.element_data.get("top_10", [])), 10)
            height += 16 + rows * 14 + 8  # header + rows + gap
            # Plot
            height += 150
            return height

        # Check for joint results (soil pressures)
        if section.category == "Joint" and hasattr(section, "joint_data") and section.joint_data is not None:
            # Table: top 10 rows
            rows = min(len(section.joint_data.get("top_10", [])), 10)
            height += 16 + rows * 14 + 8  # header + rows + gap
            # Plot
            height += 150
            return height

        # Standard global results
        # Table
        if hasattr(section, "dataset") and section.dataset is not None:
            df = section.dataset.data
            if df is not None and not df.empty:
                rows = min(len(df), 20)
                height += 18 + rows * 14 + 4

        # Plot - use remaining space, minimum 200px
        height += 200
        return height

    @staticmethod
    def get_content_height() -> int:
        """Available content height."""
        return A4_HEIGHT_PX - 2 * PAGE_MARGIN - HEADER_HEIGHT - FOOTER_HEIGHT - 10

    def draw_page(self, painter: QPainter, sections: list, project_name: str, page_number: int) -> None:
        """Draw the full page with header, sections, and footer."""
        content_x = PAGE_MARGIN
        content_width = A4_WIDTH_PX - 2 * PAGE_MARGIN
        content_top = PAGE_MARGIN + HEADER_HEIGHT + 4
        content_bottom = A4_HEIGHT_PX - PAGE_MARGIN - FOOTER_HEIGHT

        # Header
        self._header_footer.draw_header(painter, content_x, PAGE_MARGIN, content_width, project_name)

        # Calculate available height for sections
        available_height = content_bottom - content_top
        num_sections = len(sections)

        if num_sections > 0:
            # Distribute space evenly among sections
            section_height = (available_height - (num_sections - 1) * SECTION_GAP) // num_sections
            y = content_top

            for section in sections:
                self._draw_section(painter, content_x, y, content_width, section_height, section)
                y += section_height + SECTION_GAP

        # Footer
        self._header_footer.draw_footer(
            painter,
            content_x,
            A4_HEIGHT_PX - PAGE_MARGIN - FOOTER_HEIGHT,
            content_width,
            page_number,
        )

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
        if section.category == "Element" and hasattr(section, "element_data") and section.element_data is not None:
            if section.result_type == "BeamRotations":
                self._draw_beam_rotations_section(
                    painter, x, current_y, width, total_height - title_h - title_gap, section
                )
            elif section.result_type == "ColumnRotations":
                self._draw_column_rotations_section(
                    painter, x, current_y, width, total_height - title_h - title_gap, section
                )
            return

        # Check if this is a joint section (Soil Pressures)
        if section.category == "Joint" and hasattr(section, "joint_data") and section.joint_data is not None:
            if section.result_type == "SoilPressures_Min":
                self._draw_soil_pressures_section(
                    painter, x, current_y, width, total_height - title_h - title_gap, section
                )
            return

        # Standard global results section
        # Check if this is Pushover analysis
        is_pushover = getattr(section, "analysis_context", "NLTHA") == "Pushover"

        # Table
        table_h = 0
        if hasattr(section, "dataset") and section.dataset is not None and section.dataset.data is not None:
            df = section.dataset.data
            if not df.empty:
                table_h = self._table_renderer.draw_table(painter, x, current_y, width, section.dataset, is_pushover)
                current_y += table_h + 4

        # Plot fills remaining space
        remaining = total_height - title_h - title_gap - table_h - 8
        if remaining > 50:
            self._plot_renderer.draw_plot(painter, x, current_y, width, remaining, section, is_pushover)

    def _draw_beam_rotations_section(
        self,
        painter: QPainter,
        x: int,
        y: int,
        width: int,
        available_height: int,
        section,
    ) -> None:
        """Draw beam rotations section with top 10 table and scatter plot of all data."""
        element_data = section.element_data
        top_10_df = element_data["top_10"]
        load_cases = element_data["load_cases"]
        stories = element_data.get("stories", [])
        plot_data_max = element_data.get("plot_data_max", [])
        plot_data_min = element_data.get("plot_data_min", [])

        # Table for top 10 elements (by absolute average)
        table_h = self._table_renderer.draw_beam_rotations_table(painter, x, y, width, top_10_df, load_cases)
        current_y = y + table_h + 8

        # Plot for all data (scatter) - pass both Max and Min data separately
        remaining = available_height - table_h - 12
        if remaining > 60:
            self._plot_renderer.draw_beam_rotations_plot(
                painter, x, current_y, width, remaining, plot_data_max, plot_data_min, stories
            )

    def _draw_column_rotations_section(
        self,
        painter: QPainter,
        x: int,
        y: int,
        width: int,
        available_height: int,
        section,
    ) -> None:
        """Draw column rotations section with top 10 table and scatter plot of all data."""
        element_data = section.element_data
        top_10_df = element_data["top_10"]
        load_cases = element_data["load_cases"]
        stories = element_data.get("stories", [])
        plot_data_max = element_data.get("plot_data_max", [])
        plot_data_min = element_data.get("plot_data_min", [])

        # Table for top 10 elements (by absolute average)
        table_h = self._table_renderer.draw_column_rotations_table(painter, x, y, width, top_10_df, load_cases)
        current_y = y + table_h + 8

        # Plot for all data (scatter) - pass both Max and Min data separately
        remaining = available_height - table_h - 12
        if remaining > 60:
            self._plot_renderer.draw_column_rotations_plot(
                painter, x, current_y, width, remaining, plot_data_max, plot_data_min, stories
            )

    def _draw_soil_pressures_section(
        self,
        painter: QPainter,
        x: int,
        y: int,
        width: int,
        available_height: int,
        section,
    ) -> None:
        """Draw soil pressures section with top 10 table and scatter plot."""
        joint_data = section.joint_data
        top_10_df = joint_data["top_10"]
        load_cases = joint_data["load_cases"]
        plot_data = joint_data.get("plot_data", [])

        # Table for top 10 elements (by absolute average)
        table_h = self._table_renderer.draw_soil_pressures_table(painter, x, y, width, top_10_df, load_cases)
        current_y = y + table_h + 8

        # Plot for all data (scatter)
        remaining = available_height - table_h - 12
        if remaining > 60:
            self._plot_renderer.draw_soil_pressures_plot(painter, x, current_y, width, remaining, plot_data, load_cases)
