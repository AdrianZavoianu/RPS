"""Comparison All Rotations widget - scatter plot comparing rotation distributions across multiple result sets."""

import numpy as np
import pandas as pd
import pyqtgraph as pg
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)


class ComparisonAllRotationsWidget(QWidget):
    """Widget for displaying all rotations comparison as scatter plot across multiple result sets."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.current_datasets = []  # List of (result_set_name, df_data)

    def setup_ui(self):
        """Setup the UI with plot and legend."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(8)

        # Create horizontal layout for plot and legend
        h_layout = QHBoxLayout()
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(8)

        # Create plot widget
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('#0a0c10')

        # Set plot area background
        view_box = self.plot_widget.getPlotItem().getViewBox()
        view_box.setBackgroundColor('#0f1419')
        view_box.setBorder(pg.mkPen('#2c313a', width=1))

        # Configure plot appearance
        self.plot_widget.showGrid(x=True, y=True, alpha=0.5)
        self.plot_widget.getAxis('bottom').setPen(pg.mkPen('#2c313a', width=1))
        self.plot_widget.getAxis('left').setPen(pg.mkPen('#2c313a', width=1))
        self.plot_widget.getAxis('bottom').setTextPen('#d1d5db')
        self.plot_widget.getAxis('left').setTextPen('#d1d5db')

        # Disable interactions
        self.plot_widget.setMenuEnabled(False)
        view_box.setMouseEnabled(x=False, y=False)
        view_box.setDefaultPadding(0.0)

        # No title - maximizes plot area
        self.plot_widget.setTitle(None)

        h_layout.addWidget(self.plot_widget, 1)  # Plot takes available space

        # Create legend container on the right side
        self.legend_container = QWidget()
        self.legend_container.setStyleSheet("background-color: transparent;")
        legend_layout = QVBoxLayout(self.legend_container)
        legend_layout.setContentsMargins(12, 0, 0, 0)  # Add left padding
        legend_layout.setSpacing(8)
        legend_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        h_layout.addWidget(self.legend_container, 0)  # Legend doesn't stretch

        main_layout.addLayout(h_layout)

        # Store references
        self.legend_layout = legend_layout
        self.legend_items = []

    def set_x_label(self, label: str):
        """Update the X-axis label.

        Args:
            label: New X-axis label text
        """
        self.plot_widget.setLabel('bottom', label)

    def load_comparison_datasets(self, datasets: list):
        """Load and display all rotation data points for multiple result sets.

        Args:
            datasets: List of tuples (result_set_name, df_data)
                     where df_data contains columns: Element, Story, LoadCase, Rotation, StoryOrder, StoryIndex
        """
        if not datasets or all(df is None or df.empty for _, df in datasets):
            self.clear_data()
            return

        self.current_datasets = datasets

        # Update plot
        self._plot_comparison_scatter(datasets)

    def _plot_comparison_scatter(self, datasets: list):
        """Plot scatter plot with data from multiple result sets."""
        self.plot_widget.clear()
        self._clear_legend()

        # Get reference dataframe for story setup (use first non-empty)
        df_ref = None
        for _, df in datasets:
            if df is not None and not df.empty:
                df_ref = df
                break

        if df_ref is None:
            return

        # Get unique stories in order
        stories_df = df_ref[['Story', 'StoryOrder']].drop_duplicates().sort_values('StoryOrder')
        story_names_excel_order = stories_df['Story'].tolist()

        # REVERSE story order for plotting: bottom floors at bottom (y=0), top floors at top (y=max)
        story_names = list(reversed(story_names_excel_order))
        num_stories = len(story_names)

        # Create story index mapping (0, 1, 2, ... for Y axis)
        story_to_index = {name: idx for idx, name in enumerate(story_names)}

        all_x_values = []

        # Define colors for each result set (orange for first, blue for second)
        colors = [
            '#f97316',  # Orange
            '#3b82f6',  # Blue
            '#10b981',  # Green
            '#ef4444',  # Red
            '#8b5cf6',  # Purple
            '#ec4899',  # Pink
        ]

        # Plot data for each result set
        for idx, (result_set_name, df_data) in enumerate(datasets):
            if df_data is None or df_data.empty:
                continue

            # Get color for this result set
            color = colors[idx % len(colors)]

            # Prepare scatter data with jitter
            x_values, y_values = self._prepare_scatter_data(
                df_data, story_to_index, idx
            )

            if x_values:
                scatter_item = pg.ScatterPlotItem(
                    x=x_values,
                    y=y_values,
                    size=6,
                    pen=pg.mkPen(None),
                    brush=pg.mkBrush(QColor(color)),
                    symbol='o',
                )
                self.plot_widget.addItem(scatter_item)
                all_x_values.extend(x_values)

                # Add legend item for this result set
                self._add_legend_item(color, result_set_name)

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
        self.plot_widget.setLabel('bottom', 'Rotation (%)')
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

    def _prepare_scatter_data(self, df: pd.DataFrame, story_to_index: dict, seed_offset: int):
        """Prepare scatter data with jitter for a dataset.

        Args:
            df: DataFrame with rotation data
            story_to_index: Mapping of story names to y-axis indices
            seed_offset: Offset for random seed to ensure different jitter per result set

        Returns:
            Tuple of (x_values, y_values)
        """
        x_values = []
        y_values = []

        # Get unique stories in the dataframe
        story_names = df['Story'].unique()

        # Use consistent random seed for reproducible jitter
        np.random.seed(42 + seed_offset)

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

        return x_values, y_values

    def _add_legend_item(self, color: str, label: str):
        """Add a legend item to the external legend with rounded card style."""
        # Create rounded card-style legend item
        legend_item = QWidget()
        legend_item.setStyleSheet(f"""
            QWidget {{
                background-color: #161b22;
                border: 1px solid #2c313a;
                border-radius: 6px;
                padding: 8px 12px;
            }}
        """)

        item_layout = QHBoxLayout(legend_item)
        item_layout.setContentsMargins(8, 0, 0, 0)  # Add left padding inside card
        item_layout.setSpacing(8)

        # Color indicator (small colored square)
        color_indicator = QLabel()
        color_indicator.setStyleSheet(f"""
            QLabel {{
                background-color: {color};
                border: none;
                border-radius: 2px;
                min-width: 12px;
                max-width: 12px;
                min-height: 12px;
                max-height: 12px;
            }}
        """)

        # Label text
        text_label = QLabel(label)
        text_label.setStyleSheet("""
            QLabel {
                color: #d1d5db;
                font-size: 11pt;
                font-weight: 600;
                background-color: transparent;
                border: none;
            }
        """)

        item_layout.addWidget(color_indicator)
        item_layout.addWidget(text_label)
        item_layout.addStretch()

        self.legend_layout.addWidget(legend_item)
        self.legend_items.append(legend_item)

    def _clear_legend(self):
        """Clear all legend items."""
        for item in self.legend_items:
            self.legend_layout.removeWidget(item)
            item.deleteLater()
        self.legend_items.clear()

    def clear_data(self):
        """Clear all data from plot."""
        self.plot_widget.clear()
        self._clear_legend()
        self.current_datasets = []
