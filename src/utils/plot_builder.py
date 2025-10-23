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

    def set_story_range(self, num_stories: int, padding: float = -0.05):
        """
        Set y-axis range for stories with tight fit.

        Args:
            num_stories: Number of stories
            padding: Padding factor (negative for tighter fit)
        """
        self.plot.setYRange(-0.5, num_stories - 0.5, padding=padding)

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
        self.plot.setTitle(title, color='#4a7d89', size='14pt')
