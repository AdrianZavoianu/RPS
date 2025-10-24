"""Results plot widget - PyQtGraph plots with GMP styling."""

from __future__ import annotations

from typing import Optional

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QLabel,
    QFrame,
    QSpacerItem,
    QSizePolicy,
)
from PyQt6.QtCore import Qt
import pyqtgraph as pg
import pandas as pd

from utils.plot_builder import PlotBuilder
from processing.result_service import ResultDataset


class ResultsPlotWidget(QWidget):
    """Plot widget for visualizing results."""

    SUMMARY_COLUMNS = {"Avg", "Max", "Min"}

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_dataset: Optional[ResultDataset] = None
        self._plot_legends = {}
        self._plot_items = {}  # Store plot items for highlighting: {load_case: plot_item}
        self._highlighted_case = None  # Track currently highlighted load case
        self._current_selection: set[str] = set()
        self._average_plot_item = None
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
        self.tabs.addTab(self.envelope_plot, "▤ Envelope")

        self.comparison_plot = self._create_plot_widget("Load Case Comparison")
        self.tabs.addTab(self.comparison_plot, "≡ Comparison")

        self.profile_plot = self._create_plot_widget("Building Profile")
        self.tabs.addTab(self.profile_plot, "▭ Profile")

        layout.addWidget(self.tabs)

    def _create_plot_widget(self, title: str) -> QWidget:
        """Create a styled PyQtGraph plot widget with external legend."""
        # Container widget with horizontal layout
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)  # Spacing between plot and legend

        # Create the plot
        plot_widget = pg.PlotWidget()
        plot_widget.setBackground('#0a0c10')  # Overall background

        # Set plot area background to slightly lighter shade for differentiation
        view_box = plot_widget.getPlotItem().getViewBox()
        view_box.setBackgroundColor('#0f1419')

        # Add border to plot area
        view_box.setBorder(pg.mkPen('#2c313a', width=1))

        # Configure plot appearance to match GMP
        plot_widget.showGrid(x=True, y=True, alpha=0.5)  # Visible grid
        plot_widget.getAxis('bottom').setPen(pg.mkPen('#2c313a', width=1))
        plot_widget.getAxis('left').setPen(pg.mkPen('#2c313a', width=1))
        plot_widget.getAxis('bottom').setTextPen('#d1d5db')
        plot_widget.getAxis('left').setTextPen('#d1d5db')

        plot_widget.setMenuEnabled(False)
        view_box.setMouseEnabled(x=False, y=False)

        # Set padding for plot
        view_box.setDefaultPadding(0.0)

        # Set title with spacing
        plot_widget.setTitle(title, color='#4a7d89', size='12pt')

        # Add spacing between title row and plot area row
        plot_item = plot_widget.getPlotItem()
        plot_item.layout.setRowSpacing(0, 12)  # Space between title and plot

        # Create legend as a separate widget
        # Wrapper for legend with top spacing
        legend_wrapper = QWidget()
        legend_wrapper.setMaximumWidth(150)
        legend_wrapper_layout = QVBoxLayout(legend_wrapper)
        legend_wrapper_layout.setContentsMargins(0, 0, 0, 0)
        legend_wrapper_layout.setSpacing(0)

        # Add spacer to align legend with top of plot area
        top_spacer = QSpacerItem(0, 41, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        legend_wrapper_layout.addItem(top_spacer)

        legend_widget = QFrame()
        legend_widget.setStyleSheet("""
            QFrame {
                background-color: #11151c;
                border: 1px solid #2c313a;
                border-radius: 6px;
            }
        """)
        legend_widget.setSizePolicy(
            legend_widget.sizePolicy().Policy.Fixed,
            legend_widget.sizePolicy().Policy.Maximum  # Fit content height, don't expand
        )

        legend_layout = QVBoxLayout(legend_widget)
        legend_layout.setContentsMargins(8, 8, 8, 8)
        legend_layout.setSpacing(6)
        legend_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        legend_wrapper_layout.addWidget(legend_widget)
        legend_wrapper_layout.addStretch()  # Push everything to top

        # Add plot and legend to container
        layout.addWidget(plot_widget, 1)  # Plot stretches
        layout.addWidget(legend_wrapper, 0, Qt.AlignmentFlag.AlignTop)  # Legend wrapper fixed

        # Store references
        container._plot_widget = plot_widget
        container._legend_layout = legend_layout
        container._legend_items = []

        self._plot_legends[container] = legend_layout
        return container

    def _get_plot_from_container(self, container) -> pg.PlotWidget:
        """Extract the PlotWidget from container."""
        return container._plot_widget

    def _add_legend_item(self, container, color: str, label: str):
        """Add a legend item to the external legend."""
        item_widget = QWidget()
        item_widget.setStyleSheet("background-color: transparent;")
        item_widget.setContentsMargins(0, 3, 0, 3)  # Vertical margins for spacing
        item_layout = QHBoxLayout(item_widget)
        item_layout.setContentsMargins(0, 0, 0, 0)
        item_layout.setSpacing(10)

        # Color box
        color_label = QLabel()
        color_label.setStyleSheet(f"""
            QLabel {{
                background-color: {color};
                border-radius: 2px;
                min-width: 30px;
                max-width: 30px;
                min-height: 3px;
                max-height: 3px;
            }}
        """)

        # Text label
        text_label = QLabel(label)
        text_label.setStyleSheet("QLabel { color: #d1d5db; font-size: 10pt; }")

        item_layout.addWidget(color_label)
        item_layout.addWidget(text_label)
        item_layout.addStretch()

        container._legend_layout.addWidget(item_widget)
        container._legend_items.append(item_widget)

    def load_dataset(self, dataset: ResultDataset) -> None:
        """Load data and generate plots from a ResultDataset."""
        self.current_dataset = dataset
        self._current_selection.clear()
        self._average_plot_item = None

        self.clear_plots()

        df = dataset.data
        if df.empty:
            return

        config = dataset.config

        if config.plot_mode == "building_profile":
            self.tabs.tabBar().hide()  # Hide tabs for clean single plot view
            self._plot_building_profile(dataset)
        else:
            self.tabs.tabBar().show()  # Show tabs for other result types
            # Generate standard plots for other result types
            self._plot_envelope(dataset)
            self._plot_comparison(dataset)
            self._plot_profile(dataset)

    def _data_columns(self, dataset: ResultDataset) -> list[str]:
        """Return columns that represent load cases (exclude Story and summaries)."""
        return list(dataset.load_case_columns)

    def _plot_envelope(self, dataset: ResultDataset):
        """Plot envelope values by story."""
        container = self.envelope_plot
        plot = self._get_plot_from_container(container)
        self._reset_plot(container)

        df = dataset.data
        stories = df['Story'].tolist()
        story_indices = list(range(len(stories)))

        # Get numeric columns (exclude 'Story' column)
        numeric_cols = self._data_columns(dataset)

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

        # Add to external legend
        self._add_legend_item(container, '#4a7d89', f"Max {result_type}")

        # Configure axes
        axis = plot.getAxis('bottom')
        axis.setTicks([[(i, name) for i, name in enumerate(stories)]])
        plot.setLabel('bottom', 'Story')
        plot.setLabel('left', dataset.config.y_label)

        # Update title
        plot.setTitle(
            f"Maximum {dataset.meta.display_name} by Story",
            color='#4a7d89',
            size='12pt',
        )

    def _plot_comparison(self, dataset: ResultDataset):
        """Plot load case comparison."""
        container = self.comparison_plot
        plot = self._get_plot_from_container(container)
        self._reset_plot(container)

        df = dataset.data
        stories = df['Story'].tolist()
        story_indices = list(range(len(stories)))

        # Get numeric columns
        numeric_cols = self._data_columns(dataset)

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

            plot.plot(
                story_indices,
                values,
                pen=pg.mkPen(color, width=2),
                symbol='o',
                symbolSize=6,
                symbolBrush=color
            )
            self._add_legend_item(container, color, col)

        # Configure axes
        axis = plot.getAxis('bottom')
        axis.setTicks([[(i, name) for i, name in enumerate(stories)]])
        plot.setLabel('bottom', 'Story')
        plot.setLabel('left', dataset.config.y_label)

        # Update title
        plot.setTitle(
            f"{dataset.meta.display_name} - Load Case Comparison",
            color='#4a7d89',
            size='12pt',
        )

    def _plot_profile(self, dataset: ResultDataset):
        """Plot building profile (story height vs max value)."""
        container = self.profile_plot
        plot = self._get_plot_from_container(container)
        self._reset_plot(container)

        df = dataset.data
        stories = df['Story'].tolist()
        story_indices = list(range(len(stories)))

        # Get numeric columns
        numeric_cols = self._data_columns(dataset)

        if not numeric_cols:
            return

        # Calculate max and average for profile
        max_values = df[numeric_cols].max(axis=1).tolist()
        avg_values = df[numeric_cols].mean(axis=1).tolist()

        # Plot as horizontal bars (swap x and y)
        # Max envelope
        plot.plot(
            max_values,
            story_indices,
            pen=pg.mkPen('#e74c3c', width=2),
            symbol='o',
            symbolSize=6,
            symbolBrush='#e74c3c'
        )
        self._add_legend_item(container, '#e74c3c', 'Maximum')

        # Average
        plot.plot(
            avg_values,
            story_indices,
            pen=pg.mkPen('#4a7d89', width=2, style=Qt.PenStyle.DashLine),
            symbol='s',
            symbolSize=5,
            symbolBrush='#4a7d89'
        )
        self._add_legend_item(container, '#4a7d89', 'Average')

        # Configure axes
        axis = plot.getAxis('left')
        axis.setTicks([[(i, name) for i, name in enumerate(stories)]])
        plot.setLabel('left', 'Story')
        plot.setLabel('bottom', dataset.config.y_label)

        # Update title
        plot.setTitle(
            f"{dataset.meta.display_name} - Building Profile", color='#4a7d89', size='12pt'
        )

    def _plot_building_profile(self, dataset: ResultDataset):
        """Plot building profile - drift vs height."""
        # Use the envelope plot for the main view
        container = self.envelope_plot
        plot = self._get_plot_from_container(container)
        self._reset_plot(container)

        df = dataset.data
        stories = df['Story'].tolist()
        story_indices = list(range(len(stories)))

        # Get numeric columns (load cases)
        load_case_columns = self._data_columns(dataset)

        if not load_case_columns:
            return

        # Clear plot items dictionary
        self._plot_items.clear()
        self._average_plot_item = None

        # Highly distinct colors optimized for dark backgrounds
        colors = [
            '#ff4757',  # Bright red
            '#1e90ff',  # Dodger blue
            '#2ed573',  # Bright green
            '#ff6348',  # Tomato/coral
            '#a29bfe',  # Periwinkle
            '#00d2d3',  # Cyan
            '#ffa502',  # Orange (different from average)
            '#ff6b81',  # Pink
            '#5f27cd',  # Purple
            '#01a3a4',  # Teal
            '#48dbfb',  # Sky blue
            '#c44569',  # Dark pink
            '#f8b500',  # Golden yellow
        ]

        numeric_df = df[load_case_columns].apply(pd.to_numeric, errors='coerce')

        # Plot each load case as a line
        for idx, load_case in enumerate(load_case_columns):
            numeric_values = numeric_df[load_case].fillna(0.0).tolist()
            color = colors[idx % len(colors)]

            # Plot horizontal (drift on x-axis, story on y-axis)
            plot_item = plot.plot(
                numeric_values,
                story_indices,
                pen=pg.mkPen(color, width=2)
            )
            # Store the plot item for later highlighting
            self._plot_items[load_case] = {'item': plot_item, 'color': color, 'width': 2}

            self._add_legend_item(container, color, load_case)

        # Calculate and plot average line (bold, dashed)
        if len(load_case_columns) > 1:
            avg_series = numeric_df.mean(axis=1, skipna=True).fillna(0.0)
            avg_values = avg_series.tolist()

            # Plot average with bold, dashed line in bright orange
            self._average_plot_item = plot.plot(
                avg_values,
                story_indices,
                pen=pg.mkPen('#ffa500', width=4, style=Qt.PenStyle.DashLine)  # Bright orange
            )
            self._add_legend_item(container, '#ffa500', 'Average')

        # Use PlotBuilder for common configuration
        builder = PlotBuilder(plot, dataset.config)

        # Configure axes with story labels
        builder.setup_axes(stories)

        # Set y-axis range with tight padding
        builder.set_story_range(len(stories), padding=0.02)

        # Calculate x-axis range from all values
        all_values = [
            float(value)
            for value in numeric_df.to_numpy().flatten()
            if not pd.isna(value)
        ]

        # Filter out zeros and set range with small padding
        all_values = [v for v in all_values if abs(v) > 0.0]
        if all_values:
            min_val = min(all_values)
            max_val = max(all_values)
            # Small padding (3% on left, 5% on right for legend/label space)
            builder.set_value_range(min_val, max_val, left_padding=0.03, right_padding=0.05)

            # Set dynamic tick spacing (6 intervals based on data range)
            builder.set_dynamic_tick_spacing('bottom', min_val, max_val, num_intervals=6)

        # Enable grid with increased visibility
        plot.showGrid(x=True, y=True, alpha=0.5)

        # Set title
        builder.set_title(dataset.meta.display_name)

    def highlight_load_cases(self, selected_cases: list):
        """Highlight multiple selected load cases, dim others, always show average at full opacity."""
        # Store current selection for hover state restoration
        self._current_selection = set(selected_cases) if selected_cases else set()

        if not selected_cases:
            # No selection - restore all to full opacity
            for case_name, case_data in self._plot_items.items():
                item = case_data['item']
                color = case_data['color']
                width = case_data['width']
                item.setPen(pg.mkPen(color, width=width))
        else:
            # Highlight selected cases, dim others
            selected_set = set(selected_cases)

            for case_name, case_data in self._plot_items.items():
                item = case_data['item']
                color = case_data['color']
                width = case_data['width']

                if case_name in selected_set:
                    # Selected case - full opacity, slightly thicker
                    item.setPen(pg.mkPen(color, width=width + 1))
                else:
                    # Non-selected case - reduce opacity significantly
                    from PyQt6.QtGui import QColor
                    qcolor = QColor(color)
                    qcolor.setAlpha(40)  # Much lower opacity (0-255 scale, 40 is ~15%)
                    item.setPen(pg.mkPen(qcolor, width=width))

        # Always keep average line at full opacity and bold
        if hasattr(self, '_average_plot_item') and self._average_plot_item:
            self._average_plot_item.setPen(
                pg.mkPen('#ffa500', width=4, style=Qt.PenStyle.DashLine)
            )

    def hover_load_case(self, load_case: str):
        """Temporarily highlight a load case on hover (increase thickness and dim others subtly)."""
        if load_case not in self._plot_items:
            return

        from PyQt6.QtGui import QColor

        # Get current selection state
        current_selection = getattr(self, '_current_selection', set())

        for case_name, case_data in self._plot_items.items():
            item = case_data['item']
            color = case_data['color']
            width = case_data['width']

            if case_name == load_case:
                # Hovered case - make it prominent with thicker line
                item.setPen(pg.mkPen(color, width=width + 2))
            elif case_name in current_selection:
                # Selected but not hovered - keep visible with slight dim
                qcolor = QColor(color)
                qcolor.setAlpha(180)  # Still quite visible (~70%)
                item.setPen(pg.mkPen(qcolor, width=width + 1))
            else:
                # Not selected and not hovered - moderate opacity reduction
                qcolor = QColor(color)
                qcolor.setAlpha(100)  # Medium opacity (~39%)
                item.setPen(pg.mkPen(qcolor, width=width))

        # Keep average at full opacity
        if hasattr(self, '_average_plot_item') and self._average_plot_item:
            self._average_plot_item.setPen(
                pg.mkPen('#ffa500', width=4, style=Qt.PenStyle.DashLine)
            )

    def clear_hover(self):
        """Clear hover effect and restore to selected state."""
        # Restore to the current selection state
        if hasattr(self, '_current_selection'):
            self.highlight_load_cases(list(self._current_selection))
        else:
            self.highlight_load_cases([])

    def clear_plots(self):
        """Clear all plots."""
        self._reset_plot(self.envelope_plot)
        self._reset_plot(self.comparison_plot)
        self._reset_plot(self.profile_plot)
        self._plot_items.clear()
        self._highlighted_case = None
        self._average_plot_item = None
        self.current_dataset = None

    def _reset_plot(self, container):
        """Clear plot curves and legend entries."""
        plot = self._get_plot_from_container(container)
        plot.clear()

        # Clear external legend
        for item in container._legend_items:
            container._legend_layout.removeWidget(item)
            item.deleteLater()
        container._legend_items.clear()
