"""Results plot widget - PyQtGraph plots with GMP styling."""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel
from PyQt6.QtCore import Qt
import pyqtgraph as pg
import pandas as pd
import numpy as np


class ResultsPlotWidget(QWidget):
    """Plot widget for visualizing results."""

    SUMMARY_COLUMNS = {"Avg", "Max", "Min"}

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_data = None
        self.current_result_type = None
        self._plot_legends = {}
        self.setup_ui()

    def setup_ui(self):
        """Setup the plot UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)  # No margins - match table widget

        # Configure PyQtGraph to match GMP dark theme
        pg.setConfigOptions(antialias=True)
        pg.setConfigOption('background', '#0a0c10')
        pg.setConfigOption('foreground', '#d1d5db')

        # Tab widget for different plot types
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #2c313a;
                background-color: #0a0c10;
                border-radius: 6px;
                margin-top: 0px;
            }
            QTabBar {
                background-color: transparent;
            }
            QTabBar::tab {
                background-color: #161b22;
                color: #7f8b9a;
                padding: 10px 20px;
                margin-right: 2px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                min-width: 120px;
                max-height: 40px;
            }
            QTabBar::tab:selected {
                background-color: #0a0c10;
                color: #4a7d89;
                border-bottom: 2px solid #4a7d89;
            }
            QTabBar::tab:hover {
                background-color: #1f2937;
                color: #d1d5db;
            }
        """)

        # Create plot tabs
        self.envelope_plot = self._create_plot_widget("Envelope by Story")
        self.tabs.addTab(self.envelope_plot, "📊 Envelope")

        self.comparison_plot = self._create_plot_widget("Load Case Comparison")
        self.tabs.addTab(self.comparison_plot, "📈 Comparison")

        self.profile_plot = self._create_plot_widget("Building Profile")
        self.tabs.addTab(self.profile_plot, "🏢 Profile")

        layout.addWidget(self.tabs)

    def _create_plot_widget(self, title: str) -> pg.PlotWidget:
        """Create a styled PyQtGraph plot widget."""
        plot_widget = pg.PlotWidget()
        plot_widget.setBackground('#0a0c10')

        # Configure plot appearance to match GMP
        plot_widget.showGrid(x=True, y=True, alpha=0.15)
        plot_widget.getAxis('bottom').setPen(pg.mkPen('#2c313a', width=1))
        plot_widget.getAxis('left').setPen(pg.mkPen('#2c313a', width=1))
        plot_widget.getAxis('bottom').setTextPen('#d1d5db')
        plot_widget.getAxis('left').setTextPen('#d1d5db')

        plot_widget.setMenuEnabled(False)
        view_box = plot_widget.getViewBox()
        view_box.setMouseEnabled(x=False, y=False)

        # Set title
        plot_widget.setTitle(title, color='#4a7d89', size='12pt')

        # Create legend and move it to a dedicated column on the right
        legend = pg.LegendItem()
        legend.setLabelTextColor('#d1d5db')
        legend.setBrush(pg.mkBrush('#11151c'))
        legend.setPen(pg.mkPen('#2c313a'))
        legend.opts['sampleWidth'] = 16
        legend.layout.setContentsMargins(6, 6, 6, 6)
        legend.layout.setSpacing(4)

        plot_item = plot_widget.getPlotItem()
        plot_item.layout.addItem(legend, 0, 3, 3, 1)  # span title, view box, x-axis
        plot_item.layout.setColumnMinimumWidth(3, 140)
        plot_item.layout.setColumnMaximumWidth(3, 140)
        plot_item.layout.setColumnStretchFactor(0, 0)
        plot_item.layout.setColumnStretchFactor(1, 1)
        plot_item.layout.setColumnStretchFactor(2, 0)
        plot_item.layout.setColumnStretchFactor(3, 0)
        plot_item.layout.setColumnSpacing(2, 12)
        plot_item.layout.setRowStretchFactor(1, 1)

        self._plot_legends[plot_widget] = legend
        return plot_widget

    def load_data(self, df: pd.DataFrame, result_type: str):
        """Load data and generate plots."""
        self.current_data = df
        self.current_result_type = result_type

        # Clear previous plots
        self.clear_plots()

        if df.empty:
            return

        # For drifts, show building profile plot (main view) - hide tabs
        if result_type == "Drifts":
            self.tabs.tabBar().hide()  # Hide tabs for clean single plot view
            self._plot_building_profile(df, result_type)
        else:
            self.tabs.tabBar().show()  # Show tabs for other result types
            # Generate standard plots for other result types
            self._plot_envelope(df, result_type)
            self._plot_comparison(df, result_type)
            self._plot_profile(df, result_type)

    def _data_columns(self, df: pd.DataFrame) -> list[str]:
        """Return columns that represent load cases (exclude Story and summaries)."""
        return [
            col
            for col in df.columns
            if col != 'Story' and col not in self.SUMMARY_COLUMNS
        ]

    def _plot_envelope(self, df: pd.DataFrame, result_type: str):
        """Plot envelope values by story."""
        plot = self.envelope_plot
        self._reset_plot(plot)

        stories = df['Story'].tolist()
        story_indices = list(range(len(stories)))

        # Get numeric columns (exclude 'Story' column)
        numeric_cols = self._data_columns(df)

        if not numeric_cols:
            return

        # Calculate max value for each story
        max_values = df[numeric_cols].max(axis=1).tolist()

        # Plot as bar chart
        bargraph = pg.BarGraphItem(
            x=story_indices,
            height=max_values,
            width=0.8,
            brush='#4a7d89',
            pen=pg.mkPen('#2c313a', width=1)
        )
        plot.addItem(bargraph)
        self._add_legend_entry(plot, f"Max {result_type}", '#4a7d89', kind="bar")

        # Configure axes
        axis = plot.getAxis('bottom')
        axis.setTicks([[(i, name) for i, name in enumerate(stories)]])
        plot.setLabel('bottom', 'Story')
        plot.setLabel('left', self._get_ylabel(result_type))

        # Update title
        plot.setTitle(f"Maximum {result_type} by Story", color='#4a7d89', size='12pt')

    def _plot_comparison(self, df: pd.DataFrame, result_type: str):
        """Plot load case comparison."""
        plot = self.comparison_plot
        self._reset_plot(plot)

        stories = df['Story'].tolist()
        story_indices = list(range(len(stories)))

        # Get numeric columns
        numeric_cols = self._data_columns(df)

        if not numeric_cols:
            return

        # Color palette matching GMP
        colors = [
            '#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6',
            '#1abc9c', '#e67e22', '#34495e', '#16a085', '#27ae60'
        ]

        # Plot up to 10 load cases
        for idx, col in enumerate(numeric_cols[:10]):
            values = df[col].fillna(0).tolist()
            color = colors[idx % len(colors)]

            curve = plot.plot(
                story_indices,
                values,
                pen=pg.mkPen(color, width=2),
                symbol='o',
                symbolSize=6,
                symbolBrush=color,
                name=col
            )
            self._add_legend_entry(plot, curve, col)

        # Configure axes
        axis = plot.getAxis('bottom')
        axis.setTicks([[(i, name) for i, name in enumerate(stories)]])
        plot.setLabel('bottom', 'Story')
        plot.setLabel('left', self._get_ylabel(result_type))

        # Update title
        plot.setTitle(f"{result_type} - Load Case Comparison", color='#4a7d89', size='12pt')

    def _plot_profile(self, df: pd.DataFrame, result_type: str):
        """Plot building profile (story height vs max value)."""
        plot = self.profile_plot
        self._reset_plot(plot)

        stories = df['Story'].tolist()
        story_indices = list(range(len(stories)))

        # Get numeric columns
        numeric_cols = self._data_columns(df)

        if not numeric_cols:
            return

        # Calculate max and average for profile
        max_values = df[numeric_cols].max(axis=1).tolist()
        avg_values = df[numeric_cols].mean(axis=1).tolist()

        # Plot as horizontal bars (swap x and y)
        # Max envelope
        max_curve = plot.plot(
            max_values,
            story_indices,
            pen=pg.mkPen('#e74c3c', width=2),
            symbol='o',
            symbolSize=6,
            symbolBrush='#e74c3c',
            name='Maximum'
        )
        self._add_legend_entry(plot, max_curve, 'Maximum')

        # Average
        avg_curve = plot.plot(
            avg_values,
            story_indices,
            pen=pg.mkPen('#4a7d89', width=2, style=Qt.PenStyle.DashLine),
            symbol='s',
            symbolSize=5,
            symbolBrush='#4a7d89',
            name='Average'
        )
        self._add_legend_entry(plot, avg_curve, 'Average')

        # Configure axes
        axis = plot.getAxis('left')
        axis.setTicks([[(i, name) for i, name in enumerate(stories)]])
        plot.setLabel('left', 'Story')
        plot.setLabel('bottom', self._get_ylabel(result_type))

        # Update title
        plot.setTitle(f"{result_type} - Building Profile", color='#4a7d89', size='12pt')

    def _get_ylabel(self, result_type: str) -> str:
        """Get y-axis label based on result type."""
        labels = {
            'Drifts': 'Drift Ratio',
            'Accelerations': 'Acceleration (g)',
            'Forces': 'Shear Force (kN)',
        }
        return labels.get(result_type, 'Value')

    def _plot_building_profile(self, df: pd.DataFrame, result_type: str):
        """Plot building profile - drift vs height (like reference image)."""
        # Use the envelope plot for the main view
        plot = self.envelope_plot
        self._reset_plot(plot)

        stories = df['Story'].tolist()
        story_indices = list(range(len(stories)))

        # Get numeric columns (load cases)
        load_case_columns = self._data_columns(df)

        if not load_case_columns:
            return

        # Color palette matching the reference image
        colors = [
            '#e74c3c',  # Red - TH01
            '#3498db',  # Blue - TH02
            '#2ecc71',  # Green - TH03
            '#f39c12',  # Orange - TH04
            '#9b59b6',  # Purple - TH05
            '#1abc9c',  # Turquoise - TH06
            '#e67e22',  # Carrot - TH07
            '#95a5a6',  # Gray - TH08
            '#34495e',  # Dark blue - TH09
            '#16a085',  # Dark turquoise - TH10
            '#27ae60',  # Dark green - TH11
            '#2980b9',  # Dark blue - TH12
            '#8e44ad',  # Dark purple - TH13
        ]

        # Plot each load case as a line
        for idx, load_case in enumerate(load_case_columns):
            # Convert percentage back to decimal for plotting (or keep as percentage)
            values = df[load_case].fillna(0).tolist()

            # Convert percentage strings to floats
            numeric_values = []
            for val in values:
                if isinstance(val, str) and '%' in val:
                    numeric_values.append(float(val.replace('%', '')))
                else:
                    try:
                        numeric_values.append(float(val) * 100)  # Convert to percentage
                    except:
                        numeric_values.append(0)

            color = colors[idx % len(colors)]

            # Plot horizontal (drift on x-axis, story on y-axis)
            curve = plot.plot(
                numeric_values,
                story_indices,
                pen=pg.mkPen(color, width=2),
                name=load_case
            )
            self._add_legend_entry(plot, curve, load_case)

        # Calculate and plot average line (bold, dashed)
        if len(load_case_columns) > 1:
            avg_values = []
            for story_idx in range(len(stories)):
                story_values = []
                for load_case in load_case_columns:
                    val = df[load_case].iloc[story_idx]
                    if isinstance(val, str) and '%' in val:
                        story_values.append(float(val.replace('%', '')))
                    else:
                        try:
                            story_values.append(float(val) * 100)
                        except:
                            pass
                if story_values:
                    avg_values.append(sum(story_values) / len(story_values))
                else:
                    avg_values.append(0)

            # Plot average with bold, dashed line
            curve = plot.plot(
                avg_values,
                story_indices,
                pen=pg.mkPen('#4a7d89', width=3, style=Qt.PenStyle.DashLine),
                name='Average'
            )
            self._add_legend_entry(plot, curve, 'Average')

        # Configure axes
        axis = plot.getAxis('left')
        axis.setTicks([[(i, name) for i, name in enumerate(stories)]])
        plot.setLabel('left', 'Building Height')
        plot.setLabel('bottom', 'Drift (%)')

        # Set y-axis range to show all stories
        plot.setYRange(-0.5, len(stories) - 0.5)

        # Enable grid
        plot.showGrid(x=True, y=True, alpha=0.2)

        # Update title
        plot.setTitle("Story Drifts - Building Profile", color='#4a7d89', size='14pt')

    def clear_plots(self):
        """Clear all plots."""
        self._reset_plot(self.envelope_plot)
        self._reset_plot(self.comparison_plot)
        self._reset_plot(self.profile_plot)

    def _reset_plot(self, plot_widget: pg.PlotWidget):
        """Clear plot curves and synchronised legend entries."""
        plot_widget.clear()
        legend = self._plot_legends.get(plot_widget)
        if legend:
            legend.clear()

    def _add_legend_entry(self, plot_widget: pg.PlotWidget, item, label: str):
        """Add an item to the legend and tighten spacing."""
        legend = self._plot_legends.get(plot_widget)
        if legend and item is not None and label:
            legend.addItem(item, label)
            try:
                sample, label_item = legend.legendItems[-1]
                if hasattr(sample, "setFixedHeight"):
                    sample.setFixedHeight(12)
                if hasattr(sample, "setFixedWidth"):
                    sample.setFixedWidth(16)
                if hasattr(label_item, "setAttr"):
                    label_item.setAttr("size", "9pt")
            except Exception:
                pass
