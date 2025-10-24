"""Visualization widget using PyQtGraph for high-performance plotting."""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QHBoxLayout,
    QPushButton,
    QTabWidget,
)
import pyqtgraph as pg


class VisualizationWidget(QWidget):
    """Widget for visualizing results with PyQtGraph."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._create_ui()

    def _create_ui(self):
        """Create modern visualization UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header with modern card-style
        header_widget = QWidget()
        header_widget.setStyleSheet(f"""
            background-color: #161b22;
            border-bottom: 1px solid #2c313a;
            padding: 16px;
        """)
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(20, 16, 20, 16)

        # Title section
        title_layout = QVBoxLayout()
        title_layout.setSpacing(4)

        header_label = QLabel("Visualization")
        header_label.setStyleSheet("font-size: 18px; font-weight: 600; padding: 0; background: transparent;")

        subtitle_label = QLabel("Interactive plots and analysis")
        subtitle_label.setProperty("styleClass", "muted")
        subtitle_label.setStyleSheet("font-size: 13px; padding: 0; background: transparent;")

        title_layout.addWidget(header_label)
        title_layout.addWidget(subtitle_label)

        header_layout.addLayout(title_layout)
        header_layout.addStretch()

        # Export button
        export_button = QPushButton("⊞ Export")
        export_button.setMinimumHeight(36)
        export_button.setProperty("styleClass", "secondary")
        export_button.clicked.connect(self._on_export)
        header_layout.addWidget(export_button)

        layout.addWidget(header_widget)

        # Tab widget for different plot types with modern styling
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background-color: #0a0c10;
                padding: 16px;
            }
            QTabBar::tab {
                padding: 12px 24px;
                margin-right: 4px;
                font-size: 13px;
            }
        """)

        # Time-history tab
        self.time_history_widget = self._create_time_history_tab()
        self.tabs.addTab(self.time_history_widget, "≡ Time History")

        # Envelope tab
        self.envelope_widget = self._create_envelope_tab()
        self.tabs.addTab(self.envelope_widget, "▤ Envelope")

        # Comparison tab
        self.comparison_widget = self._create_comparison_tab()
        self.tabs.addTab(self.comparison_widget, "◐ Comparison")

        layout.addWidget(self.tabs)

    def _create_time_history_tab(self):
        """Create time-history plot tab with modern dark theme."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create PyQtGraph plot widget with dark theme
        self.time_plot = pg.PlotWidget()
        self.time_plot.setBackground('#0a0c10')
        self.time_plot.setLabel("left", "Value", color='#d1d5db', **{'font-size': '11pt'})
        self.time_plot.setLabel("bottom", "Time", units="s", color='#d1d5db', **{'font-size': '11pt'})
        self.time_plot.showGrid(x=True, y=True, alpha=0.15)
        self.time_plot.addLegend(brush='#161b22', labelTextColor='#d1d5db')

        # Style the axes
        self.time_plot.getAxis('left').setPen('#2c313a')
        self.time_plot.getAxis('bottom').setPen('#2c313a')
        self.time_plot.getAxis('left').setTextPen('#d1d5db')
        self.time_plot.getAxis('bottom').setTextPen('#d1d5db')

        # Add placeholder text with modern styling
        text = pg.TextItem(
            "Select results from the browser to visualize",
            anchor=(0.5, 0.5),
            color='#7f8b9a'
        )
        text.setPos(0.5, 0.5)
        self.time_plot.addItem(text)

        layout.addWidget(self.time_plot)

        return widget

    def _create_envelope_tab(self):
        """Create envelope plot tab with modern dark theme."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create PyQtGraph plot widget with dark theme
        self.envelope_plot = pg.PlotWidget()
        self.envelope_plot.setBackground('#0a0c10')
        self.envelope_plot.setLabel("left", "Story", color='#d1d5db', **{'font-size': '11pt'})
        self.envelope_plot.setLabel("bottom", "Value", color='#d1d5db', **{'font-size': '11pt'})
        self.envelope_plot.showGrid(x=True, y=True, alpha=0.15)

        # Style the axes
        self.envelope_plot.getAxis('left').setPen('#2c313a')
        self.envelope_plot.getAxis('bottom').setPen('#2c313a')
        self.envelope_plot.getAxis('left').setTextPen('#d1d5db')
        self.envelope_plot.getAxis('bottom').setTextPen('#d1d5db')

        layout.addWidget(self.envelope_plot)

        return widget

    def _create_comparison_tab(self):
        """Create comparison plot tab with modern dark theme."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create PyQtGraph plot widget with dark theme
        self.comparison_plot = pg.PlotWidget()
        self.comparison_plot.setBackground('#0a0c10')
        self.comparison_plot.setLabel("left", "Value", color='#d1d5db', **{'font-size': '11pt'})
        self.comparison_plot.setLabel("bottom", "Load Case", color='#d1d5db', **{'font-size': '11pt'})
        self.comparison_plot.showGrid(x=True, y=True, alpha=0.15)

        # Style the axes
        self.comparison_plot.getAxis('left').setPen('#2c313a')
        self.comparison_plot.getAxis('bottom').setPen('#2c313a')
        self.comparison_plot.getAxis('left').setTextPen('#d1d5db')
        self.comparison_plot.getAxis('bottom').setTextPen('#d1d5db')

        layout.addWidget(self.comparison_plot)

        return widget

    def on_selection_changed(self, selection):
        """Handle selection change from results browser."""
        # TODO: Load and plot selected data
        selected_name = selection.get("name", "")
        self.time_plot.setTitle(f"Selected: {selected_name}")

    def _on_export(self):
        """Export current plot to file."""
        # TODO: Implement plot export
        pass

    def plot_time_history(self, time_data, value_data, label="Data"):
        """Plot time-history data.

        Args:
            time_data: List or array of time values
            value_data: List or array of values
            label: Label for the plot legend
        """
        self.time_plot.clear()
        pen = pg.mkPen(color=(0, 0, 255), width=2)
        self.time_plot.plot(
            time_data, value_data, pen=pen, name=label, antialias=True
        )

    def plot_envelope(self, stories, max_values, min_values=None):
        """Plot envelope data by story.

        Args:
            stories: List of story names
            max_values: List of maximum values
            min_values: Optional list of minimum values
        """
        self.envelope_plot.clear()

        # Convert story names to numeric indices
        y_positions = list(range(len(stories)))

        # Plot max values
        pen_max = pg.mkPen(color=(255, 0, 0), width=2)
        self.envelope_plot.plot(
            max_values, y_positions, pen=pen_max, symbol="o", symbolSize=8
        )

        # Plot min values if provided
        if min_values:
            pen_min = pg.mkPen(color=(0, 0, 255), width=2)
            self.envelope_plot.plot(
                min_values, y_positions, pen=pen_min, symbol="s", symbolSize=8
            )

        # Set y-axis labels
        ax = self.envelope_plot.getAxis("left")
        ax.setTicks([[(i, stories[i]) for i in y_positions]])
