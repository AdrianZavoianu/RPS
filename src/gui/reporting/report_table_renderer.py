"""Table rendering logic for report preview pages."""

from __future__ import annotations

import pandas as pd
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QColor, QFont, QPen

from .constants import PRINT_COLORS


class ReportTableRenderer:
    """Renders tables for report preview sections."""

    def draw_table(self, painter: QPainter, x: int, y: int, width: int, dataset, is_pushover: bool = False) -> int:
        """Draw table, return height used."""
        df = dataset.data
        config = dataset.config
        decimals = getattr(config, "decimal_places", 3)

        row_h = 14
        header_h = 16
        max_rows = min(len(df), 20)

        # Columns - exclude Avg for Pushover analysis
        if is_pushover:
            summary = [c for c in df.columns if c in {"Max", "Min"}]
        else:
            summary = [c for c in df.columns if c in {"Avg", "Max", "Min"}]
        load_cases = [
            c
            for c in df.columns
            if c not in {"Story", "Avg", "Max", "Min", "Average", "Maximum", "Minimum"}
        ]
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
            story = str(df["Story"].iloc[row_i])[:8] if "Story" in df.columns else str(df.index[row_i])[:8]
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

    def draw_beam_rotations_table(self, painter: QPainter, x: int, y: int, width: int, df, load_cases: list) -> int:
        """Draw beam rotations table showing top 10 elements by absolute average.

        Returns height used.
        """
        row_h = 14
        header_h = 16
        max_rows = min(len(df), 10)

        if max_rows == 0:
            return 0

        # Columns: Frame/Wall | Story | Hinge | ALL Load Cases | Avg | Max | Min
        displayed_load_cases = load_cases
        num_load_cases = len(displayed_load_cases)

        # Determine which summary columns are present
        summary_cols = [c for c in ["Avg", "Max", "Min"] if c in df.columns]
        num_summary = len(summary_cols)

        # Calculate column widths to fit within available width
        elem_w = 36
        story_w = 36
        hinge_w = 28
        summary_w = 30  # For Avg, Max, Min columns

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

    def draw_column_rotations_table(self, painter: QPainter, x: int, y: int, width: int, df, load_cases: list) -> int:
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
        num_summary = len(summary_cols)

        # Calculate column widths to fit within available width
        col_w = 36
        story_w = 36
        dir_w = 22
        summary_w = 30  # For Avg, Max, Min columns

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

    def draw_soil_pressures_table(self, painter: QPainter, x: int, y: int, width: int, df, load_cases: list) -> int:
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
        num_summary = len(summary_cols)

        # Calculate column widths
        shell_w = 42
        name_w = 42
        summary_w = 32  # For Avg, Max, Min columns

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
                    txt = f"{abs(val):.0f}"  # Show absolute, no decimals for kN/m^2
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
