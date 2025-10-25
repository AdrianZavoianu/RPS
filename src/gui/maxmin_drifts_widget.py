"""Max/Min Results widget - displays positive and negative envelopes."""

import math
from typing import TYPE_CHECKING, Optional

import pandas as pd
import pyqtgraph as pg
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from config.result_config import get_config, RESULT_CONFIGS
from utils.plot_builder import PlotBuilder
from .styles import COLORS

if TYPE_CHECKING:
    from processing.result_service import MaxMinDataset


class InteractiveLegendItem(QWidget):
    """Interactive legend item that responds to hover and click."""

    def __init__(self, label: str, color: str, direction: str, parent_widget):
        super().__init__()
        self.label = label
        self.color = color
        self.direction = direction
        self.parent_widget = parent_widget
        self.is_selected = False

        # Set fixed border that's always visible
        self.setStyleSheet(f"""
            background-color: transparent;
            border-left: 3px solid {color};
            border-radius: 4px;
            padding-left: 4px;
        """)
        self.setContentsMargins(0, 3, 0, 3)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Color indicator
        self.color_label = QLabel()
        self.color_label.setStyleSheet(f"""
            QLabel {{
                background-color: {color};
                border: none;
                border-radius: 2px;
                min-width: 30px;
                max-width: 30px;
                min-height: 3px;
                max-height: 3px;
            }}
        """)

        # Text label (always bold to prevent layout shifts)
        self.text_label = QLabel(label)
        self.text_label.setStyleSheet("QLabel { color: #d1d5db; font-size: 10pt; font-weight: 600; }")

        layout.addWidget(self.color_label)
        layout.addWidget(self.text_label)
        layout.addStretch()

    def enterEvent(self, event):
        """Handle mouse enter - trigger hover highlight."""
        self.parent_widget.hover_load_case(self.label, self.direction)
        # Strong hover effect: white text + subtle background highlight
        self.setStyleSheet(f"""
            background-color: rgba(255, 255, 255, 0.08);
            border-left: 3px solid {self.color};
            border-radius: 4px;
            padding-left: 4px;
        """)
        self.text_label.setStyleSheet("QLabel { color: #ffffff; font-size: 10pt; font-weight: 600; }")
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Handle mouse leave - clear hover."""
        self.parent_widget.clear_hover(self.direction)
        # Restore to selection state (call set_selected to restore proper background and text)
        self.set_selected(self.is_selected)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        """Handle click - toggle selection."""
        self.parent_widget.toggle_load_case_selection(self.label, self.direction)
        super().mousePressEvent(event)

    def set_selected(self, selected: bool):
        """Update visual state based on selection."""
        self.is_selected = selected
        if selected:
            # Selected state: bright cyan text, cyan background highlight (border stays same color)
            self.setStyleSheet(f"""
                background-color: rgba(103, 232, 249, 0.15);
                border-left: 3px solid {self.color};
                border-radius: 4px;
                padding-left: 4px;
            """)
            self.text_label.setStyleSheet("QLabel { color: #67e8f9; font-size: 10pt; font-weight: 600; }")
        else:
            # Normal state: transparent background (border stays same color, text always bold)
            self.setStyleSheet(f"""
                background-color: transparent;
                border-left: 3px solid {self.color};
                border-radius: 4px;
                padding-left: 4px;
            """)
            self.text_label.setStyleSheet("QLabel { color: #d1d5db; font-size: 10pt; font-weight: 600; }")


class MaxMinDriftsWidget(QWidget):
    """Widget for displaying Max/Min drifts with plots and tables."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.current_data = None
        self.current_base_type = "Drifts"
        self.current_display_name = "Max/Min Drifts"

        # Track plot items for highlighting
        self.x_plot_items = {}  # {load_case: {'max_item': item, 'min_item': item, 'color': color}}
        self.y_plot_items = {}
        self.x_current_selection = set()
        self.y_current_selection = set()

        # Track manually selected rows for each table
        self._table_selected_rows = {}  # {table_id: set of row indices}

        # Direction containers for visibility toggling
        self.x_plot_container = None
        self.y_plot_container = None
        self.x_tables_container = None
        self.y_tables_container = None
        self.x_tables_label: Optional[QLabel] = None
        self.y_tables_label: Optional[QLabel] = None

    def setup_ui(self):
        """Setup the UI with tabs for Plots and Tables."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Tab widget
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                background-color: {COLORS['background']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 8px;
            }}
            QTabBar::tab {{
                background-color: transparent;
                color: {COLORS['muted']};
                border: none;
                padding: 10px 20px;
                margin-right: 4px;
                margin-bottom: 4px;
                font-size: 14px;
                border-radius: 6px;
            }}
            QTabBar::tab:hover {{
                color: {COLORS['text']};
                background-color: {COLORS['hover']};
            }}
            QTabBar::tab:selected {{
                color: {COLORS['accent']};
                background-color: rgba(74, 125, 137, 0.15);
                font-weight: 600;
            }}
        """)

        # Plots tab
        self.plots_tab = self._create_plots_tab()
        self.tabs.addTab(self.plots_tab, "📊 Plots")

        # Tables tab
        self.tables_tab = self._create_tables_tab()
        self.tabs.addTab(self.tables_tab, "📋 Tables")

        layout.addWidget(self.tabs)

    def _create_plots_tab(self) -> QWidget:
        """Create plots tab with X and Y direction plots side-by-side - simplified structure matching normal drift page."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Horizontal layout for X and Y plots with padding
        plots_layout = QHBoxLayout()
        plots_layout.setContentsMargins(0, 0, 0, 0)
        plots_layout.setSpacing(16)  # 16px spacing between the two plots

        # X Direction plot
        x_container = self._create_plot_widget("X")
        plots_layout.addWidget(x_container, 1)

        # Y Direction plot
        y_container = self._create_plot_widget("Y")
        plots_layout.addWidget(y_container, 1)

        layout.addLayout(plots_layout)

        return widget

    def _create_plot_widget(self, direction: str) -> QWidget:
        """Create a plot widget with external legend - matching normal drift page exactly."""
        # Container with horizontal layout (plot + legend)
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Create plot widget
        plot_widget = pg.PlotWidget()
        plot_widget.setBackground('#0a0c10')

        # Set plot area background
        view_box = plot_widget.getPlotItem().getViewBox()
        view_box.setBackgroundColor('#0f1419')
        view_box.setBorder(pg.mkPen('#2c313a', width=1))

        # Configure plot appearance
        plot_widget.showGrid(x=True, y=True, alpha=0.5)
        plot_widget.getAxis('bottom').setPen(pg.mkPen('#2c313a', width=1))
        plot_widget.getAxis('left').setPen(pg.mkPen('#2c313a', width=1))
        plot_widget.getAxis('bottom').setTextPen('#d1d5db')
        plot_widget.getAxis('left').setTextPen('#d1d5db')

        # Disable interactions
        plot_widget.setMenuEnabled(False)
        view_box.setMouseEnabled(x=False, y=False)
        view_box.setDefaultPadding(0.0)

        layout.addWidget(plot_widget, 1)

        # Create external legend
        from PyQt6.QtWidgets import QFrame, QSizePolicy, QSpacerItem
        legend_wrapper = QWidget()
        legend_wrapper.setMaximumWidth(150)
        legend_wrapper_layout = QVBoxLayout(legend_wrapper)
        legend_wrapper_layout.setContentsMargins(0, 0, 0, 0)
        legend_wrapper_layout.setSpacing(0)

        # Add spacer to align legend with plot area
        top_spacer = QSpacerItem(0, 42, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)  # 80px down from previous position (33 + 80 = 113)
        legend_wrapper_layout.addItem(top_spacer)

        legend_frame = QFrame()
        legend_frame.setStyleSheet("""
            QFrame {
                background-color: #11151c;
                border: 1px solid #2c313a;
                border-radius: 6px;
            }
        """)
        legend_frame.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Maximum)

        legend_layout = QVBoxLayout(legend_frame)
        legend_layout.setContentsMargins(8, 8, 8, 8)
        legend_layout.setSpacing(6)
        legend_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        legend_wrapper_layout.addWidget(legend_frame)
        legend_wrapper_layout.addStretch()

        layout.addWidget(legend_wrapper, 0, Qt.AlignmentFlag.AlignTop)

        # Store references
        if direction == "X":
            self.x_plot = plot_widget
            self.x_legend_layout = legend_layout
            self.x_plot_container = container
        else:
            self.y_plot = plot_widget
            self.y_legend_layout = legend_layout
            self.y_plot_container = container

        return container

    def _create_tables_tab(self) -> QWidget:
        """Create tables tab with X and Y direction containers stacked vertically."""
        from PyQt6.QtWidgets import QScrollArea

        # Create scroll area for the entire tables container
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)

        # Content widget
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(16)

        # X Direction container (Min and Max side-by-side)
        x_container = self._create_direction_tables("X")
        layout.addWidget(x_container)

        # Y Direction container (Min and Max side-by-side)
        y_container = self._create_direction_tables("Y")
        layout.addWidget(y_container)

        layout.addStretch()  # Push content to top

        scroll_area.setWidget(content_widget)
        return scroll_area

    def _create_direction_tables(self, direction: str) -> QWidget:
        """Create Min and Max tables side-by-side for a direction."""
        # Outer container
        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(8)

        # Title
        title_label = QLabel(f"{direction} Direction")
        title_label.setStyleSheet(f"""
            font-size: 16px;
            font-weight: 600;
            color: {COLORS['text']};
        """)
        main_layout.addWidget(title_label)

        # Horizontal layout for Min and Max tables
        tables_layout = QHBoxLayout()
        tables_layout.setContentsMargins(0, 0, 0, 0)
        tables_layout.setSpacing(12)

        # Min table
        min_table = self._create_single_table("Min")
        tables_layout.addWidget(min_table, 1)

        # Max table
        max_table = self._create_single_table("Max")
        tables_layout.addWidget(max_table, 1)

        main_layout.addLayout(tables_layout)

        # Store references (extract actual table widgets from containers)
        if direction == "X":
            self.x_min_table = min_table._table
            self.x_max_table = max_table._table
            self.x_tables_container = container
            self.x_tables_label = title_label
        else:
            self.y_min_table = min_table._table
            self.y_max_table = max_table._table
            self.y_tables_container = container
            self.y_tables_label = title_label

        return container

    def _create_single_table(self, label: str) -> QTableWidget:
        """Create a single styled table widget with label."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Label for Min/Max
        label_widget = QLabel(label)
        label_widget.setStyleSheet(f"""
            font-size: 14px;
            font-weight: 600;
            color: {COLORS['text']};
        """)
        layout.addWidget(label_widget)

        # Table
        table = QTableWidget()
        table.setStyleSheet("""
            QTableWidget {
                background-color: #0a0c10;
                border: 1px solid #2c313a;
                border-radius: 0px;
                gridline-color: #2c313a;
            }
            QTableWidget::item {
                padding: 4px 6px;
                border: none;
            }
            QTableWidget::item:selected {
                background-color: transparent;
                color: inherit;
            }
            QTableWidget::item:focus {
                background-color: transparent;
                color: inherit;
                border: none;
                outline: none;
            }
            QHeaderView::section {
                background-color: #161b22;
                color: #4a7d89;
                border: none;
                border-bottom: 1px solid #2c313a;
                padding: 4px 6px;
                font-weight: 600;
            }
            QTableWidget QTableCornerButton::section {
                background-color: #161b22;
                border: none;
            }
        """)

        # Hide vertical header (row numbers) - matches normal drift page
        table.verticalHeader().setVisible(False)

        # Configure selection
        from PyQt6.QtWidgets import QAbstractItemView
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)  # Disable Qt selection - use manual tracking
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # Prevent focus styling

        # Override palette to prevent Qt from changing text colors on selection
        from PyQt6.QtGui import QPalette, QColor
        palette = table.palette()
        # Set highlight text color to match normal text (prevents color change)
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#d1d5db"))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(0, 0, 0, 0))  # Transparent highlight
        table.setPalette(palette)

        # Enable mouse tracking for hover effects
        table.setMouseTracking(True)
        table.viewport().setMouseTracking(True)

        # Store references for tracking
        table._hovered_row = -1

        # Install event filter for hover effects AND clicks
        table.viewport().installEventFilter(self)

        # Disable individual table scrolling - scroll area handles scrolling
        table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Set size policy to expand based on content
        from PyQt6.QtWidgets import QSizePolicy
        table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        table.setSizeAdjustPolicy(QTableWidget.SizeAdjustPolicy.AdjustToContents)

        layout.addWidget(table)

        # Store label for reference
        container._table = table
        container._label = label
        return container

    def load_dataset(self, dataset: "MaxMinDataset"):
        """Load dataset from the result service."""
        if not dataset or dataset.data.empty:
            self.clear_data()
            return

        self.load_data(dataset)

    def load_data(self, dataset: "MaxMinDataset"):
        """Load and display Max/Min data for any result type."""
        df = dataset.data
        self.current_data = df
        self.current_display_name = dataset.meta.display_name
        base_result_type = dataset.source_type or self._infer_base_result_type(dataset.meta.result_type)
        self.current_base_type = base_result_type

        story_names = df['Story'].tolist() if 'Story' in df.columns else []
        available_directions = tuple(dataset.directions or ("X", "Y"))

        direction_visibility = {}
        for direction in ("X", "Y"):
            if direction in available_directions:
                has_data = self._load_direction_data(df, direction, story_names, base_result_type)
            else:
                self._clear_direction(direction)
                has_data = False

            direction_visibility[direction] = has_data
            self._set_direction_visibility(direction, has_data)
            self._update_direction_label(direction)

        if not any(direction_visibility.values()):
            self.clear_data()

    def _load_direction_data(self, df: pd.DataFrame, direction: str, story_names: list, base_result_type: str) -> bool:
        """Load data for a specific direction.

        Args:
            df: Full DataFrame
            direction: 'X' or 'Y'
            story_names: List of story names
            base_result_type: Base result identifier (Drifts, Accelerations, etc.)
        """
        # Get columns for this direction
        suffix = f'_{direction}'
        direction_cols = [col for col in df.columns if col.endswith(suffix)]

        if not direction_cols:
            self._clear_direction(direction)
            return False

        # Separate into Max (positive) and Min (negative) columns
        # Assuming Max columns contain positive drift, Min contains negative
        max_cols = [col for col in direction_cols if 'Max' in col]
        min_cols = [col for col in direction_cols if 'Min' in col]

        if not max_cols and not min_cols:
            self._clear_direction(direction)
            return False

        config_key = self._get_config_key(base_result_type, direction)
        config = get_config(config_key)

        # Plot and populate tables
        if direction == 'X':
            self._plot_maxmin_data(self.x_plot, self.x_legend_layout, df, max_cols, min_cols, story_names, direction, base_result_type, config)
            self._populate_min_max_tables(self.x_min_table, self.x_max_table, df, max_cols, min_cols, story_names, direction, base_result_type, config)
        else:
            self._plot_maxmin_data(self.y_plot, self.y_legend_layout, df, max_cols, min_cols, story_names, direction, base_result_type, config)
            self._populate_min_max_tables(self.y_min_table, self.y_max_table, df, max_cols, min_cols, story_names, direction, base_result_type, config)

        return True

    def _plot_maxmin_data(self, plot_widget, legend_layout, df, max_cols, min_cols, story_names, direction, base_result_type: str, config):
        """Plot Max/Min drift data - horizontal orientation (drift on X, story on Y) - matches normal drift page."""
        plot_widget.clear()

        # Clear external legend
        self._clear_legend(legend_layout)

        # Clear plot items for this direction
        if direction == 'X':
            self.x_plot_items.clear()
            plot_items = self.x_plot_items
        else:
            self.y_plot_items.clear()
            plot_items = self.y_plot_items

        if not story_names:
            return

        include_base_anchor = base_result_type == "Displacements"
        num_stories = len(story_names)
        story_indices = list(range(num_stories))
        if include_base_anchor:
            story_labels = ["Base"] + list(story_names)
            base_index = 0
            story_indices = [idx + 1 for idx in range(len(story_names))]
        else:
            story_labels = list(story_names)
            base_index = None
            story_indices = list(range(len(story_names)))

        # Highly distinct colors matching normal drift page
        colors = [
            '#ff4757',  # Bright red
            '#1e90ff',  # Dodger blue
            '#2ed573',  # Bright green
            '#ff6348',  # Tomato/coral
            '#a29bfe',  # Periwinkle
            '#00d2d3',  # Cyan
            '#ffa502',  # Orange
            '#ff6b81',  # Pink
            '#5f27cd',  # Purple
            '#01a3a4',  # Teal
            '#48dbfb',  # Sky blue
            '#c44569',  # Dark pink
            '#f8b500',  # Golden yellow
        ]

        # Collect all drift values for range calculation
        all_values = []

        # Match Max and Min columns by load case
        load_cases_plotted = []
        avg_color = "#ffa500"

        # Plot each load case - Max and Min with same color
        for idx, max_col in enumerate(max_cols):
            if max_col not in df.columns:
                continue

            # Extract load case name (remove file prefix and direction suffix)
            # Format: "Max_FileName_TH01_X" -> "TH01"
            load_case_full = max_col.replace(f'_{direction}', '').replace('Max_', '')

            # Extract just the load case part (last part after underscore, or whole if no underscore)
            load_case_parts = load_case_full.split('_')
            load_case = load_case_parts[-1] if len(load_case_parts) > 1 else load_case_full

            # Find corresponding Min column
            min_col = f'Min_{load_case_full}_{direction}'
            if min_col not in min_cols:
                continue

            color = colors[idx % len(colors)]

            # Get values
            max_values = df[max_col].values.tolist()
            min_values = (-df[min_col].values).tolist()  # Negated for negative side

            y_positions = list(story_indices)

            if include_base_anchor:
                # Anchor all series at the base so plotted lines originate at (0, 0)
                y_positions = [base_index] + y_positions
                max_values = [0.0] + max_values
                min_values = [0.0] + min_values

            # Collect values for range calculation
            all_values.extend(max_values)
            all_values.extend(min_values)

            # Plot Max values (positive drifts) - SOLID line
            # Horizontal: drift on X-axis, story on Y-axis
            max_item = plot_widget.plot(
                max_values, y_positions,
                pen=pg.mkPen(color=color, width=2),
                antialias=True
            )

            # Plot Min values (negative drifts) - DASHED line, SAME COLOR
            min_item = plot_widget.plot(
                min_values, y_positions,
                pen=pg.mkPen(color=color, width=2, style=Qt.PenStyle.DashLine),
                antialias=True
            )

            # Store plot items for highlighting
            plot_items[load_case] = {
                'max_item': max_item,
                'min_item': min_item,
                'color': color,
                'width': 2
            }

            # Add to legend ONCE - just the load case name (no "Max" or "Min")
            self._add_legend_item(legend_layout, color, load_case, direction)

            load_cases_plotted.append(load_case)

        # Plot average envelopes (drawn last so they sit on top)
        max_avg_series = self._compute_average_series(df, max_cols)
        if max_avg_series is not None:
            avg_values = max_avg_series.tolist()
            y_positions = list(story_indices)
            if include_base_anchor:
                avg_values = [0.0] + avg_values
                y_positions = [base_index] + y_positions

            avg_max_item = plot_widget.plot(
                avg_values,
                y_positions,
                pen=pg.mkPen(avg_color, width=4, style=Qt.PenStyle.SolidLine),
                antialias=True,
            )
            all_values.extend(avg_values)
            self._add_static_legend_item(legend_layout, avg_color, "Avg Max", Qt.PenStyle.SolidLine)

        min_avg_series = self._compute_average_series(df, min_cols, absolute=True)
        if min_avg_series is not None:
            avg_values = [-val for val in min_avg_series.tolist()]
            y_positions = list(story_indices)
            if include_base_anchor:
                avg_values = [0.0] + avg_values
                y_positions = [base_index] + y_positions

            avg_min_item = plot_widget.plot(
                avg_values,
                y_positions,
                pen=pg.mkPen(avg_color, width=4, style=Qt.PenStyle.DashLine),
                antialias=True,
            )
            all_values.extend(avg_values)
            self._add_static_legend_item(legend_layout, avg_color, "Avg Min", Qt.PenStyle.DashLine)

        # Add zero drift line for symmetry (vertical line at x=0)
        plot_widget.addLine(x=0, pen=pg.mkPen('#4a7d89', width=1, style=Qt.PenStyle.DotLine))

        # Use PlotBuilder for axis configuration (matching normal drift page)
        from utils.plot_builder import PlotBuilder
        builder = PlotBuilder(plot_widget, config)

        # Configure axes with story labels (include base if needed)
        builder.setup_axes(story_labels)

        # Set y-axis range with tight padding
        builder.set_story_range(len(story_labels), padding=0.1)

        # Calculate x-axis range from all values
        # Filter out zeros and set range with small padding on all sides
        all_values = [v for v in all_values if v != 0.0]
        if all_values:
            min_val = min(all_values)
            max_val = max(all_values)
            # Small symmetric padding (3% on left, 5% on right for legend space)
            builder.set_value_range(min_val, max_val, left_padding=0.03, right_padding=0.05)

        # Set title (matching normal drift page format)
        builder.set_title(f"Max/Min Drifts - {direction}")

        # Set dynamic tick spacing (6 intervals based on data range)
        if all_values:
            builder.set_dynamic_tick_spacing('bottom', min_val, max_val, num_intervals=6)

        # Lock the view ranges to prevent auto-scaling during pen updates
        view_box = plot_widget.getPlotItem().getViewBox()
        view_box.enableAutoRange(enable=False)

    def _populate_min_max_tables(self, min_table, max_table, df, max_cols, min_cols, story_names, direction, base_result_type, config):
        """Populate separate Min and Max tables with color gradients."""
        from utils.color_utils import get_gradient_color
        from utils.data_utils import parse_percentage_value
        from PyQt6.QtGui import QColor

        # Populate Max table
        self._populate_single_table(max_table, df, max_cols, story_names, direction, base_result_type, config.color_scheme, is_max=True)

        # Populate Min table
        self._populate_single_table(min_table, df, min_cols, story_names, direction, base_result_type, config.color_scheme, is_max=False)

    def _populate_single_table(self, table, df, cols, story_names, direction, base_result_type: str, color_scheme: str, is_max):
        """Populate a single table (Min or Max) with color gradients on text."""
        from utils.color_utils import get_gradient_color
        from utils.data_utils import parse_percentage_value
        from PyQt6.QtGui import QColor

        table.clear()

        if not cols or not story_names:
            return

        # Set dimensions (Story column + load cases + Avg)
        table.setRowCount(len(story_names))
        table.setColumnCount(len(cols) + 2)

        # Extract load case names
        load_case_names = []
        for col in cols:
            # Remove direction suffix and Max/Min prefix
            # Format: "Max_FileName_TH01_X" -> "TH01"
            col_clean = col.replace(f'_{direction}', '').replace('Max_', '').replace('Min_', '')
            parts = col_clean.split('_')
            load_case = parts[-1] if len(parts) > 1 else col_clean
            load_case_names.append(load_case)

        # Set headers (Story + load case names)
        headers = ['Story'] + load_case_names + ['Avg']
        table.setHorizontalHeaderLabels(headers)

        # Collect all values for gradient range calculation
        all_values = []
        for col in cols:
            if col in df.columns:
                for idx in range(len(story_names)):
                    value = df[col].iloc[idx]
                    # Handle both string and numeric values
                    if isinstance(value, str):
                        numeric_value = parse_percentage_value(value)
                    else:
                        numeric_value = float(value)
                    # Use absolute values for range calculation
                    all_values.append(abs(numeric_value))

        # Filter zeros and calculate range
        all_values = [v for v in all_values if v != 0.0]
        if all_values:
            min_val = min(all_values)
            max_val = max(all_values)
        else:
            min_val, max_val = 0, 0

        # Populate data with color gradients on text
        for row_idx in range(len(story_names)):
            row_values = []
            # First column: Story name
            story_item = QTableWidgetItem(story_names[row_idx])
            story_item.setFlags(story_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            story_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            story_color = QColor("#d1d5db")  # Default text color
            story_item.setForeground(story_color)
            # Store original color for hover/selection preservation
            story_item._original_color = story_color
            table.setItem(row_idx, 0, story_item)

            # Data columns: drift values
            for col_idx, col in enumerate(cols):
                if col in df.columns:
                    value = df[col].iloc[row_idx]

                    # Handle both raw and already-formatted values
                    if isinstance(value, str):
                        numeric_value = parse_percentage_value(value)
                    else:
                        # Value is already numeric (likely from cache)
                        numeric_value = float(value)

                    display_text = self._format_maxmin_number(numeric_value, base_result_type)
                    item = QTableWidgetItem(display_text)
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                    # Ensure no background is set
                    from PyQt6.QtCore import Qt as QtCore
                    item.setData(QtCore.ItemDataRole.BackgroundRole, None)

                    # Apply color gradient to text (use absolute value for coloring)
                    abs_value = abs(numeric_value)
                    if abs_value != 0.0 and min_val != max_val and min_val != 0:
                        color_hex = get_gradient_color(abs_value, min_val, max_val, color_scheme)
                        gradient_color = QColor(color_hex)
                        item.setForeground(gradient_color)
                        # Store original color for hover/selection preservation
                        item._original_color = gradient_color
                    else:
                        # Default text color for zeros or invalid range
                        default_color = QColor("#d1d5db")
                        item.setForeground(default_color)
                        # Store original color for hover/selection preservation
                        item._original_color = default_color

                    table.setItem(row_idx, col_idx + 1, item)  # +1 because Story is column 0
                    row_values.append(numeric_value)

            avg_value = self._calculate_row_average(row_values)
            avg_item = self._create_average_item(avg_value, base_result_type)
            table.setItem(row_idx, len(cols) + 1, avg_item)

        # Resize columns - Story column fixed width, data columns stretch
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        for i in range(1, table.columnCount()):
            table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)

        # Resize table to show all rows (no internal scrolling)
        self._resize_table_to_content(table)

    @staticmethod
    def _calculate_row_average(values):
        """Return the mean of valid numeric values, ignoring None/NaN."""
        valid = [
            val for val in values
            if val is not None and not (isinstance(val, float) and math.isnan(val))
        ]
        if not valid:
            return None
        return sum(valid) / len(valid)

    def _create_average_item(self, value, base_result_type: str) -> QTableWidgetItem:
        """Create a styled table item for the Average column."""
        from PyQt6.QtGui import QColor

        item = QTableWidgetItem()
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

        if value is None or (isinstance(value, float) and math.isnan(value)):
            item.setText("-")
        else:
            item.setText(self._format_maxmin_number(value, base_result_type))

        accent = QColor("#ffa500")
        item.setForeground(accent)
        item._original_color = QColor(accent)
        return item

    def _compute_average_series(self, df: pd.DataFrame, columns: list[str], absolute: bool = False):
        """Return a per-story average series for the provided columns."""
        if not columns:
            return None

        valid_cols = [col for col in columns if col in df.columns]
        if not valid_cols:
            return None

        numeric_df = df[valid_cols].apply(pd.to_numeric, errors='coerce')
        if numeric_df.empty:
            return None

        if absolute:
            numeric_df = numeric_df.abs()

        avg_series = numeric_df.mean(axis=1, skipna=True)
        if avg_series.isna().all():
            return None

        return avg_series.fillna(0.0)

    def _resize_table_to_content(self, table):
        """Resize table height to show all rows without scrolling."""
        # Calculate total height needed
        total_height = table.horizontalHeader().height()  # Header height

        for row in range(table.rowCount()):
            total_height += table.rowHeight(row)

        # Add some padding for borders
        total_height += 2

        # Set fixed height to show all content
        table.setMaximumHeight(total_height)
        table.setMinimumHeight(total_height)

    def _add_legend_item(self, legend_layout, color: str, label: str, direction: str):
        """Add an interactive legend item to the external legend."""
        from PyQt6.QtWidgets import QHBoxLayout, QLabel

        # Create interactive legend item widget
        item_widget = InteractiveLegendItem(label, color, direction, self)
        legend_layout.addWidget(item_widget)

    def _add_static_legend_item(self, legend_layout, color: str, label: str, pen_style: Qt.PenStyle):
        """Add a non-interactive legend item (for aggregate lines like averages)."""
        from PyQt6.QtWidgets import QHBoxLayout, QLabel, QWidget

        item_widget = QWidget()
        item_widget.setStyleSheet("background-color: transparent;")
        item_widget.setContentsMargins(0, 3, 0, 3)

        layout = QHBoxLayout(item_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        indicator = QLabel()
        indicator.setStyleSheet(f"""
            QLabel {{
                min-width: 30px;
                max-width: 30px;
                min-height: 1px;
                max-height: 1px;
                border-bottom: 2px {'dashed' if pen_style == Qt.PenStyle.DashLine else 'solid'} {color};
            }}
        """)

        text_label = QLabel(label)
        text_label.setStyleSheet("QLabel { color: #d1d5db; font-size: 10pt; font-weight: 600; }")

        layout.addWidget(indicator)
        layout.addWidget(text_label)
        layout.addStretch()

        legend_layout.addWidget(item_widget)

    def _clear_legend(self, legend_layout):
        """Clear all items from the external legend."""
        while legend_layout.count():
            item = legend_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _base_type_decimals(self, base_type: str) -> int:
        mapping = {"Drifts": 2, "Accelerations": 2, "Forces": 0, "Displacements": 0}
        return mapping.get(base_type, 2)

    def _format_maxmin_number(self, value: float, base_type: str) -> str:
        decimals = self._base_type_decimals(base_type)
        if decimals <= 0:
            text = f"{round(value):.0f}"
        else:
            text = f"{value:.{decimals}f}"
        return f"{text}%" if base_type == "Drifts" else text

    def eventFilter(self, obj, event):
        """Handle hover effects and clicks for table rows."""
        from PyQt6.QtCore import QEvent, Qt as QtCore
        from PyQt6.QtWidgets import QTableWidget

        table = obj.parent()
        if not isinstance(table, QTableWidget):
            return False

        if event.type() == QEvent.Type.MouseButtonPress:
            # Handle click
            if event.button() == QtCore.MouseButton.LeftButton:
                pos = event.pos()
                item = table.itemAt(pos)
                if item:
                    row = item.row()
                    table_id = id(table)

                    # Initialize set for this table if not exists
                    if table_id not in self._table_selected_rows:
                        self._table_selected_rows[table_id] = set()

                    # Toggle row selection
                    if row in self._table_selected_rows[table_id]:
                        self._table_selected_rows[table_id].remove(row)
                    else:
                        self._table_selected_rows[table_id].add(row)

                    # Update row styling
                    self._apply_table_row_style(table, row)
                    return True

        elif event.type() == QEvent.Type.MouseMove:
            # Handle hover
            pos = event.pos()
            item = table.itemAt(pos)

            if item:
                new_row = item.row()
                old_row = getattr(table, '_hovered_row', -1)

                if new_row != old_row:
                    # Clear old hover
                    if old_row >= 0:
                        self._apply_table_row_hover(table, old_row, False)

                    # Apply new hover
                    table._hovered_row = new_row
                    self._apply_table_row_hover(table, new_row, True)
            else:
                # Clear hover when not over any item
                old_row = getattr(table, '_hovered_row', -1)
                if old_row >= 0:
                    self._apply_table_row_hover(table, old_row, False)
                    table._hovered_row = -1

        elif event.type() == QEvent.Type.Leave:
            # Clear hover when mouse leaves table
            old_row = getattr(table, '_hovered_row', -1)
            if old_row >= 0:
                self._apply_table_row_hover(table, old_row, False)
                table._hovered_row = -1

        return False

    def _apply_table_row_style(self, table, row):
        """Apply style to a row based on hover and selection state."""
        from PyQt6.QtGui import QColor, QBrush

        table_id = id(table)
        is_hovered = (row == getattr(table, '_hovered_row', -1))
        is_selected = (table_id in self._table_selected_rows and row in self._table_selected_rows[table_id])

        for col in range(table.columnCount()):
            item = table.item(row, col)
            if item and hasattr(item, '_original_color'):
                # Always restore original foreground color
                item.setForeground(item._original_color)

                # Apply background overlay if hovered or selected
                if is_hovered or is_selected:
                    item.setBackground(QColor(103, 232, 249, 20))  # 8% cyan opacity
                else:
                    item.setBackground(QBrush())  # Clear background

    def _apply_table_row_hover(self, table, row, is_hovered):
        """Apply or remove hover effect from a row."""
        # Use unified styling method
        self._apply_table_row_style(table, row)

    def clear_data(self):
        """Clear all data from plots and tables."""
        self._clear_direction('X')
        self._clear_direction('Y')
        self._set_direction_visibility('X', True)
        self._set_direction_visibility('Y', True)

        self.current_data = None
        self.current_base_type = "Drifts"
        self.current_display_name = "Max/Min Drifts"

        # Clear selected rows tracking
        self._table_selected_rows.clear()

    def _clear_direction(self, direction: str):
        """Clear plot, legend, and tables for a direction."""
        if direction == 'X':
            plot = getattr(self, 'x_plot', None)
            legend = getattr(self, 'x_legend_layout', None)
            min_table = getattr(self, 'x_min_table', None)
            max_table = getattr(self, 'x_max_table', None)
            plot_items = self.x_plot_items
            selection = self.x_current_selection
        else:
            plot = getattr(self, 'y_plot', None)
            legend = getattr(self, 'y_legend_layout', None)
            min_table = getattr(self, 'y_min_table', None)
            max_table = getattr(self, 'y_max_table', None)
            plot_items = self.y_plot_items
            selection = self.y_current_selection

        if plot:
            plot.clear()
        if legend:
            self._clear_legend(legend)
        if min_table:
            min_table.clear()
        if max_table:
            max_table.clear()

        if min_table:
            self._table_selected_rows.pop(id(min_table), None)
        if max_table:
            self._table_selected_rows.pop(id(max_table), None)

        plot_items.clear()
        selection.clear()

    def _set_direction_visibility(self, direction: str, visible: bool):
        """Show or hide the UI containers for a direction."""
        if direction == 'X':
            plot_container = self.x_plot_container
            tables_container = self.x_tables_container
        else:
            plot_container = self.y_plot_container
            tables_container = self.y_tables_container

        if plot_container is not None:
            plot_container.setVisible(visible)
        if tables_container is not None:
            tables_container.setVisible(visible)

    def _update_direction_label(self, direction: str):
        """Update the direction title to reflect the current result type."""
        label = self.x_tables_label if direction == 'X' else self.y_tables_label
        if label:
            label.setText(f"{direction} Direction - {self.current_base_type}")

    @staticmethod
    def _infer_base_result_type(result_type: Optional[str]) -> str:
        """Infer the base result type name from a Max/Min identifier."""
        if not result_type:
            return "Drifts"
        if result_type.startswith("MaxMin"):
            base = result_type.replace("MaxMin", "", 1)
            return base or "Drifts"
        return result_type

    @staticmethod
    def _get_config_key(base_result_type: str, direction: str) -> str:
        """Return the configuration key for a result type/direction."""
        key = f"{base_result_type}_{direction}"
        if key in RESULT_CONFIGS:
            return key
        return base_result_type

    def highlight_load_cases(self, selected_cases: list, direction: str):
        """Highlight selected load cases, dim others."""
        plot_items = self.x_plot_items if direction == 'X' else self.y_plot_items
        current_selection = self.x_current_selection if direction == 'X' else self.y_current_selection

        if not selected_cases:
            # No selection - restore all to full opacity
            for case_name, case_data in plot_items.items():
                max_item = case_data['max_item']
                min_item = case_data['min_item']
                color = case_data['color']
                width = case_data['width']

                max_item.setPen(pg.mkPen(color, width=width))
                min_item.setPen(pg.mkPen(color, width=width, style=Qt.PenStyle.DashLine))
        else:
            # Highlight selected cases, dim others
            selected_set = set(selected_cases)

            for case_name, case_data in plot_items.items():
                max_item = case_data['max_item']
                min_item = case_data['min_item']
                color = case_data['color']
                width = case_data['width']

                if case_name in selected_set:
                    # Selected case - full opacity, keep same width
                    max_item.setPen(pg.mkPen(color, width=width))
                    min_item.setPen(pg.mkPen(color, width=width, style=Qt.PenStyle.DashLine))
                else:
                    # Non-selected case - reduce opacity
                    from PyQt6.QtGui import QColor
                    qcolor = QColor(color)
                    qcolor.setAlpha(40)  # Low opacity (~15%)
                    max_item.setPen(pg.mkPen(qcolor, width=width))
                    min_item.setPen(pg.mkPen(qcolor, width=width, style=Qt.PenStyle.DashLine))

    def hover_load_case(self, load_case: str, direction: str):
        """Temporarily highlight a load case on hover."""
        plot_items = self.x_plot_items if direction == 'X' else self.y_plot_items
        current_selection = self.x_current_selection if direction == 'X' else self.y_current_selection

        if load_case not in plot_items:
            return

        from PyQt6.QtGui import QColor

        for case_name, case_data in plot_items.items():
            max_item = case_data['max_item']
            min_item = case_data['min_item']
            color = case_data['color']
            width = case_data['width']

            if case_name == load_case:
                # Hovered case - full opacity, keep width constant
                max_item.setPen(pg.mkPen(color, width=width))
                min_item.setPen(pg.mkPen(color, width=width, style=Qt.PenStyle.DashLine))
            elif case_name in current_selection:
                # Selected but not hovered - heavily dimmed to emphasize hover
                qcolor = QColor(color)
                qcolor.setAlpha(60)  # Low opacity (~23%)
                max_item.setPen(pg.mkPen(qcolor, width=width))
                min_item.setPen(pg.mkPen(qcolor, width=width, style=Qt.PenStyle.DashLine))
            else:
                # Not selected and not hovered - very heavily dimmed
                qcolor = QColor(color)
                qcolor.setAlpha(25)  # Very low opacity (~10%)
                max_item.setPen(pg.mkPen(qcolor, width=width))
                min_item.setPen(pg.mkPen(qcolor, width=width, style=Qt.PenStyle.DashLine))

    def clear_hover(self, direction: str):
        """Clear hover effect and restore to selected state."""
        current_selection = self.x_current_selection if direction == 'X' else self.y_current_selection
        self.highlight_load_cases(list(current_selection), direction)

    def toggle_load_case_selection(self, load_case: str, direction: str):
        """Toggle selection of a load case."""
        current_selection = self.x_current_selection if direction == 'X' else self.y_current_selection
        legend_layout = self.x_legend_layout if direction == 'X' else self.y_legend_layout

        if load_case in current_selection:
            current_selection.remove(load_case)
        else:
            current_selection.add(load_case)

        # Update highlighting
        self.highlight_load_cases(list(current_selection), direction)

        # Update legend item visual states
        for i in range(legend_layout.count()):
            item = legend_layout.itemAt(i).widget()
            if isinstance(item, InteractiveLegendItem):
                item.set_selected(item.label in current_selection)
