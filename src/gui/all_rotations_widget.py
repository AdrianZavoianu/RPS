"""All Rotations widget - scatter plot and histogram showing distribution of quad rotations across all elements."""

import numpy as np
import pandas as pd
import pyqtgraph as pg
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QVBoxLayout,
    QWidget,
    QTabWidget,
)


class AllRotationsWidget(QWidget):
    """Widget for displaying all quad rotations as scatter plot and histogram (Max and Min combined)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.current_data_max = None
        self.current_data_min = None

    def setup_ui(self):
        """Setup the UI with tabs for scatter plot and histogram."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Create tab widget
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background-color: transparent;
            }
            QTabBar::tab {
                background-color: transparent;
                color: #9ca3af;
                padding: 8px 14px;
                border: none;
                margin-right: 6px;
            }
            QTabBar::tab:selected {
                background-color: transparent;
                color: #67e8f9;
                border-bottom: 2px solid #67e8f9;
            }
            QTabBar::tab:hover {
                background-color: transparent;
                color: #cbd5e1;
            }
        """)

        # Create scatter plot widget
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('#0a0c10')

        # Set plot area background
        view_box = self.plot_widget.getPlotItem().getViewBox()
        view_box.setBackgroundColor('#0c1016')
        view_box.setBorder(None)

        # Configure plot appearance
        self.plot_widget.showGrid(x=True, y=True, alpha=0.35)
        subtle_axis = pg.mkPen('#151b22', width=1)
        self.plot_widget.getAxis('bottom').setPen(subtle_axis)
        self.plot_widget.getAxis('left').setPen(subtle_axis)
        self.plot_widget.getAxis('bottom').setTextPen('#cdd3dd')
        self.plot_widget.getAxis('left').setTextPen('#cdd3dd')

        # Disable interactions
        self.plot_widget.setMenuEnabled(False)
        view_box.setMouseEnabled(x=False, y=False)
        view_box.setDefaultPadding(0.0)

        # No title - maximizes plot area
        self.plot_widget.setTitle(None)

        # Create histogram widget
        self.histogram_widget = pg.PlotWidget()
        self.histogram_widget.setBackground('#0a0c10')

        # Set histogram area background
        hist_view_box = self.histogram_widget.getPlotItem().getViewBox()
        hist_view_box.setBackgroundColor('#0c1016')
        hist_view_box.setBorder(None)

        # Configure histogram appearance
        self.histogram_widget.showGrid(x=True, y=True, alpha=0.35)
        self.histogram_widget.getAxis('bottom').setPen(subtle_axis)
        self.histogram_widget.getAxis('left').setPen(subtle_axis)
        self.histogram_widget.getAxis('bottom').setTextPen('#cdd3dd')
        self.histogram_widget.getAxis('left').setTextPen('#cdd3dd')

        # Disable interactions
        self.histogram_widget.setMenuEnabled(False)
        hist_view_box.setMouseEnabled(x=False, y=False)
        hist_view_box.setDefaultPadding(0.05)

        # No title - maximizes plot area
        self.histogram_widget.setTitle(None)

        # Add tabs
        self.tabs.addTab(self.plot_widget, "Scatter")
        self.tabs.addTab(self.histogram_widget, "Histogram")

        layout.addWidget(self.tabs)

    def set_x_label(self, label: str):
        """Update the X-axis label for both plots.

        Args:
            label: New X-axis label text
        """
        self.plot_widget.setLabel('bottom', label)
        self.histogram_widget.setLabel('bottom', label)

    def load_dataset(self, df_max: pd.DataFrame, df_min: pd.DataFrame):
        """Load and display all rotation data points (both Max and Min).

        Args:
            df_max: DataFrame with Max rotation data (Element, Story, LoadCase, Rotation, StoryOrder, StoryIndex)
            df_min: DataFrame with Min rotation data (Element, Story, LoadCase, Rotation, StoryOrder, StoryIndex)
        """
        if (df_max is None or df_max.empty) and (df_min is None or df_min.empty):
            self.clear_data()
            return

        self.current_data_max = df_max
        self.current_data_min = df_min

        # Update scatter plot
        self._plot_combined_scatter(df_max, df_min)

        # Update histogram
        self._plot_histogram(df_max, df_min)

    def _plot_combined_scatter(self, df_max: pd.DataFrame, df_min: pd.DataFrame):
        """Plot scatter plot with both Max and Min data, story bins, and vertical jitter."""
        self.plot_widget.clear()

        # Use whichever dataframe is available to get story info
        df_ref = df_max if df_max is not None and not df_max.empty else df_min
        if df_ref is None or df_ref.empty:
            return

        # Get unique stories in order
        stories_df = df_ref[['Story', 'StoryOrder']].drop_duplicates().sort_values('StoryOrder')
        story_names_excel_order = stories_df['Story'].tolist()

        # REVERSE story order for plotting: bottom floors at bottom (y=0), top floors at top (y=max)
        # Excel typically has top-to-bottom, but we want bottom-to-top for plots
        story_names = list(reversed(story_names_excel_order))
        num_stories = len(story_names)

        # Create story index mapping (0, 1, 2, ... for Y axis)
        # Now 0 = bottom floor, max = top floor
        story_to_index = {name: idx for idx, name in enumerate(story_names)}

        all_x_values = []

        # Define single orange color for all markers
        orange_color = QColor('#f97316')

        # Plot Max data points (small orange circles)
        if df_max is not None and not df_max.empty:
            x_max, y_max, _ = self._prepare_scatter_data(
                df_max, story_to_index, "Max"
            )
            if x_max:
                scatter_max = pg.ScatterPlotItem(
                    x=x_max,
                    y=y_max,
                    size=4,  # Smaller markers
                    pen=pg.mkPen(None),
                    brush=pg.mkBrush(orange_color),  # All orange
                    symbol='o',
                )
                self.plot_widget.addItem(scatter_max)
                all_x_values.extend(x_max)

        # Plot Min data points (small orange circles)
        if df_min is not None and not df_min.empty:
            x_min, y_min, _ = self._prepare_scatter_data(
                df_min, story_to_index, "Min"
            )
            if x_min:
                scatter_min = pg.ScatterPlotItem(
                    x=x_min,
                    y=y_min,
                    size=4,  # Smaller markers
                    pen=pg.mkPen(None),
                    brush=pg.mkBrush(orange_color),  # All orange
                    symbol='o',
                )
                self.plot_widget.addItem(scatter_min)
                all_x_values.extend(x_min)

        # Add vertical line at x=0 to show center
        zero_line = pg.InfiniteLine(pos=0, angle=90, pen=pg.mkPen('#4a7d89', width=1, style=Qt.PenStyle.DashLine))
        self.plot_widget.addItem(zero_line)

        # Configure Y-axis with story labels
        y_axis = self.plot_widget.getAxis('left')
        y_ticks = [(idx, name) for idx, name in enumerate(story_names)]
        y_axis.setTicks([y_ticks])

        # Set Y-axis range with padding
        self.plot_widget.setYRange(-0.5, num_stories - 0.5, padding=0)

        # Set X-axis label
        self.plot_widget.setLabel('bottom', 'Quad Rotation (%)')
        self.plot_widget.setLabel('left', 'Story')

        # Set X-axis range centered at 0 for symmetry
        if all_x_values:
            min_x = min(all_x_values)
            max_x = max(all_x_values)

            # Find the maximum absolute value to create symmetric range
            max_abs = max(abs(min_x), abs(max_x))

            # Add 10% padding
            padding_x = max_abs * 0.1

            # Set symmetric range around 0
            self.plot_widget.setXRange(-(max_abs + padding_x), max_abs + padding_x, padding=0)

    def _prepare_scatter_data(self, df: pd.DataFrame, story_to_index: dict, label: str):
        """Prepare scatter data with jitter for a dataset.

        Returns:
            Tuple of (x_values, y_values, colors)
        """
        x_values = []
        y_values = []
        colors = []

        # Get unique stories in the dataframe
        story_names = df['Story'].unique()

        # Use consistent random seed for reproducible jitter
        np.random.seed(42 if label == "Max" else 43)

        for story_name in story_names:
            if story_name not in story_to_index:
                continue

            story_data = df[df['Story'] == story_name]
            story_idx = story_to_index[story_name]

            # Get rotation values for this story
            rotations = story_data['Rotation'].values

            # Apply vertical jitter within ±0.3 of story index
            jitter_range = 0.3
            jitter = np.random.uniform(-jitter_range, jitter_range, len(rotations))
            jittered_y = story_idx + jitter

            x_values.extend(rotations)
            y_values.extend(jittered_y)

            # Color by rotation magnitude
            for rot in rotations:
                colors.append(self._get_rotation_color(rot, label))

        return x_values, y_values, colors

    def _get_rotation_color(self, rotation: float, label: str) -> QColor:
        """Get color based on rotation magnitude and Max/Min type.

        Args:
            rotation: Rotation value in percentage
            label: "Max" or "Min"
        """
        # Normalize rotation to 0-1 range (assuming typical range 0-2%)
        norm_value = min(abs(rotation) / 2.0, 1.0)

        if label == "Max":
            # Max: Blue (#3b82f6) to Orange (#f97316) to Red (#ef4444)
            if norm_value < 0.5:
                # Blue to orange
                t = norm_value * 2
                r = int(59 + (249 - 59) * t)
                g = int(130 + (115 - 130) * t)
                b = int(246 + (22 - 246) * t)
            else:
                # Orange to red
                t = (norm_value - 0.5) * 2
                r = int(249 + (239 - 249) * t)
                g = int(115 + (68 - 115) * t)
                b = int(22 + (68 - 22) * t)
        else:
            # Min: Orange (#f97316) to Red (#ef4444)
            r = int(249 + (239 - 249) * norm_value)
            g = int(115 + (68 - 115) * norm_value)
            b = int(22 + (68 - 22) * norm_value)

        return QColor(r, g, b, 180)  # 70% opacity

    def _plot_histogram(self, df_max: pd.DataFrame, df_min: pd.DataFrame):
        """Plot histogram of all rotation values.

        Args:
            df_max: DataFrame with Max rotation data
            df_min: DataFrame with Min rotation data
        """
        self.histogram_widget.clear()

        # Collect all rotation values
        all_rotations = []
        if df_max is not None and not df_max.empty:
            all_rotations.extend(df_max['Rotation'].values)
        if df_min is not None and not df_min.empty:
            all_rotations.extend(df_min['Rotation'].values)

        if not all_rotations:
            return

        # Calculate histogram with automatic binning
        # Use 50 bins for good resolution
        counts, bin_edges = np.histogram(all_rotations, bins=50)

        # Create bar graph
        bin_width = bin_edges[1] - bin_edges[0]
        x_positions = bin_edges[:-1]  # Use left edge of each bin

        # Create bar chart
        bar_item = pg.BarGraphItem(
            x=x_positions,
            height=counts,
            width=bin_width,
            brush=pg.mkBrush(251, 146, 60, 180),  # Orange with alpha
            pen=pg.mkPen('#fb923c', width=1)
        )
        self.histogram_widget.addItem(bar_item)

        # Add vertical line at x=0 to show center
        zero_line = pg.InfiniteLine(pos=0, angle=90, pen=pg.mkPen('#4a7d89', width=1, style=Qt.PenStyle.DashLine))
        self.histogram_widget.addItem(zero_line)

        # Set axis labels
        self.histogram_widget.setLabel('bottom', 'Quad Rotation (%)')
        self.histogram_widget.setLabel('left', 'Count')

        # Set Y-axis to start at 0
        max_count = max(counts) if len(counts) > 0 else 1
        self.histogram_widget.setYRange(0, max_count * 1.1, padding=0)

        # Set X-axis range with padding
        min_x = min(all_rotations)
        max_x = max(all_rotations)
        padding_x = (max_x - min_x) * 0.05
        self.histogram_widget.setXRange(min_x - padding_x, max_x + padding_x, padding=0)

    def clear_data(self):
        """Clear all data from plots."""
        self.plot_widget.clear()
        self.histogram_widget.clear()
        self.current_data_max = None
        self.current_data_min = None
