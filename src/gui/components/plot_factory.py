"""Factory for creating consistent PyQtGraph plots.

Centralizes plot widget creation and configuration to eliminate duplication
across ~11 widget files. All plots use consistent styling based on design tokens.

Usage:
    from gui.components.plot_factory import create_plot_widget, configure_building_profile

    # Create a standard scatter plot
    plot = create_plot_widget()

    # Create a histogram plot
    hist = create_plot_widget(plot_type='histogram')

    # Configure for building profile display
    configure_building_profile(plot, x_label="Drift [%]", y_label="Story")
"""

from __future__ import annotations

from typing import Literal, Optional

import pyqtgraph as pg

from gui.design_tokens import PALETTE


# Plot color constants derived from design tokens
PLOT_COLORS = {
    'background': PALETTE['bg_primary'],           # '#0a0c10'
    'plot_area': '#0f1419',                        # Slightly lighter for plot area
    'grid': 0.5,                                   # Grid alpha
    'axis_line': '#1a1f26',                        # Subtle axis line color
    'axis_text': PALETTE['text_primary'],          # '#d1d5db'
    'border': PALETTE['border_default'],           # '#2c313a'
    'accent': PALETTE['accent_primary'],           # '#4a7d89'
}


def create_plot_widget(
    *,
    plot_type: Literal['standard', 'histogram', 'scatter'] = 'standard',
    interactive: bool = False,
    show_grid: bool = True,
    grid_alpha: float = 0.5,
    show_border: bool = True,
) -> pg.PlotWidget:
    """Create a styled PyQtGraph PlotWidget.

    Args:
        plot_type: Type of plot ('standard', 'histogram', 'scatter')
        interactive: Whether to enable mouse interaction (default: False)
        show_grid: Whether to show grid lines (default: True)
        grid_alpha: Grid line alpha/opacity (default: 0.5)
        show_border: Whether to show plot area border (default: True)

    Returns:
        Configured PlotWidget instance
    """
    plot_widget = pg.PlotWidget()

    # Set outer background
    plot_widget.setBackground(PLOT_COLORS['background'])

    # Configure plot area (ViewBox)
    view_box = plot_widget.getPlotItem().getViewBox()
    view_box.setBackgroundColor(PLOT_COLORS['plot_area'])

    if show_border:
        view_box.setBorder(pg.mkPen(PLOT_COLORS['border'], width=1))
    else:
        view_box.setBorder(None)

    # Configure grid
    if show_grid:
        plot_widget.showGrid(x=True, y=True, alpha=grid_alpha)

    # Configure axis styling
    axis_pen = pg.mkPen(PLOT_COLORS['axis_line'], width=1)
    text_pen = PLOT_COLORS['axis_text']

    plot_widget.getAxis('bottom').setPen(axis_pen)
    plot_widget.getAxis('left').setPen(axis_pen)
    plot_widget.getAxis('bottom').setTextPen(text_pen)
    plot_widget.getAxis('left').setTextPen(text_pen)

    # Configure interactivity
    plot_widget.setMenuEnabled(interactive)
    view_box.setMouseEnabled(x=interactive, y=interactive)
    view_box.setDefaultPadding(0.0)

    # No title by default - maximizes plot area
    plot_widget.setTitle(None)

    return plot_widget


def configure_building_profile(
    plot_widget: pg.PlotWidget,
    *,
    x_label: Optional[str] = None,
    y_label: str = "Story",
    invert_y: bool = False,
) -> None:
    """Configure a plot for building profile display (stories on Y-axis).

    Args:
        plot_widget: PlotWidget to configure
        x_label: Label for X-axis (e.g., "Drift [%]", "Force [kN]")
        y_label: Label for Y-axis (default: "Story")
        invert_y: Whether to invert Y-axis (top-to-bottom, default: False)
    """
    if x_label:
        plot_widget.setLabel('bottom', x_label)

    if y_label:
        plot_widget.setLabel('left', y_label)

    if invert_y:
        plot_widget.getPlotItem().invertY(True)


def configure_scatter_plot(
    plot_widget: pg.PlotWidget,
    *,
    x_label: Optional[str] = None,
    y_label: Optional[str] = None,
) -> None:
    """Configure a plot for scatter/distribution display.

    Args:
        plot_widget: PlotWidget to configure
        x_label: Label for X-axis
        y_label: Label for Y-axis
    """
    if x_label:
        plot_widget.setLabel('bottom', x_label)

    if y_label:
        plot_widget.setLabel('left', y_label)


def configure_time_series(
    plot_widget: pg.PlotWidget,
    *,
    x_label: str = "Time [s]",
    y_label: Optional[str] = None,
    show_crosshair: bool = False,
) -> None:
    """Configure a plot for time series display.

    Args:
        plot_widget: PlotWidget to configure
        x_label: Label for X-axis (default: "Time [s]")
        y_label: Label for Y-axis
        show_crosshair: Whether to enable crosshair (default: False)
    """
    plot_widget.setLabel('bottom', x_label)

    if y_label:
        plot_widget.setLabel('left', y_label)

    if show_crosshair:
        # Enable crosshair for time series navigation
        view_box = plot_widget.getPlotItem().getViewBox()
        view_box.setMouseEnabled(x=True, y=False)


def set_plot_range(
    plot_widget: pg.PlotWidget,
    *,
    x_min: Optional[float] = None,
    x_max: Optional[float] = None,
    y_min: Optional[float] = None,
    y_max: Optional[float] = None,
    padding: float = 0.05,
) -> None:
    """Set the visible range for a plot with optional padding.

    Args:
        plot_widget: PlotWidget to configure
        x_min: Minimum X value (None for auto)
        x_max: Maximum X value (None for auto)
        y_min: Minimum Y value (None for auto)
        y_max: Maximum Y value (None for auto)
        padding: Padding factor (0.05 = 5% padding)
    """
    if x_min is not None and x_max is not None:
        x_range = x_max - x_min
        plot_widget.setXRange(
            x_min - x_range * padding,
            x_max + x_range * padding,
            padding=0
        )

    if y_min is not None and y_max is not None:
        y_range = y_max - y_min
        plot_widget.setYRange(
            y_min - y_range * padding,
            y_max + y_range * padding,
            padding=0
        )


def clear_plot(plot_widget: pg.PlotWidget) -> None:
    """Clear all items from a plot while preserving configuration.

    Args:
        plot_widget: PlotWidget to clear
    """
    plot_widget.clear()


# Convenience function for common pattern: scatter plot with element display
def create_element_scatter_plot() -> pg.PlotWidget:
    """Create a plot configured for element-level scatter visualization."""
    plot = create_plot_widget(plot_type='scatter')
    return plot


# Convenience function for common pattern: building profile plot
def create_building_profile_plot(
    x_label: str,
    y_label: str = "Story"
) -> pg.PlotWidget:
    """Create a plot configured for building profile display.

    Args:
        x_label: Label for the value axis (e.g., "Drift [%]")
        y_label: Label for the story axis (default: "Story")

    Returns:
        Configured PlotWidget
    """
    plot = create_plot_widget()
    configure_building_profile(plot, x_label=x_label, y_label=y_label)
    return plot
