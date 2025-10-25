"""Plot building utilities for PyQtGraph."""

import pyqtgraph as pg
from PyQt6.QtCore import Qt
from config.result_config import ResultTypeConfig


class PlotBuilder:
    """Helper class to build plots with common configuration."""

    def __init__(self, plot_widget: pg.PlotWidget, config: ResultTypeConfig):
        """
        Initialize plot builder.

        Args:
            plot_widget: The PyQtGraph PlotWidget to configure
            config: Result type configuration
        """
        self.plot = plot_widget
        self.config = config

    def setup_axes(self, stories: list[str], x_label: str = None, y_label: str = None):
        """
        Configure axes with story labels and labels.

        Args:
            stories: List of story names for y-axis ticks
            x_label: Label for x-axis (defaults to config.y_label)
            y_label: Label for y-axis (defaults to 'Building Height')
        """
        # Configure y-axis (stories)
        axis = self.plot.getAxis('left')
        story_indices = list(range(len(stories)))
        axis.setTicks([[(i, name) for i, name in enumerate(stories)]])

        # Set labels with larger font
        self.plot.setLabel(
            'left',
            y_label or 'Building Height',
            **{'font-size': '12pt'}
        )
        self.plot.setLabel(
            'bottom',
            x_label or self.config.y_label,
            **{'font-size': '12pt'}
        )

    def set_story_range(self, num_stories: int, padding: float = 0.08):
        """
        Set y-axis range for stories with a compact margin.

        Args:
            num_stories: Number of story labels plotted along Y
            padding: Extra space (in story units) to keep above/below the data
        """
        if num_stories <= 0:
            return

        padding = max(0.0, padding)
        lower = -padding
        upper = (num_stories - 1) + padding

        # Ensure a minimum height when only one story exists
        if upper <= lower:
            upper = lower + 1.0

        # padding=0 disables PyQtGraph's automatic margins
        self.plot.setYRange(lower, upper, padding=0)

    def set_value_range(self, min_val: float, max_val: float,
                       left_padding: float = 0.02, right_padding: float = 0.15):
        """
        Set x-axis range with asymmetric padding.

        Args:
            min_val: Minimum value
            max_val: Maximum value
            left_padding: Left padding as fraction of range
            right_padding: Right padding as fraction of range
        """
        range_val = max_val - min_val
        self.plot.setXRange(
            min_val - range_val * left_padding,
            max_val + range_val * right_padding,
            padding=0
        )

    def add_line(self, x_values: list, y_values: list,
                color: str, width: int = 2, style=Qt.PenStyle.SolidLine):
        """
        Add a line to the plot.

        Args:
            x_values: X coordinates
            y_values: Y coordinates
            color: Line color (hex or name)
            width: Line width in pixels
            style: Line style (SolidLine, DashLine, etc.)

        Returns:
            PlotDataItem reference
        """
        return self.plot.plot(
            x_values,
            y_values,
            pen=pg.mkPen(color, width=width, style=style)
        )

    def set_title(self, title: str, bold: bool = True):
        """
        Set plot title.

        Args:
            title: Title text
            bold: Whether to make title bold
        """
        if bold:
            title = f"<b>{title}</b>"
        self.plot.setTitle(title, color='#d1d5db', size='14pt')  # Match other titles

        # Add spacing between title and plot area
        plot_item = self.plot.getPlotItem()
        plot_item.layout.setRowSpacing(0, 12)

    def set_tick_spacing(self, axis: str = 'bottom', tick_interval: float = None):
        """
        Set tick spacing for an axis.

        Args:
            axis: 'bottom' or 'left'
            tick_interval: Interval between ticks (if None, calculated automatically)
        """
        ax = self.plot.getAxis(axis)
        if tick_interval is not None:
            ax.setTickSpacing(major=tick_interval, minor=tick_interval/2)

    def set_dynamic_tick_spacing(self, axis: str = 'bottom', min_val: float = None,
                                  max_val: float = None, num_intervals: int = 6):
        """
        Set dynamic tick spacing based on data range, rounded to nice numbers.

        Args:
            axis: 'bottom' or 'left'
            min_val: Minimum value in the data range
            max_val: Maximum value in the data range
            num_intervals: Target number of intervals (default 6)
        """
        if min_val is None or max_val is None:
            return

        # Calculate range
        data_range = abs(max_val - min_val)

        if data_range == 0:
            return

        # Calculate raw interval
        raw_interval = data_range / num_intervals

        # Get magnitude (power of 10)
        import math
        magnitude = 10 ** math.floor(math.log10(raw_interval))

        # Normalize to 1-10 range
        normalized = raw_interval / magnitude

        # Round to nice number using 1-2-5 pattern
        # This gives intervals like: 0.1, 0.2, 0.5, but capped at 0.5 maximum
        if normalized <= 1.5:
            nice_interval = 1.0
        elif normalized <= 3.5:
            nice_interval = 2.0
        else:
            nice_interval = 5.0

        # Scale back to original magnitude
        tick_interval = nice_interval * magnitude

        # Cap at 0.5 only when working with small drift-style ranges
        if tick_interval > 0.5 and data_range <= 5:
            tick_interval = 0.5

        # Set tick spacing
        ax = self.plot.getAxis(axis)
        ax.setTickSpacing(major=tick_interval, minor=tick_interval/2)
