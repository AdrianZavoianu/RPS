"""Beam Rotations widget - displays R3 plastic rotation data with table and plot tabs."""

import numpy as np
import pandas as pd
import pyqtgraph as pg
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QVBoxLayout,
    QWidget,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
)

from .styles import COLORS
from .design_tokens import PALETTE


class BeamRotationsWidget(QWidget):
    """Widget for displaying beam rotations with table and plot tabs."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_data_max = None
        self.current_data_min = None
        self.current_mode = "table"  # "table" or "plot"
        self.setup_ui()

    def setup_ui(self):
        """Setup the UI with tab widget containing table and plot."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Create tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {COLORS['border']};
                background-color: {COLORS['background']};
            }}
            QTabBar::tab {{
                background-color: {COLORS['card']};
                color: {COLORS['muted']};
                padding: 8px 16px;
                border: 1px solid {COLORS['border']};
                border-bottom: none;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background-color: {COLORS['background']};
                color: {COLORS['accent']};
            }}
            QTabBar::tab:hover {{
                color: {COLORS['text']};
            }}
        """)

        # Table tab
        self.table_widget = QTableWidget()
        self.table_widget.setStyleSheet(f"""
            QTableWidget {{
                background-color: {COLORS['background']};
                border: none;
                gridline-color: #1e2329;
                color: {COLORS['text']};
            }}
            QTableWidget::item {{
                padding: 4px 8px;
                border: none;
            }}
            QHeaderView {{
                background-color: {COLORS['card']};
            }}
            QHeaderView::section {{
                background-color: {COLORS['card']};
                color: {COLORS['accent']};
                padding: 4px 4px;
                border: none;
                border-right: 1px solid #1e2329;
                border-bottom: 1px solid #1e2329;
                font-weight: 600;
            }}
            QHeaderView::section:last {{
                border-right: none;
            }}
        """)
        self.tab_widget.addTab(self.table_widget, "Table")

        # Plot tab
        self.plot_container = QWidget()
        plot_layout = QVBoxLayout(self.plot_container)
        plot_layout.setContentsMargins(0, 0, 0, 0)

        # Create plot widget using factory
        from gui.components.plot_factory import create_plot_widget
        self.plot_widget = create_plot_widget()

        # Set title
        self.plot_widget.setTitle("Beam R3 Plastic Rotations", color=PALETTE['accent_primary'], size='12pt')

        # Add spacing between title and plot
        plot_item = self.plot_widget.getPlotItem()
        plot_item.layout.setRowSpacing(0, 12)

        plot_layout.addWidget(self.plot_widget)
        self.tab_widget.addTab(self.plot_container, "Plot")

        # Connect tab change signal
        self.tab_widget.currentChanged.connect(self._on_tab_changed)

        layout.addWidget(self.tab_widget)

    def _on_tab_changed(self, index):
        """Handle tab changes."""
        if index == 0:
            self.current_mode = "table"
        else:
            self.current_mode = "plot"

    def load_dataset(self, df_max: pd.DataFrame, df_min: pd.DataFrame, element_name: str):
        """Load and display beam rotation data (both Max and Min).

        Args:
            df_max: DataFrame with Max rotation data
            df_min: DataFrame with Min rotation data
            element_name: Name of the beam element
        """
        if (df_max is None or df_max.empty) and (df_min is None or df_min.empty):
            self.clear_data()
            return

        self.current_data_max = df_max
        self.current_data_min = df_min

        # Update plot title with element name
        self.plot_widget.setTitle(f"{element_name} - R3 Plastic Rotations", color=PALETTE['accent_primary'], size='12pt')

        # Update table (show Max data by default, or Min if Max not available)
        df_display = df_max if df_max is not None and not df_max.empty else df_min
        if df_display is not None and not df_display.empty:
            self._update_table(df_display)

        # Update plot
        self._plot_combined_scatter(df_max, df_min)

    def _update_table(self, df: pd.DataFrame):
        """Update table view with rotation data."""
        # Create display dataframe with relevant columns
        display_df = df[['Story', 'LoadCase', 'Rotation']].copy()

        # Clear and configure table
        self.table_widget.clear()
        self.table_widget.setRowCount(len(display_df))
        self.table_widget.setColumnCount(3)
        self.table_widget.setHorizontalHeaderLabels(['Story', 'Load Case', 'R3 Plastic (%)'])

        # Populate table
        for row_idx, (_, row) in enumerate(display_df.iterrows()):
            # Story
            story_item = QTableWidgetItem(str(row['Story']))
            self.table_widget.setItem(row_idx, 0, story_item)

            # Load Case
            case_item = QTableWidgetItem(str(row['LoadCase']))
            self.table_widget.setItem(row_idx, 1, case_item)

            # Rotation (percentage value, no unit suffix)
            rotation_value = row['Rotation']
            rotation_item = QTableWidgetItem(f"{rotation_value:.2f}")
            self.table_widget.setItem(row_idx, 2, rotation_item)

        # Resize columns to content
        self.table_widget.resizeColumnsToContents()

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
        story_names = list(reversed(story_names_excel_order))
        num_stories = len(story_names)

        # Create story index mapping (0, 1, 2, ... for Y axis)
        story_to_index = {name: idx for idx, name in enumerate(story_names)}

        all_x_values = []

        # Define single orange color for all markers
        orange_color = QColor('#f97316')

        # Plot Max data points (small orange circles)
        if df_max is not None and not df_max.empty:
            x_max, y_max = self._prepare_scatter_data(df_max, story_to_index, "Max")
            if x_max:
                scatter_max = pg.ScatterPlotItem(
                    x=x_max,
                    y=y_max,
                    size=4,
                    pen=pg.mkPen(None),
                    brush=pg.mkBrush(orange_color),
                    symbol='o',
                )
                self.plot_widget.addItem(scatter_max)
                all_x_values.extend(x_max)

        # Plot Min data points (small orange circles)
        if df_min is not None and not df_min.empty:
            x_min, y_min = self._prepare_scatter_data(df_min, story_to_index, "Min")
            if x_min:
                scatter_min = pg.ScatterPlotItem(
                    x=x_min,
                    y=y_min,
                    size=4,
                    pen=pg.mkPen(None),
                    brush=pg.mkBrush(orange_color),
                    symbol='o',
                )
                self.plot_widget.addItem(scatter_min)
                all_x_values.extend(x_min)

        # Add vertical line at x=0 to show center
        zero_line = pg.InfiniteLine(pos=0, angle=90, pen=pg.mkPen(PALETTE['accent_primary'], width=1, style=Qt.PenStyle.DashLine))
        self.plot_widget.addItem(zero_line)

        # Configure Y-axis with story labels
        y_axis = self.plot_widget.getAxis('left')
        y_ticks = [(idx, name) for idx, name in enumerate(story_names)]
        y_axis.setTicks([y_ticks])

        # Set Y-axis range with padding
        self.plot_widget.setYRange(-0.5, num_stories - 0.5, padding=0)

        # Set X-axis label
        self.plot_widget.setLabel('bottom', 'R3 Plastic Rotation (%)')
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
            Tuple of (x_values, y_values)
        """
        x_values = []
        y_values = []

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

        return x_values, y_values

    def clear_data(self):
        """Clear all data from table and plot."""
        self.table_widget.clear()
        self.plot_widget.clear()
        self.current_data_max = None
        self.current_data_min = None

    def set_active_tab(self, tab_name: str):
        """Set the active tab.

        Args:
            tab_name: "table" or "plot"
        """
        if tab_name == "table":
            self.tab_widget.setCurrentIndex(0)
        elif tab_name == "plot":
            self.tab_widget.setCurrentIndex(1)
