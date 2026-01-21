"""GUI helper modules.

This package contains utility modules extracted from large widget files
to improve code organization and reusability.

Modules:
    table_utils: Common table operations (formatting, styling, calculations)
"""

from .table_utils import (
    calculate_row_average,
    compute_average_series,
    resize_table_to_content,
    create_styled_table_item,
    format_number,
    get_decimals_for_result_type,
    apply_row_style,
    apply_alternating_row_colors,
    clear_table,
    hide_table_widget,
    show_table_widget,
)

__all__ = [
    "calculate_row_average",
    "compute_average_series",
    "resize_table_to_content",
    "create_styled_table_item",
    "format_number",
    "get_decimals_for_result_type",
    "apply_row_style",
    "apply_alternating_row_colors",
    "clear_table",
    "hide_table_widget",
    "show_table_widget",
]
