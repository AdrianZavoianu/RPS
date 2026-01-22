"""Reusable view combining table and plot for result set comparisons."""

from __future__ import annotations

import pandas as pd
import pyqtgraph as pg
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gui.styles import COLORS
from services.result_service import ComparisonDataset
from utils.color_utils import get_gradient_color

from ..results_table_widget import ResultsTableWidget


class ComparisonPlotWidget(QWidget):
    """Simple plot widget for comparison view without tabs."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._plot_items = {}
        self._average_plot_item = None
        self.setup_ui()

    def setup_ui(self):
        """Setup the plot UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Configure PyQtGraph
        pg.setConfigOptions(antialias=True)
        pg.setConfigOption('background', '#0a0c10')
        pg.setConfigOption('foreground', '#d1d5db')

        # Create single plot container
        self.plot_container = self._create_plot_widget()
        layout.addWidget(self.plot_container)

    def _create_plot_widget(self) -> QWidget:
        """Create a styled PyQtGraph plot widget with external legend."""
        container = QWidget()
        main_layout = QHBoxLayout(container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(8)

        # Create the plot using factory
        from gui.components.plot_factory import create_plot_widget
        plot_widget = create_plot_widget()

        main_layout.addWidget(plot_widget, 1)  # Plot takes available space

        # Create external legend container on the right side
        legend_container = QWidget()
        legend_container.setStyleSheet(f"background-color: transparent;")
        legend_layout = QVBoxLayout(legend_container)
        legend_layout.setContentsMargins(12, 0, 0, 0)  # Add left padding
        legend_layout.setSpacing(8)
        legend_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        main_layout.addWidget(legend_container, 0)  # Legend doesn't stretch

        # Store references
        container._plot_widget = plot_widget
        container._legend_layout = legend_layout
        container._legend_items = []
        container._legend_col = 0

        return container

    def _get_plot_from_container(self, container) -> pg.PlotWidget:
        """Extract the PlotWidget from container."""
        return container._plot_widget

    def _add_legend_item(self, container, color: str, label: str):
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

        container._legend_layout.addWidget(legend_item)
        container._legend_items.append(legend_item)

    def clear_plots(self):
        """Clear the plot."""
        self._reset_plot(self.plot_container)
        self._plot_items.clear()
        self._average_plot_item = None

    def _reset_plot(self, container):
        """Clear plot curves and legend entries."""
        plot = self._get_plot_from_container(container)
        plot.clear()

        # Clear external legend
        for item in container._legend_items:
            container._legend_layout.removeWidget(item)
            item.deleteLater()
        container._legend_items.clear()
        container._legend_col = 0


class ComparisonTableWidget(ResultsTableWidget):
    """Table widget for comparison data with missing data handling."""

    def load_comparison_dataset(self, dataset: ComparisonDataset) -> None:
        """Load comparison dataset into table with missing data handling."""
        self.clear_data()

        if dataset.data.empty:
            return

        # Set up table
        self.table.setRowCount(len(dataset.data))
        self.table.setColumnCount(len(dataset.data.columns))
        self.table.setHorizontalHeaderLabels(list(dataset.data.columns))

        # Populate table
        for row_idx, (_, row) in enumerate(dataset.data.iterrows()):
            for col_idx, (col_name, value) in enumerate(row.items()):
                item = QTableWidgetItem()

                if col_name == "Story":
                    # Story column - centered
                    item.setText(str(value))
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                elif pd.isna(value):
                    # Missing data - centered
                    item.setText("—")
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    item.setForeground(QColor(COLORS['muted']))
                else:
                    # Numeric value - centered
                    is_ratio = "/" in col_name

                    if is_ratio:
                        # Ratio column - always 2 decimal places, no unit
                        formatted_value = f"{value:.2f}"
                    else:
                        # Regular result column - use config decimal places (no unit suffix)
                        formatted_value = f"{value:.{dataset.config.decimal_places}f}"

                    item.setText(formatted_value)
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                    # Apply gradient color for non-ratio columns
                    if not is_ratio:
                        min_val = dataset.data[col_name].min()
                        max_val = dataset.data[col_name].max()
                        if pd.notna(min_val) and pd.notna(max_val):
                            color = get_gradient_color(
                                value,
                                min_val,
                                max_val,
                                dataset.config.color_scheme
                            )
                            item.setForeground(color)
                            item._original_color = QColor(color)

                self.table.setItem(row_idx, col_idx, item)

        # Resize columns to fit content
        self.table.resizeColumnsToContents()

        # Calculate total width needed
        total_width = sum(self.table.columnWidth(i) for i in range(self.table.columnCount())) + 2

        # Set table to exact content width (no scrolling, no max width)
        self.table.setMinimumWidth(total_width)
        self.table.setMaximumWidth(total_width)
        self.setMinimumWidth(total_width)
        self.setMaximumWidth(total_width)


class ComparisonResultView(QWidget):
    """Container widget hosting table and plot for result set comparisons."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.table = ComparisonTableWidget()
        self.plot = ComparisonPlotWidget()
        self.warnings_banner = None
        self._initial_sizes_set = False

        self._configure_layout()
        self._connect_signals()

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def showEvent(self, event) -> None:
        """Set splitter proportions after widget is shown."""
        super().showEvent(event)
        if not self._initial_sizes_set:
            QTimer.singleShot(0, self._apply_splitter_proportions)
            self._initial_sizes_set = True

    def set_dataset(self, dataset: ComparisonDataset) -> None:
        """Populate the table and plot with the provided comparison dataset."""
        # Show/hide warnings banner
        if dataset.warnings:
            if not self.warnings_banner:
                self._create_warnings_banner()
            self._update_warnings(dataset.warnings)
            self.warnings_banner.show()
        else:
            if self.warnings_banner:
                self.warnings_banner.hide()

        # Load data into table
        self.table.load_comparison_dataset(dataset)

        # Load data into plot (multi-series)
        self._load_plot(dataset)

        # Force splitter proportions
        QTimer.singleShot(100, self._apply_splitter_proportions)

    def clear(self) -> None:
        """Reset table, plot, and warnings."""
        self.table.clear_data()
        self.plot.clear_plots()
        if self.warnings_banner:
            self.warnings_banner.hide()

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _apply_splitter_proportions(self) -> None:
        """Let table take minimum width needed, give remaining space to plot."""
        pass

    def _configure_layout(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Splitter for table and plot
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(16)
        splitter.setStyleSheet(
            """
            QSplitter {
                padding: 0px;
                margin: 0px;
            }
            QSplitter::handle {
                background-color: transparent;
                margin: 0px 8px;
            }
            """
        )

        splitter.addWidget(self.table)
        splitter.addWidget(self.plot)

        # Table doesn't stretch, plot takes all remaining space
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter)

        self._splitter = splitter

    def _create_warnings_banner(self) -> None:
        """Create warnings banner (inserted at top of layout)."""
        self.warnings_banner = QWidget()
        banner_layout = QHBoxLayout(self.warnings_banner)
        banner_layout.setContentsMargins(16, 12, 16, 12)
        banner_layout.setSpacing(12)

        # Warning icon
        icon_label = QLabel("⚠")
        icon_label.setStyleSheet(f"color: {COLORS['warning']}; font-size: 16px; font-weight: bold;")

        # Warning text
        self.warnings_text = QLabel()
        self.warnings_text.setWordWrap(True)
        self.warnings_text.setStyleSheet(f"color: {COLORS['text']}; font-size: 13px;")

        # Dismiss button
        dismiss_btn = QPushButton("✗")
        dismiss_btn.setFixedSize(24, 24)
        dismiss_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                color: {COLORS['muted']};
                font-size: 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                color: {COLORS['text']};
            }}
        """)
        dismiss_btn.clicked.connect(lambda: self.warnings_banner.hide())

        banner_layout.addWidget(icon_label)
        banner_layout.addWidget(self.warnings_text, 1)
        banner_layout.addWidget(dismiss_btn)

        # Styling
        self.warnings_banner.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS['warning_bg']};
                border: 1px solid {COLORS['warning']};
                border-radius: 6px;
            }}
        """)

        # Insert at top of layout
        self.layout().insertWidget(0, self.warnings_banner)
        self.warnings_banner.hide()

    def _update_warnings(self, warnings: list[str]) -> None:
        """Update warnings banner text."""
        if not warnings:
            return

        if len(warnings) == 1:
            text = warnings[0]
        else:
            text = f"{len(warnings)} warnings:\n" + "\n".join(f"• {w}" for w in warnings)

        self.warnings_text.setText(text)

    def _load_plot(self, dataset: ComparisonDataset) -> None:
        """Load comparison data into plot as multiple series."""
        self.plot.clear_plots()

        if dataset.data.empty:
            return

        # Get stories
        stories = dataset.data['Story'].tolist()

        # Get all result set columns (exclude Story and ratio columns)
        result_set_cols = [
            col for col in dataset.data.columns
            if col != 'Story' and "/" not in col
        ]

        # Create series for each result set with data
        series_list = []
        for col in result_set_cols:
            values = dataset.data[col].tolist()

            # Skip if all NaN
            import pandas as pd
            if all(pd.isna(v) for v in values):
                continue

            # Extract result set name from column (e.g., "DES_Avg" → "DES")
            result_set_name = col.rsplit('_', 1)[0]

            series_list.append({
                'name': result_set_name,
                'x_values': values,
                'y_values': list(range(len(stories))),
                'stories': stories
            })

        # Load into plot widget
        if series_list:
            self._plot_multi_series(dataset, series_list)

    def _plot_multi_series(self, dataset: ComparisonDataset, series_list: list) -> None:
        """Plot multiple result set series on building profile."""
        if not series_list:
            return

        import pyqtgraph as pg
        from PyQt6.QtCore import Qt
        from utils.plot_builder import PlotBuilder
        import pandas as pd

        # Get plot widget's main plot
        plot = self.plot._get_plot_from_container(self.plot.plot_container)
        self.plot._reset_plot(self.plot.plot_container)

        # Story setup
        stories = series_list[0]['stories']
        story_labels = stories
        story_positions = list(range(len(stories)))

        # Define colors for each result set
        colors = [
            '#3b82f6',  # Blue
            '#ef4444',  # Red
            '#10b981',  # Green
            '#f59e0b',  # Orange
            '#8b5cf6',  # Purple
            '#ec4899',  # Pink
        ]

        # Clear plot items
        self.plot._plot_items.clear()
        self.plot._average_plot_item = None

        # Plot each result set series
        for idx, series_data in enumerate(series_list):
            values = series_data['x_values']
            result_set_name = series_data['name']

            # Convert NaN to 0 for plotting
            import pandas as pd
            numeric_values = [0.0 if pd.isna(v) else v for v in values]

            # Use cycling colors
            color = colors[idx % len(colors)]

            # Plot the series
            plot_item = plot.plot(
                numeric_values,
                story_positions,
                pen=pg.mkPen(color, width=3)
            )

            # Store plot item for potential interaction
            self.plot._plot_items[result_set_name] = {
                'item': plot_item,
                'color': color,
                'width': 3
            }

            # Add to legend
            self.plot._add_legend_item(self.plot.plot_container, color, result_set_name)

        # Use PlotBuilder for axes configuration
        builder = PlotBuilder(plot, dataset.config)
        builder.setup_axes(story_labels)

        # Set y-axis range
        builder.set_story_range(len(story_labels), padding=0.02)

        # Set x-axis range based on all series data
        all_values = []
        for series_data in series_list:
            all_values.extend([v for v in series_data['x_values'] if pd.notna(v)])

        if all_values:
            min_val = min(all_values)
            max_val = max(all_values)
            builder.set_value_range(min_val, max_val, left_padding=0.03, right_padding=0.05)
            builder.set_dynamic_tick_spacing('bottom', min_val, max_val, num_intervals=6)

    def _connect_signals(self) -> None:
        """Connect table and plot signals (limited for comparison view)."""
        # Note: Comparison view doesn't have load case selection like standard view
        # Table interaction is view-only
        pass
