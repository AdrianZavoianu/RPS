"""Comparison Joint Scatter widget - scatter plot comparing soil pressures/vertical displacements across multiple result sets."""

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


class ComparisonJointScatterWidget(QWidget):
    """Widget for displaying joint result comparison as scatter plot across multiple result sets.

    Similar to ComparisonAllRotationsWidget but for soil pressures and vertical displacements.
    Load cases on X-axis, values on Y-axis, with multiple result sets overlaid.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.current_datasets = []  # List of (result_set_name, df_data, load_cases)
        self.y_label = "Value"  # Will be set based on result type

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
        view_box.setDefaultPadding(0.05)

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

    def set_labels(self, x_label: str, y_label: str):
        """Update the axis labels.

        Args:
            x_label: X-axis label text
            y_label: Y-axis label text
        """
        self.plot_widget.setLabel('bottom', x_label)
        self.plot_widget.setLabel('left', y_label)
        self.y_label = y_label

    def load_comparison_datasets(self, datasets: list, result_type: str):
        """Load and display joint result data points for multiple result sets.

        Args:
            datasets: List of tuples (result_set_name, df_data, load_cases)
                     where df_data contains columns for each load case with pressure/displacement values
            result_type: Type of result ('SoilPressures' or 'VerticalDisplacements')
        """
        if not datasets or all(df is None or df.empty for _, df, _ in datasets):
            self.clear_data()
            return

        self.current_datasets = datasets

        # Set appropriate labels
        if result_type == 'SoilPressures':
            self.set_labels('Load Case', 'Soil Pressure (kN/m²)')
        elif result_type == 'VerticalDisplacements':
            self.set_labels('Load Case', 'Vertical Displacement (mm)')
        else:
            self.set_labels('Load Case', 'Value')

        # Update plot
        self._plot_comparison_scatter(datasets)

    def _plot_comparison_scatter(self, datasets: list):
        """Plot scatter plot with data from multiple result sets."""
        self.plot_widget.clear()
        self._clear_legend()

        # Get all unique load cases across all datasets (for X-axis)
        all_load_cases = []
        for _, df_data, load_cases in datasets:
            if df_data is not None and not df_data.empty and load_cases:
                all_load_cases.extend(load_cases)

        # Use unique load cases in sorted order
        unique_load_cases = sorted(set(all_load_cases))
        if not unique_load_cases:
            return

        # Create load case index mapping (0, 1, 2, ... for X axis)
        load_case_to_index = {lc: idx for idx, lc in enumerate(unique_load_cases)}

        all_y_values = []

        # Define colors for each result set
        colors = [
            '#f97316',  # Orange
            '#3b82f6',  # Blue
            '#10b981',  # Green
            '#ef4444',  # Red
            '#8b5cf6',  # Purple
            '#ec4899',  # Pink
        ]

        # Plot data for each result set
        for idx, (result_set_name, df_data, load_cases) in enumerate(datasets):
            if df_data is None or df_data.empty or not load_cases:
                continue

            # Get color for this result set
            color = colors[idx % len(colors)]

            # Prepare scatter data with jitter
            x_values, y_values = self._prepare_scatter_data(
                df_data, load_cases, load_case_to_index, idx
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
                all_y_values.extend(y_values)

                # Add legend item for this result set
                self._add_legend_item(color, result_set_name)

        # Configure X-axis with load case labels
        x_axis = self.plot_widget.getAxis('bottom')
        x_ticks = [(idx, lc) for idx, lc in enumerate(unique_load_cases)]
        x_axis.setTicks([x_ticks])

        # Rotate labels if there are many load cases
        if len(unique_load_cases) > 10:
            x_axis.setStyle(tickTextOffset=10)
            # Note: PyQtGraph doesn't support angled text, but we can increase spacing

        # Set X-axis range with padding
        self.plot_widget.setXRange(-0.5, len(unique_load_cases) - 0.5, padding=0)

        # Set Y-axis range based on data
        if all_y_values:
            min_y = min(all_y_values)
            max_y = max(all_y_values)

            # Add 10% padding
            y_range = max_y - min_y
            padding_y = y_range * 0.1 if y_range > 0 else 1

            self.plot_widget.setYRange(min_y - padding_y, max_y + padding_y, padding=0)

    def _prepare_scatter_data(self, df: pd.DataFrame, load_cases: list,
                             load_case_to_index: dict, seed_offset: int):
        """Prepare scatter data with jitter for a dataset.

        Args:
            df: DataFrame with joint result data (columns are load cases)
            load_cases: List of load case column names in this dataset
            load_case_to_index: Mapping of load case names to x-axis indices
            seed_offset: Offset for random seed to ensure different jitter per result set

        Returns:
            Tuple of (x_values, y_values)
        """
        x_values = []
        y_values = []

        # Use consistent random seed for reproducible jitter
        np.random.seed(42 + seed_offset)

        for load_case in load_cases:
            if load_case not in df.columns or load_case not in load_case_to_index:
                continue

            # Get all values for this load case
            values = df[load_case].dropna().abs().values  # Use absolute values like standard view

            if len(values) == 0:
                continue

            lc_idx = load_case_to_index[load_case]

            # Apply horizontal jitter within ±0.3 of load case index
            jitter_range = 0.3
            jitter = np.random.uniform(-jitter_range, jitter_range, len(values))
            jittered_x = lc_idx + jitter

            x_values.extend(jittered_x)
            y_values.extend(values)

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
        item_layout.setContentsMargins(0, 0, 0, 0)
        item_layout.setSpacing(8)

        # Color indicator (circle)
        color_indicator = QLabel()
        color_indicator.setFixedSize(12, 12)
        color_indicator.setStyleSheet(f"""
            QLabel {{
                background-color: {color};
                border-radius: 6px;
            }}
        """)
        item_layout.addWidget(color_indicator)

        # Label
        label_widget = QLabel(label)
        label_widget.setStyleSheet("""
            QLabel {
                color: #d1d5db;
                font-size: 13px;
                font-weight: 500;
            }
        """)
        item_layout.addWidget(label_widget)

        # Add to legend layout
        self.legend_layout.addWidget(legend_item)
        self.legend_items.append(legend_item)

    def _clear_legend(self):
        """Remove all legend items."""
        for item in self.legend_items:
            item.deleteLater()
        self.legend_items.clear()

    def clear_data(self):
        """Clear all data from the plot."""
        self.plot_widget.clear()
        self._clear_legend()
        self.current_datasets = []
