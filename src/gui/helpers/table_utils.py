"""Table utility functions for result widgets.

Extracted from large widget files to improve maintainability.
Provides common table operations used across multiple widgets.
"""

import math
from typing import List, Optional

import pandas as pd
from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor


def calculate_row_average(values: List) -> Optional[float]:
    """Return the mean of valid numeric values, ignoring None/NaN.
    
    Args:
        values: List of numeric values (may contain None/NaN)
        
    Returns:
        Mean of valid values, or None if no valid values
    """
    valid = [
        val for val in values
        if val is not None and not (isinstance(val, float) and math.isnan(val))
    ]
    if not valid:
        return None
    return sum(valid) / len(valid)


def compute_average_series(
    df: pd.DataFrame,
    columns: List[str],
    absolute: bool = False
) -> Optional[pd.Series]:
    """Return a per-row average series for the provided columns.
    
    Args:
        df: DataFrame containing the data
        columns: List of column names to average
        absolute: Whether to use absolute values
        
    Returns:
        Series with per-row averages, or None if no valid data
    """
    if not columns:
        return None

    valid_cols = [col for col in columns if col in df.columns]
    if not valid_cols:
        return None

    numeric_df = df[valid_cols].apply(pd.to_numeric, errors='coerce')
    if numeric_df.empty:
        return None

    if absolute:
        numeric_df = numeric_df.abs()

    avg_series = numeric_df.mean(axis=1, skipna=True)
    if avg_series.isna().all():
        return None

    return avg_series.fillna(0.0)


def resize_table_to_content(table: QTableWidget) -> None:
    """Resize table height to show all rows without scrolling.
    
    Args:
        table: QTableWidget to resize
    """
    total_height = table.horizontalHeader().height()  # Header height

    for row in range(table.rowCount()):
        total_height += table.rowHeight(row)

    # Add some padding for borders
    total_height += 2

    # Set fixed height to show all content
    table.setMaximumHeight(total_height)
    table.setMinimumHeight(total_height)


def create_styled_table_item(
    text: str,
    color: Optional[QColor] = None,
    alignment: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignCenter,
    editable: bool = False,
) -> QTableWidgetItem:
    """Create a styled QTableWidgetItem.
    
    Args:
        text: Text to display
        color: Optional foreground color
        alignment: Text alignment flag
        editable: Whether item is editable
        
    Returns:
        Configured QTableWidgetItem
    """
    item = QTableWidgetItem(text)
    
    if not editable:
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
    
    item.setTextAlignment(alignment)
    
    if color:
        item.setForeground(color)
        item._original_color = QColor(color)  # Store for hover effects
    
    return item


def format_number(
    value: float,
    decimals: int = 4,
    show_sign: bool = False,
) -> str:
    """Format a numeric value for display.
    
    Args:
        value: Value to format
        decimals: Number of decimal places
        show_sign: Whether to show + for positive values
        
    Returns:
        Formatted string
    """
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "-"
    
    fmt = f"{{:+.{decimals}f}}" if show_sign else f"{{:.{decimals}f}}"
    return fmt.format(value)


def get_decimals_for_result_type(base_type: str) -> int:
    """Get the number of decimal places for a result type.
    
    Args:
        base_type: Base result type name
        
    Returns:
        Number of decimal places
    """
    from config.result_config import RESULT_CONFIGS
    
    config = RESULT_CONFIGS.get(base_type)
    if not config:
        return 4
    if isinstance(config, dict):
        return config.get("decimal_places", config.get("decimals", 4))
    return getattr(config, "decimal_places", getattr(config, "decimals", 4))


def apply_row_style(
    table: QTableWidget,
    row: int,
    background_color: QColor,
    text_color: Optional[QColor] = None,
) -> None:
    """Apply consistent styling to a table row.
    
    Args:
        table: QTableWidget to style
        row: Row index
        background_color: Background color
        text_color: Optional text color (preserves existing if not set)
    """
    for col in range(table.columnCount()):
        item = table.item(row, col)
        if item:
            item.setBackground(background_color)
            if text_color:
                item.setForeground(text_color)


def apply_alternating_row_colors(
    table: QTableWidget,
    color1: QColor,
    color2: QColor,
    start_row: int = 0,
) -> None:
    """Apply alternating row colors to a table.
    
    Args:
        table: QTableWidget to style
        color1: Color for even rows
        color2: Color for odd rows
        start_row: Row to start from
    """
    for row in range(start_row, table.rowCount()):
        color = color1 if row % 2 == 0 else color2
        apply_row_style(table, row, color)


def clear_table(table: QTableWidget) -> None:
    """Clear all content from a table while preserving headers.
    
    Args:
        table: QTableWidget to clear
    """
    table.setRowCount(0)
    table.clearContents()


def hide_table_widget(table: QTableWidget) -> None:
    """Hide a table widget properly.
    
    Args:
        table: QTableWidget to hide
    """
    table.hide()
    if hasattr(table, '_label_widget'):
        table._label_widget.hide()


def show_table_widget(table: QTableWidget, label_text: Optional[str] = None) -> None:
    """Show a table widget with optional label update.
    
    Args:
        table: QTableWidget to show
        label_text: Optional text to set on associated label
    """
    table.show()
    if hasattr(table, '_label_widget'):
        if label_text:
            table._label_widget.setText(label_text)
        table._label_widget.show()
