"""Table preparation helpers for max/min results."""

from __future__ import annotations

import math

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QHeaderView, QTableWidgetItem

from utils.color_utils import get_gradient_color
from utils.data_utils import parse_percentage_value

from .maxmin_data_processor import MaxMinDataProcessor


class MaxMinTableBuilder:
    """Builds max/min tables and formatting."""

    def __init__(self, data_processor: MaxMinDataProcessor) -> None:
        self._data = data_processor

    def populate_min_max_tables(
        self,
        min_table,
        max_table,
        df,
        max_cols,
        min_cols,
        story_names,
        direction,
        base_result_type,
        color_scheme: str,
    ) -> None:
        """Populate separate Min and Max tables with color gradients."""
        self.populate_single_table(
            max_table, df, max_cols, story_names, direction, base_result_type, color_scheme, is_max=True
        )
        self.populate_single_table(
            min_table, df, min_cols, story_names, direction, base_result_type, color_scheme, is_max=False
        )

    def populate_axial_combined_table(
        self,
        table,
        df,
        max_cols,
        min_cols,
        story_names,
        base_result_type,
        color_scheme: str,
    ) -> None:
        """Populate a single table with both Max and Min axial values (no X/Y split)."""
        if table is None:
            return

        table.clear()
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Pair load cases that have both Max and Min columns
        pairs = []
        for max_col in sorted(max_cols):
            load_case_full = max_col.replace("Max_", "")
            min_col = f"Min_{load_case_full}"
            if min_col in min_cols:
                parts = load_case_full.split("_")
                load_case = parts[-1] if len(parts) > 1 else load_case_full
                pairs.append((load_case, max_col, min_col))

        if not pairs or not story_names:
            return

        column_count = 1 + len(pairs) * 2 + 1  # Story + (Max/Min per LC) + Avg
        table.setRowCount(len(story_names))
        table.setColumnCount(column_count)

        headers = ["Story"]
        for load_case, _, _ in pairs:
            headers.extend([f"{load_case} Max", f"{load_case} Min"])
        headers.append("Avg")
        table.setHorizontalHeaderLabels(headers)

        # Gradient range based on absolute values
        all_values = []
        for _, max_col, min_col in pairs:
            for idx in range(len(story_names)):
                for col in (max_col, min_col):
                    value = df[col].iloc[idx]
                    if isinstance(value, str):
                        numeric_value = parse_percentage_value(value)
                    else:
                        numeric_value = float(value)
                    all_values.append(abs(numeric_value))

        all_values = [v for v in all_values if v != 0.0]
        if all_values:
            min_val = min(all_values)
            max_val = max(all_values)
        else:
            min_val = max_val = 0

        for row_idx, story_name in enumerate(story_names):
            row_values = []
            story_item = QTableWidgetItem(story_name)
            story_item.setFlags(story_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            story_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            story_color = QColor("#d1d5db")
            story_item.setForeground(story_color)
            story_item._original_color = story_color
            table.setItem(row_idx, 0, story_item)

            for pair_idx, (_, max_col, min_col) in enumerate(pairs):
                for offset, col in enumerate((max_col, min_col)):
                    value = df[col].iloc[row_idx]
                    if isinstance(value, str):
                        numeric_value = parse_percentage_value(value)
                    else:
                        numeric_value = float(value)

                    display_text = self.format_maxmin_number(numeric_value, base_result_type)
                    item = QTableWidgetItem(display_text)
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                    abs_value = abs(numeric_value)
                    if abs_value != 0.0 and min_val != max_val and min_val != 0:
                        color_hex = get_gradient_color(abs_value, min_val, max_val, color_scheme)
                        gradient_color = QColor(color_hex)
                        item.setForeground(gradient_color)
                        item._original_color = gradient_color
                    else:
                        default_color = QColor("#d1d5db")
                        item.setForeground(default_color)
                        item._original_color = default_color

                    table.setItem(row_idx, 1 + pair_idx * 2 + offset, item)
                    row_values.append(numeric_value)

            avg_value = self._data.calculate_row_average(row_values)
            avg_item = self.create_average_item(avg_value, base_result_type)
            table.setItem(row_idx, column_count - 1, avg_item)

        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        for i in range(1, table.columnCount()):
            table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)

        self.resize_table_to_content(table)

    def hide_table_widget(self, table) -> None:
        """Hide a table and its container (used for single-table layouts)."""
        if not table:
            return
        table.setVisible(False)
        parent = table.parent()
        if parent:
            parent.setVisible(False)
            parent.setMaximumWidth(0)
            parent.setMaximumHeight(0)

    def show_table_widget(self, table, label_text: str | None = None) -> None:
        """Show a table and restore its container sizing."""
        if not table:
            return
        table.setVisible(True)
        if label_text in {"Min", "Max"}:
            table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        parent = table.parent()
        if parent:
            parent.setVisible(True)
            parent.setMaximumWidth(16777215)
            parent.setMaximumHeight(16777215)
        if label_text and hasattr(table, "_label_widget"):
            table._label_widget.setText(label_text)

    def populate_single_table(
        self,
        table,
        df,
        cols,
        story_names,
        direction,
        base_result_type: str,
        color_scheme: str,
        is_max: bool,
    ) -> None:
        """Populate a single table (Min or Max) with color gradients on text."""
        table.clear()

        if not cols or not story_names:
            return

        # Set dimensions (Story column + load cases + Avg)
        table.setRowCount(len(story_names))
        table.setColumnCount(len(cols) + 2)

        # Extract load case names
        load_case_names = [self._data.extract_load_case_name(col, direction) for col in cols]

        # Set headers (Story + load case names)
        headers = ["Story"] + load_case_names + ["Avg"]
        table.setHorizontalHeaderLabels(headers)

        # Collect all values for gradient range calculation
        all_values = []
        for col in cols:
            if col in df.columns:
                for idx in range(len(story_names)):
                    value = df[col].iloc[idx]
                    if isinstance(value, str):
                        numeric_value = parse_percentage_value(value)
                    else:
                        numeric_value = float(value)
                    all_values.append(abs(numeric_value))

        all_values = [v for v in all_values if v != 0.0]
        if all_values:
            min_val = min(all_values)
            max_val = max(all_values)
        else:
            min_val, max_val = 0, 0

        # Populate data with color gradients on text
        for row_idx in range(len(story_names)):
            row_values = []
            story_item = QTableWidgetItem(story_names[row_idx])
            story_item.setFlags(story_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            story_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            story_color = QColor("#d1d5db")
            story_item.setForeground(story_color)
            story_item._original_color = story_color
            table.setItem(row_idx, 0, story_item)

            for col_idx, col in enumerate(cols):
                if col in df.columns:
                    value = df[col].iloc[row_idx]
                    if isinstance(value, str):
                        numeric_value = parse_percentage_value(value)
                    else:
                        numeric_value = float(value)

                    display_text = self.format_maxmin_number(numeric_value, base_result_type)
                    item = QTableWidgetItem(display_text)
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                    item.setData(Qt.ItemDataRole.BackgroundRole, None)

                    abs_value = abs(numeric_value)
                    if abs_value != 0.0 and min_val != max_val and min_val != 0:
                        color_hex = get_gradient_color(abs_value, min_val, max_val, color_scheme)
                        gradient_color = QColor(color_hex)
                        item.setForeground(gradient_color)
                        item._original_color = gradient_color
                    else:
                        default_color = QColor("#d1d5db")
                        item.setForeground(default_color)
                        item._original_color = default_color

                    table.setItem(row_idx, col_idx + 1, item)
                    row_values.append(numeric_value)

            avg_value = self._data.calculate_row_average(row_values)
            avg_item = self.create_average_item(avg_value, base_result_type)
            table.setItem(row_idx, len(cols) + 1, avg_item)

        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        for i in range(1, table.columnCount()):
            table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)

        self.resize_table_to_content(table)

    def create_average_item(self, value, base_result_type: str) -> QTableWidgetItem:
        """Create a styled table item for the Average column."""
        item = QTableWidgetItem()
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

        if value is None or (isinstance(value, float) and math.isnan(value)):
            item.setText("-")
        else:
            item.setText(self.format_maxmin_number(value, base_result_type))

        accent = QColor("#ffa500")
        item.setForeground(accent)
        item._original_color = QColor(accent)
        return item

    @staticmethod
    def base_type_decimals(base_type: str) -> int:
        mapping = {
            "Drifts": 2,
            "Accelerations": 2,
            "Forces": 0,
            "Displacements": 0,
            "WallShears": 0,
            "ColumnShears": 0,
            "ColumnAxials": 4,
            "ColumnRotations": 2,
            "QuadRotations": 2,
        }
        return mapping.get(base_type, 2)

    def format_maxmin_number(self, value: float, base_type: str) -> str:
        decimals = self.base_type_decimals(base_type)
        if decimals <= 0:
            text = f"{round(value):.0f}"
        else:
            text = f"{value:.{decimals}f}"
        return text

    @staticmethod
    def resize_table_to_content(table) -> None:
        """Resize table height to show all rows without scrolling."""
        total_height = table.horizontalHeader().height()
        for row in range(table.rowCount()):
            total_height += table.rowHeight(row)
        total_height += 2
        table.setMaximumHeight(total_height)
        table.setMinimumHeight(total_height)
