"""Helpers to build tables for beam rotations and foundation results."""

from __future__ import annotations

from typing import List, Sequence

import pandas as pd
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem

from utils.color_utils import get_gradient_color


def apply_headers(table: QTableWidget, column_names: Sequence[str]) -> None:
    table.setColumnCount(len(column_names))
    table.setHorizontalHeaderLabels(list(column_names))


def populate_beam_rotations_table(table: QTableWidget, df: pd.DataFrame, color_scheme: str) -> None:
    fixed_cols = ['Story', 'Frame/Wall', 'Unique Name', 'Hinge', 'Generated Hinge', 'Rel Dist']
    summary_cols = ['Avg', 'Max', 'Min']
    load_case_cols = [col for col in df.columns if col not in fixed_cols and col not in summary_cols]

    numeric_cols = load_case_cols + summary_cols
    all_numeric_values = []
    for col in numeric_cols:
        if col in df.columns:
            all_numeric_values.extend(df[col].dropna().tolist())

    min_val = min(all_numeric_values) if all_numeric_values else 0
    max_val = max(all_numeric_values) if all_numeric_values else 0

    table.setRowCount(len(df))
    table.setColumnCount(len(df.columns))

    for row_idx, (_, row) in enumerate(df.iterrows()):
        for col_idx, col_name in enumerate(df.columns):
            value = row[col_name]

            if col_name in fixed_cols:
                if col_name == 'Rel Dist':
                    item_text = f"{value:.2f}" if value is not None else ""
                else:
                    item_text = str(value) if value is not None else ""
            elif col_name in load_case_cols or col_name in summary_cols:
                if value is not None and not pd.isna(value):
                    item_text = f"{value:.2f}%"
                else:
                    item_text = ""
            else:
                item_text = str(value) if value is not None else ""

            item = QTableWidgetItem(item_text)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            if col_name in load_case_cols or col_name in summary_cols:
                if value is not None and not pd.isna(value):
                    color = get_gradient_color(value, min_val, max_val, color_scheme)
                    item.setForeground(color)
                    item._original_color = QColor(color)
                else:
                    default_color = QColor("#9ca3af")
                    item.setForeground(default_color)
                    item._original_color = QColor(default_color)
            else:
                default_color = QColor("#d1d5db")
                item.setForeground(default_color)
                item._original_color = QColor(default_color)

            table.setItem(row_idx, col_idx, item)

    table.resizeColumnsToContents()


def populate_foundation_table(
    table: QTableWidget,
    df: pd.DataFrame,
    load_case_cols: List[str],
    summary_cols: List[str],
    color_scheme: str,
) -> None:
    table.setRowCount(len(df))
    table.setColumnCount(len(df.columns))

    all_numeric_values = []
    for col in load_case_cols:
        if col in df.columns:
            all_numeric_values.extend(df[col].dropna().tolist())

    if all_numeric_values:
        global_min = min(all_numeric_values)
        global_max = max(all_numeric_values)
    else:
        global_min = global_max = 0

    for row_idx, (_, row) in enumerate(df.iterrows()):
        for col_idx, col_name in enumerate(df.columns):
            value = row[col_name]

            if (col_name in load_case_cols or col_name in summary_cols) and pd.notna(value):
                formatted_value = f"{value:.2f}"
            else:
                formatted_value = str(value) if pd.notna(value) else ""

            item = QTableWidgetItem(formatted_value)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            if col_name in load_case_cols and pd.notna(value):
                if global_max != global_min:
                    color = get_gradient_color(value, global_min, global_max, color_scheme)
                    item.setForeground(color)
                    item._original_color = QColor(color)
                else:
                    default_color = QColor("#9ca3af")
                    item.setForeground(default_color)
                    item._original_color = QColor(default_color)
            elif col_name in summary_cols and pd.notna(value):
                summary_color = QColor("#a3a3a3")
                item.setForeground(summary_color)
                item._original_color = QColor(summary_color)
            else:
                default_color = QColor("#d1d5db")
                item.setForeground(default_color)
                item._original_color = QColor(default_color)

            table.setItem(row_idx, col_idx, item)

    table.resizeColumnsToContents()
