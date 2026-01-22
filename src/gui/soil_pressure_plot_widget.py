"""Soil Pressure Plot widget - scatter plot and histogram showing pressure distribution across load cases."""

import numpy as np
import pandas as pd
import pyqtgraph as pg
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QVBoxLayout, QWidget, QTabWidget


class SoilPressurePlotWidget(QWidget):
    """Widget for displaying soil pressures as scatter plot and histogram (load cases on X-axis, pressures on Y-axis)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.current_data = None

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

        # Create scatter plot widget using factory
        from gui.components.plot_factory import create_plot_widget, configure_scatter_plot
        self.plot_widget = create_plot_widget(show_border=False, grid_alpha=0.35)
        configure_scatter_plot(self.plot_widget, x_label='Load Case', y_label='Soil Pressure (kN/m²)')

        # Create histogram widget using factory
        self.histogram_widget = create_plot_widget(
            plot_type='histogram', show_border=False, grid_alpha=0.35
        )
        configure_scatter_plot(self.histogram_widget, x_label='Soil Pressure (kN/m²)', y_label='Count')

        # Add tabs
        self.tabs.addTab(self.plot_widget, "Scatter")
        self.tabs.addTab(self.histogram_widget, "Histogram")

        layout.addWidget(self.tabs)

    def load_dataset(self, df: pd.DataFrame, load_cases: list, result_type: str = "SoilPressures"):
        """Load and display soil pressure data as scatter plot and histogram.

        Args:
            df: DataFrame with columns: Shell Object, Unique Name, and load case columns
            load_cases: List of load case column names
            result_type: 'SoilPressures' or 'VerticalDisplacements' to drive axis labels
        """
        if df is None or df.empty or not load_cases:
            self.clear_data()
            return

        # Update axis labels based on the dataset being rendered
        if result_type == "VerticalDisplacements":
            self.plot_widget.setLabel('bottom', 'Load Case')
            self.plot_widget.setLabel('left', 'Vertical Displacement (mm)')
            self.histogram_widget.setLabel('bottom', 'Vertical Displacement (mm)')
            self.histogram_widget.setLabel('left', 'Count')
        else:
            self.plot_widget.setLabel('bottom', 'Load Case')
            self.plot_widget.setLabel('left', 'Soil Pressure (kN/mı)')
            self.histogram_widget.setLabel('bottom', 'Soil Pressure (kN/mı)')
            self.histogram_widget.setLabel('left', 'Count')

        self.current_data = df

        # Collect all pressure values for each load case (use absolute values)
        load_case_data = []
        for i, load_case in enumerate(load_cases):
            if load_case in df.columns:
                values = df[load_case].dropna().abs()  # Use absolute values
                if len(values) > 0:
                    load_case_data.append({
                        'load_case': load_case,
                        'index': i,
                        'values': values.values
                    })

        if not load_case_data:
            self.clear_data()
            return

        # Plot the scatter points
        self._plot_scatter(load_case_data)

        # Plot the histogram
        self._plot_histogram(load_case_data)

    def _plot_scatter(self, load_case_data: list):
        """Plot scatter points with load cases on X-axis and individual pressure values on Y-axis.

        Args:
            load_case_data: List of dicts with keys: load_case, index, values
        """
        self.plot_widget.clear()

        if not load_case_data:
            return

        # Extract load case names for axis labels
        load_case_names = [item['load_case'] for item in load_case_data]

        # Track global min/max for Y-axis range
        all_values = []

        # Plot scatter points for each load case
        for item in load_case_data:
            x_index = item['index']
            values = item['values']
            all_values.extend(values)

            # Add small random jitter to X positions to avoid overlapping points
            # Jitter range: ±0.15 around the center position
            x_positions = np.ones(len(values)) * x_index + np.random.uniform(-0.15, 0.15, len(values))

            # Create scatter plot
            scatter = pg.ScatterPlotItem(
                x=x_positions,
                y=values,
                size=6,
                pen=pg.mkPen(None),
                brush=pg.mkBrush(251, 146, 60, 180),  # #fb923c (orange) with alpha
                symbol='o'
            )
            self.plot_widget.addItem(scatter)

        # Set X-axis labels
        axis = self.plot_widget.getAxis('bottom')
        ticks = [(i, name) for i, name in enumerate(load_case_names)]
        axis.setTicks([ticks])

        # Set Y-axis range based on data
        if all_values:
            y_min = 0  # Start at 0 for pressure
            y_max = max(all_values) * 1.1  # Add 10% padding at top
            self.plot_widget.setYRange(y_min, y_max, padding=0)

    def _plot_histogram(self, load_case_data: list):
        """Plot histogram of all soil pressure values.

        Args:
            load_case_data: List of dicts with keys: load_case, index, values
        """
        self.histogram_widget.clear()

        # Collect all pressure values from all load cases
        all_pressures = []
        for item in load_case_data:
            all_pressures.extend(item['values'])

        if not all_pressures:
            return

        # Calculate histogram with automatic binning
        # Use 50 bins for good resolution
        counts, bin_edges = np.histogram(all_pressures, bins=50)

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

        # Set Y-axis to start at 0
        max_count = max(counts) if len(counts) > 0 else 1
        self.histogram_widget.setYRange(0, max_count * 1.1, padding=0)

        # Set X-axis range with padding
        min_x = min(all_pressures)
        max_x = max(all_pressures)
        padding_x = (max_x - min_x) * 0.05
        self.histogram_widget.setXRange(min_x - padding_x, max_x + padding_x, padding=0)

    def clear_data(self):
        """Clear the plots."""
        self.plot_widget.clear()
        self.histogram_widget.clear()
        self.current_data = None
