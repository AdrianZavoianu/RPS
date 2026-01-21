"""Reusable GUI components for RPS."""

from .export_selectors import ResultSetSelector, ResultTypeSelector
from .legend import InteractiveLegendItem
from .results_table_header import ClickableTableWidget, SelectableHeaderView
from .import_dialog_base import (
    ImportDialogBase,
    BaseImportWorker,
    create_checkbox_icons,
)
from .plot_factory import (
    create_plot_widget,
    configure_building_profile,
    configure_scatter_plot,
    configure_time_series,
    create_building_profile_plot,
    create_element_scatter_plot,
    set_plot_range,
    clear_plot,
    PLOT_COLORS,
)

__all__ = [
    "ResultSetSelector",
    "ResultTypeSelector",
    "InteractiveLegendItem",
    "ClickableTableWidget",
    "SelectableHeaderView",
    "ImportDialogBase",
    "BaseImportWorker",
    "create_checkbox_icons",
    # Plot factory
    "create_plot_widget",
    "configure_building_profile",
    "configure_scatter_plot",
    "configure_time_series",
    "create_building_profile_plot",
    "create_element_scatter_plot",
    "set_plot_range",
    "clear_plot",
    "PLOT_COLORS",
]
