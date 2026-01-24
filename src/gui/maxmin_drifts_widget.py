"""Max/Min Results widget - displays positive and negative envelopes."""

from typing import TYPE_CHECKING, Optional

import pandas as pd
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QTableWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from config.result_config import get_config
from config.visual_config import TABLE_CELL_PADDING, TABLE_HEADER_PADDING
from gui.icon_utils import load_svg_icon
from gui.components.results_table_header import ClickableTableWidget
from .styles import COLORS
from .maxmin_data_processor import MaxMinDataProcessor
from .maxmin_plot_builder import MaxMinPlotBuilder
from .maxmin_table_builder import MaxMinTableBuilder

if TYPE_CHECKING:
    from services.result_service import MaxMinDataset


class MaxMinDriftsWidget(QWidget):
    """Widget for displaying Max/Min drifts with plots and tables."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self._data_processor = MaxMinDataProcessor()
        self._plot_builder = MaxMinPlotBuilder(self._data_processor)
        self._table_builder = MaxMinTableBuilder(self._data_processor)
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

        # Tab widget - minimalistic, borderless
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                background-color: {COLORS['background']};
                border: none;
                border-radius: 0px;
                padding: 0px;
            }}
            QTabBar::tab {{
                background-color: transparent;
                color: {COLORS['muted']};
                border: none;
                padding: 8px 16px;
                margin-right: 4px;
                font-size: 14px;
                border-radius: 0px;
            }}
            QTabBar::tab:hover {{
                color: {COLORS['text']};
                background-color: transparent;
            }}
            QTabBar::tab:selected {{
                color: {COLORS['accent']};
                background-color: transparent;
                font-weight: 600;
                border-bottom: 2px solid {COLORS['accent']};
            }}
        """)

        # Plots tab
        self.plots_tab = self._create_plots_tab()
        self.tabs.addTab(self.plots_tab, load_svg_icon("chart", 16, COLORS['muted']), "Plots")

        # Tables tab
        self.tables_tab = self._create_tables_tab()
        self.tabs.addTab(self.tables_tab, load_svg_icon("table", 16, COLORS['muted']), "Tables")

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
        from gui.components.plot_factory import create_plot_widget

        # Container with horizontal layout (plot + legend)
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Create plot widget using factory
        plot_widget = create_plot_widget()

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
                background-color: transparent;
                border: none;
                border-radius: 0px;
            }
        """)
        legend_frame.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Maximum)

        legend_layout = QVBoxLayout(legend_frame)
        legend_layout.setContentsMargins(0, 0, 0, 0)
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
        layout.setContentsMargins(6, 6, 6, 6)  # Proper margins for readability
        layout.setSpacing(12)  # Readable spacing between X and Y tables

        # X Direction container (Min and Max side-by-side)
        x_container = self._create_direction_tables("X")
        layout.addWidget(x_container)

        # Y Direction container (Min and Max side-by-side) - not used for directionless datasets
        y_container = self._create_direction_tables("Y")
        y_container.hide()
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
        main_layout.setSpacing(6)  # Readable spacing between title and tables

        # Title
        title_label = QLabel(f"{direction} Direction")
        title_label.setStyleSheet(f"""
            font-size: 14px;
            font-weight: 600;
            color: {COLORS['text']};
        """)
        main_layout.addWidget(title_label)

        # Horizontal layout for Min and Max tables
        tables_layout = QHBoxLayout()
        tables_layout.setContentsMargins(0, 0, 0, 0)
        tables_layout.setSpacing(8)  # Readable horizontal spacing between Min and Max

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
        layout.setSpacing(4)  # Readable spacing between label and table

        # Label for Min/Max
        label_widget = QLabel(label)
        label_widget.setStyleSheet(f"""
            font-size: 13px;
            font-weight: 600;
            color: {COLORS['text']};
        """)
        layout.addWidget(label_widget)

        # Table
        table = ClickableTableWidget()
        table.setStyleSheet(f"""
            QTableWidget {{
                background-color: #0a0c10;
                border: none;
                gridline-color: #1e2329;
            }}
            QTableWidget::item {{
                padding: {TABLE_CELL_PADDING};
                border: none;
            }}
            QTableWidget::item:selected {{
                background-color: transparent;
                color: inherit;
            }}
            QTableWidget::item:focus {{
                background-color: transparent;
                color: inherit;
                border: none;
                outline: none;
            }}
            QHeaderView {{
                background-color: #161b22;
                border: none;
            }}
            QHeaderView::section {{
                background-color: transparent;
                color: #4a7d89;
                border: none;
                border-left: none;
                border-right: none;
                border-top: none;
                border-bottom: none;
                padding: {TABLE_HEADER_PADDING};
                font-weight: 600;
                text-align: center;
            }}
            QTableWidget QTableCornerButton::section {{
                background-color: #161b22;
                border: none;
            }}
        """)

        # Set smaller font for compact display on smaller screens
        from PyQt6.QtGui import QFont
        table_font = QFont("Inter", 7)  # Ultra-compact font for Max/Min tables
        table.setFont(table_font)
        table.horizontalHeader().setFont(table_font)

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
        table._label_widget = label_widget

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
        df_excel_order = dataset.data
        self.current_display_name = dataset.meta.display_name
        base_result_type = dataset.source_type or self._infer_base_result_type(dataset.meta.result_type)
        self.current_base_type = base_result_type
        column_axials = base_result_type == "ColumnAxials"

        # For column axials we never want direction titles; replace immediately with the dataset name
        if column_axials and self.x_tables_label:
            self.x_tables_label.setText(self.current_display_name or "Max/Min Column Axials")
        if column_axials and self.y_tables_label:
            self.y_tables_label.setText("")

        # REVERSE story order for plotting: bottom floors at bottom (y=0), top floors at top (y=max)
        # Excel has top-to-bottom, but we want bottom-to-top for plots
        df = df_excel_order.iloc[::-1].reset_index(drop=True)
        self.current_data = df

        story_names_excel = df_excel_order['Story'].tolist() if 'Story' in df_excel_order.columns else []
        story_names = list(reversed(story_names_excel))  # Reverse for plotting
        available_directions = tuple(dataset.directions or ("X", "Y"))

        # Check if this is directionless data (e.g., QuadRotations, ColumnAxials)
        is_directionless = column_axials or (len(available_directions) == 1 and available_directions[0] == "")

        if is_directionless:
            # For directionless data, show single plot in X position, completely hide Y
            has_data = self._load_direction_data(df, "", story_names, base_result_type, "X")
            direction_visibility = {"X": has_data, "Y": False}

            # Clear Y direction data to ensure it's empty
            self._clear_direction("Y")

            # Set visibility
            self._set_direction_visibility("X", has_data)
            self._set_direction_visibility("Y", False)

            # Update label to remove direction indicator
            if self.x_tables_label:
                self.x_tables_label.setText(self.current_display_name or "Column Axials")
            # Explicitly clear the Y label and container for directionless data
            if self.y_tables_label:
                self.y_tables_label.setText("")
            self._set_direction_visibility("Y", False)
        else:
            # Map V2/V3 to X/Y for display (element results use V2/V3, global uses X/Y)
            direction_map = self._create_direction_map(available_directions)

            direction_visibility = {}
            for display_direction in ("X", "Y"):
                # Get actual data direction (V2→X, V3→Y for element results)
                data_direction = direction_map.get(display_direction, display_direction)

                if data_direction in available_directions:
                    has_data = self._load_direction_data(df, data_direction, story_names, base_result_type, display_direction)
                else:
                    self._clear_direction(display_direction)
                    has_data = False

                direction_visibility[display_direction] = has_data
                self._set_direction_visibility(display_direction, has_data)
                self._update_direction_label(display_direction, data_direction)

        if not any(direction_visibility.values()):
            self.clear_data()
        elif column_axials:
            # Force X label to dataset name for column axials and hide Y title if present
            if self.x_tables_label:
                self.x_tables_label.setText(self.current_display_name or "Column Axials")
            if self.y_tables_label:
                self.y_tables_label.setText("")

    def _load_direction_data(self, df: pd.DataFrame, direction: str, story_names: list, base_result_type: str, display_direction: str = None) -> bool:
        """Load data for a specific direction.

        Args:
            df: Full DataFrame
            direction: Actual data direction ('X', 'Y', 'V2', 'V3', or '' for directionless)
            story_names: List of story names
            base_result_type: Base result identifier (Drifts, Accelerations, etc.)
            display_direction: Display direction for widget mapping ('X' or 'Y'), defaults to direction
        """
        if display_direction is None:
            display_direction = direction

        max_cols, min_cols = self._data_processor.split_direction_columns(df, direction)

        if not max_cols and not min_cols:
            self._clear_direction(display_direction)
            return False

        config_key = self._get_config_key(base_result_type, direction)
        config = get_config(config_key)

        # Plot and populate tables using display_direction for widget selection
        if display_direction == 'X':
            self._plot_maxmin_data(self.x_plot, self.x_legend_layout, df, max_cols, min_cols, story_names, direction, base_result_type, config, display_direction)
            self._show_table_widget(self.x_min_table, "Min")
            self._show_table_widget(self.x_max_table, "Max")
            self._populate_min_max_tables(self.x_min_table, self.x_max_table, df, max_cols, min_cols, story_names, direction, base_result_type, config)
        else:
            self._plot_maxmin_data(self.y_plot, self.y_legend_layout, df, max_cols, min_cols, story_names, direction, base_result_type, config, display_direction)
            self._show_table_widget(self.y_min_table, "Min")
            self._show_table_widget(self.y_max_table, "Max")
            self._populate_min_max_tables(self.y_min_table, self.y_max_table, df, max_cols, min_cols, story_names, direction, base_result_type, config)

        return True

    def _plot_maxmin_data(self, plot_widget, legend_layout, df, max_cols, min_cols, story_names, direction, base_result_type: str, config, display_direction: str = None):
        """Plot Max/Min drift data - horizontal orientation (drift on X, story on Y) - matches normal drift page."""
        if display_direction is None:
            display_direction = direction

        plot_items = self.x_plot_items if display_direction == "X" else self.y_plot_items

        self._plot_builder.plot_maxmin_data(
            plot_widget=plot_widget,
            legend_layout=legend_layout,
            df=df,
            max_cols=max_cols,
            min_cols=min_cols,
            story_names=story_names,
            direction=direction,
            base_result_type=base_result_type,
            config=config,
            plot_items=plot_items,
            on_toggle=lambda case: self.toggle_load_case_selection(case, display_direction),
            on_hover=lambda case: self.hover_load_case(case, display_direction),
            on_leave=lambda: self.clear_hover(display_direction),
        )

    def _populate_min_max_tables(self, min_table, max_table, df, max_cols, min_cols, story_names, direction, base_result_type, config):
        """Populate separate Min and Max tables with color gradients."""
        self._table_builder.populate_min_max_tables(
            min_table,
            max_table,
            df,
            max_cols,
            min_cols,
            story_names,
            direction,
            base_result_type,
            config.color_scheme,
        )

    def _populate_axial_combined_table(self, table, df, max_cols, min_cols, story_names, base_result_type, color_scheme: str):
        """Populate a single table with both Max and Min axial values (no X/Y split)."""
        self._table_builder.populate_axial_combined_table(
            table,
            df,
            max_cols,
            min_cols,
            story_names,
            base_result_type,
            color_scheme,
        )

    def _hide_table_widget(self, table):
        """Hide a table and its container (used for single-table layouts)."""
        self._table_builder.hide_table_widget(table)

    def _show_table_widget(self, table, label_text: str = None):
        """Show a table and restore its container sizing."""
        self._table_builder.show_table_widget(table, label_text)

    def _populate_single_table(self, table, df, cols, story_names, direction, base_result_type: str, color_scheme: str, is_max):
        """Populate a single table (Min or Max) with color gradients on text."""
        self._table_builder.populate_single_table(
            table,
            df,
            cols,
            story_names,
            direction,
            base_result_type,
            color_scheme,
            is_max,
        )

    def _calculate_row_average(self, values):
        """Return the mean of valid numeric values, ignoring None/NaN."""
        return self._data_processor.calculate_row_average(values)

    def _create_average_item(self, value, base_result_type: str):
        """Create a styled table item for the Average column."""
        return self._table_builder.create_average_item(value, base_result_type)

    def _compute_average_series(self, df: pd.DataFrame, columns: list[str], absolute: bool = False):
        """Return a per-story average series for the provided columns."""
        return self._data_processor.compute_average_series(df, columns, absolute)

    def _resize_table_to_content(self, table):
        """Resize table height to show all rows without scrolling."""
        self._table_builder.resize_table_to_content(table)

    def _add_legend_item(self, legend_layout, color: str, label: str, direction: str):
        """Add an interactive legend item to the external legend."""
        self._plot_builder.add_legend_item(
            legend_layout,
            color,
            label,
            on_toggle=lambda case: self.toggle_load_case_selection(case, direction),
            on_hover=lambda case: self.hover_load_case(case, direction),
            on_leave=lambda: self.clear_hover(direction),
        )

    def _add_static_legend_item(self, legend_layout, color: str, label: str, pen_style: Qt.PenStyle):
        """Add a non-interactive legend item (for aggregate lines like averages)."""
        self._plot_builder.add_static_legend_item(legend_layout, color, label, pen_style)

    def _clear_legend(self, legend_layout):
        """Clear all items from the external legend."""
        self._plot_builder.clear_legend(legend_layout)

    def _base_type_decimals(self, base_type: str) -> int:
        return self._table_builder.base_type_decimals(base_type)

    def _format_maxmin_number(self, value: float, base_type: str) -> str:
        return self._table_builder.format_maxmin_number(value, base_type)

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
            if not visible:
                # Completely hide and collapse the container
                plot_container.setVisible(False)
                plot_container.setMaximumWidth(0)
                plot_container.setMaximumHeight(0)
                # Remove from parent layout to prevent space allocation
                parent_layout = plot_container.parent().layout() if plot_container.parent() else None
                if parent_layout:
                    parent_layout.removeWidget(plot_container)
            else:
                # Restore visibility and size constraints
                plot_container.setVisible(True)
                plot_container.setMaximumWidth(16777215)
                plot_container.setMaximumHeight(16777215)

        if tables_container is not None:
            if not visible:
                # Completely hide and collapse the container
                tables_container.setVisible(False)
                tables_container.setMaximumWidth(0)
                tables_container.setMaximumHeight(0)
                # Remove from parent layout to prevent space allocation
                parent_layout = tables_container.parent().layout() if tables_container.parent() else None
                if parent_layout:
                    parent_layout.removeWidget(tables_container)
            else:
                # Restore visibility and size constraints
                tables_container.setVisible(True)
                tables_container.setMaximumWidth(16777215)
                tables_container.setMaximumHeight(16777215)

    def _update_direction_label(self, display_direction: str, data_direction: str = None):
        """Update the direction title to reflect the current result type.

        Args:
            display_direction: Display direction ('X' or 'Y')
            data_direction: Actual data direction ('X', 'Y', 'V2', 'V3'), defaults to display_direction
        """
        if data_direction is None:
            data_direction = display_direction

        label = self.x_tables_label if display_direction == 'X' else self.y_tables_label
        if label:
            if self.current_base_type == "ColumnAxials":
                # Column axials are directionless; omit X/Y titles
                label.setText(self.current_display_name or "Column Axials")
            else:
                label.setText(f"{data_direction} Direction - {self.current_base_type}")

    @staticmethod
    def _create_direction_map(available_directions: tuple) -> dict:
        """Create a mapping from display directions (X/Y) to data directions (X/Y/V2/V3/R2/R3/empty).

        Args:
            available_directions: Tuple of available data directions

        Returns:
            Dict mapping display direction to data direction
        """
        return MaxMinDataProcessor.create_direction_map(available_directions)

    @staticmethod
    def _infer_base_result_type(result_type: Optional[str]) -> str:
        """Infer the base result type name from a Max/Min identifier."""
        return MaxMinDataProcessor.infer_base_result_type(result_type)

    @staticmethod
    def _get_config_key(base_result_type: str, direction: str) -> str:
        """Return the configuration key for a result type/direction."""
        return MaxMinDataProcessor.get_config_key(base_result_type, direction)

    def highlight_load_cases(self, selected_cases: list, direction: str):
        """Highlight selected load cases, dim others."""
        plot_items = self.x_plot_items if direction == "X" else self.y_plot_items
        self._plot_builder.highlight_load_cases(plot_items, selected_cases)

    def hover_load_case(self, load_case: str, direction: str):
        """Temporarily highlight a load case on hover."""
        plot_items = self.x_plot_items if direction == "X" else self.y_plot_items
        current_selection = self.x_current_selection if direction == "X" else self.y_current_selection
        self._plot_builder.hover_load_case(plot_items, current_selection, load_case)

    def clear_hover(self, direction: str):
        """Clear hover effect and restore to selected state."""
        plot_items = self.x_plot_items if direction == "X" else self.y_plot_items
        current_selection = self.x_current_selection if direction == "X" else self.y_current_selection
        self._plot_builder.clear_hover(plot_items, current_selection)

    def toggle_load_case_selection(self, load_case: str, direction: str):
        """Toggle selection of a load case."""
        plot_items = self.x_plot_items if direction == "X" else self.y_plot_items
        current_selection = self.x_current_selection if direction == "X" else self.y_current_selection
        legend_layout = self.x_legend_layout if direction == "X" else self.y_legend_layout
        self._plot_builder.toggle_load_case_selection(plot_items, current_selection, load_case, legend_layout)
