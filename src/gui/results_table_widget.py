"""Results table widget - displays tabular data with GMP styling."""

from __future__ import annotations

import logging
from typing import List, Optional, Set, TYPE_CHECKING

import pandas as pd
from PyQt6.QtCore import QEvent, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHeaderView,
    QHBoxLayout,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from utils.color_utils import get_gradient_color
from .components.results_table_header import ClickableTableWidget, SelectableHeaderView, PerimeterBorderDelegate

if TYPE_CHECKING:
    pass




if TYPE_CHECKING:
    from processing.result_service import ResultDataset

logger = logging.getLogger(__name__)


class ResultsTableWidget(QWidget):
    """Table widget for displaying results in tabular format."""

    # Signal emitted when a load case column is clicked (column_name)
    load_case_selected = pyqtSignal(str)
    # Signal emitted when selection changes (list of selected load cases)
    selection_changed = pyqtSignal(list)
    # Signals for hover effects
    load_case_hovered = pyqtSignal(str)
    hover_cleared = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        # Set size policy: preferred width (can shrink/grow), expand vertically to match plot height
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)

        # Transparent container; table manages its own border
        self.setObjectName("tableContainer")
        self.setStyleSheet("background-color: transparent; border: none;")

        # Track selected load cases for highlighting
        self._selected_load_cases = set()

        # Track Story column sort order
        self._story_sort_order = Qt.SortOrder.AscendingOrder

        # Track selected rows manually (for click highlighting)
        self._selected_rows = set()

        self._dataset: Optional["ResultDataset"] = None
        self._column_names: List[str] = []
        self._load_case_columns: List[str] = []
        self._load_case_column_set: Set[str] = set()
        self._shorthand_mapping: dict = {}  # Full name -> shorthand
        self._reverse_mapping: dict = {}  # Shorthand -> full name
        self._non_selectable_columns: Set[str] = {"Story"}

        self.setup_ui()

    def setup_ui(self):
        """Setup the table UI."""
        from PyQt6.QtWidgets import QHeaderView  # Local import to avoid missing symbol during hot reload

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.table = ClickableTableWidget()
        # No frame - we'll handle borders via CSS on container
        self.table.setFrameShape(QFrame.Shape.NoFrame)
        self.table.setFrameShadow(QFrame.Shadow.Plain)
        self.table.setLineWidth(0)
        self.table.setMidLineWidth(0)
        # Use Qt gridlines for internal borders
        self.table.setShowGrid(True)

        # Connect row click signal (for Story column clicks only)
        self.table.rowClicked.connect(self._on_row_clicked)

        # Set custom header view for highlighting selected columns
        custom_header = SelectableHeaderView(Qt.Orientation.Horizontal, self.table)
        self.table.setHorizontalHeader(custom_header)

        # Store reference to custom header
        self._custom_header = custom_header

        self.table.setAlternatingRowColors(False)  # Disable alternating row colors
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)  # Disable Qt selection - use manual tracking
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(False)  # Disable automatic sorting - we'll handle manually
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # Prevent focus styling

        # Override palette to prevent Qt from changing text colors on selection
        from PyQt6.QtGui import QPalette, QColor
        palette = self.table.palette()
        # Set highlight text color to match normal text (prevents color change)
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#d1d5db"))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(0, 0, 0, 0))  # Transparent highlight
        self.table.setPalette(palette)

        # Enable scrollbars when table is resized smaller than content
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Set consistent font across entire table (compact for fitting both table and plot)
        table_font = QFont("Inter", 9)
        self.table.setFont(table_font)
        self.table.horizontalHeader().setFont(table_font)

        # Style matching GMP tables - clean minimal design
        # NOTE: No background rules for ::item to allow programmatic background styling
        # Minimal design: no outer border, subtle gridlines, clean header separators
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #0a0c10;
                border: none;
                border-left: none;
                border-right: none;
                border-top: none;
                border-bottom: none;
                outline: none;
                gridline-color: #1e2329;
                color: #d1d5db;
            }
            QTableWidget QAbstractItemView {
                border: none;
                border-left: none;
                outline: none;
            }
            QTableWidget::item {
                padding: 1px 2px;
                border: none;
            }
            QTableWidget QTableCornerButton::section {
                border: none;
                background-color: #161b22;
            }
            QHeaderView {
                background-color: #161b22;
                border: none;
            }
            QHeaderView::section {
                background-color: transparent;
                color: #4a7d89;
                padding: 4px 4px;
                border: none;
                border-left: none;
                border-right: none;
                border-top: none;
                border-bottom: none;
                font-weight: 600;
                text-align: center;
            }
            QScrollBar:vertical {
                border: none;
                border-left: none;
                border-right: none;
                background-color: transparent;
                width: 2px;
                margin: 0px;
                padding: 0px;
            }
            QScrollBar::handle:vertical {
                background-color: rgba(255, 255, 255, 0.03);
                border: none;
                border-left: none;
                border-right: none;
                border-radius: 1px;
                min-height: 20px;
                margin: 0px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: rgba(255, 255, 255, 0.08);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
                border: none;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
                border: none;
            }
        """)

        # Configure headers - fixed mode (no resizing)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        header.setStretchLastSection(False)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setDefaultSectionSize(48)  # Default column width
        header.setSectionsClickable(True)  # Enable clicking

        self.table.verticalHeader().setVisible(False)
        self.table.setWordWrap(False)  # Prevent wrapping for compact display

        # Enable mouse tracking for row hover effects
        self.table.setMouseTracking(True)
        self.table.viewport().setMouseTracking(True)
        self.table.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.table.viewport().setAttribute(Qt.WidgetAttribute.WA_Hover, True)

        # Store references for hover tracking
        self.table._hovered_row = -1
        self._current_result_type = None

        # Install event filter for hover effects only
        self.table.viewport().installEventFilter(self)

        # Connect header click signal
        header.sectionClicked.connect(self._on_header_clicked)

        # Connect hover signals from custom header
        if isinstance(header, SelectableHeaderView):
            # Translate shorthand back to full name before emitting
            header.section_hovered.connect(self._on_header_hovered)
            header.section_hover_left.connect(self.hover_cleared.emit)

        layout.addWidget(self.table)

    def set_shorthand_mapping(self, mapping: dict):
        """
        Set shorthand mapping for column headers.

        Args:
            mapping: Dictionary mapping full names to shorthand (e.g., {"Push-Mod-X+Ecc+" -> "Px1"})
        """
        self._shorthand_mapping = mapping
        self._reverse_mapping = {v: k for k, v in mapping.items()}

    def clear_shorthand_mapping(self):
        """Clear the shorthand mapping."""
        self._shorthand_mapping = {}
        self._reverse_mapping = {}

    def load_dataset(self, dataset: "ResultDataset", shorthand_mapping: dict = None):
        """
        Load data from a ResultDataset into the table.

        Args:
            dataset: The result dataset to display
            shorthand_mapping: Optional mapping of full names to shorthand for column headers
        """
        df = dataset.data

        self._dataset = dataset
        self._current_result_type = dataset.meta.result_type or ""
        self._apply_type_styles(self._base_result_type())
        self._selected_load_cases.clear()
        self._selected_rows.clear()
        self._load_case_columns = list(dataset.load_case_columns)
        self._load_case_column_set = set(self._load_case_columns)

        # Set shorthand mapping if provided (check for None, not just falsy, since {} is valid)
        if shorthand_mapping is not None:
            logger.debug("Table load_dataset: received mapping with %s entries", len(shorthand_mapping))
            if shorthand_mapping:
                logger.debug("Table sample mapping: %s", list(shorthand_mapping.items())[:2])
            self.set_shorthand_mapping(shorthand_mapping)
        else:
            logger.debug("Table load_dataset: no mapping provided (None)")
            self.clear_shorthand_mapping()
        self._non_selectable_columns = {"Story", *dataset.summary_columns}
        self._story_sort_order = Qt.SortOrder.AscendingOrder

        header = self.table.horizontalHeader()
        if isinstance(header, QHeaderView):
            header.setSortIndicatorShown(False)

        if df.empty:
            self.clear_data()
            return

        column_names = df.columns.tolist()
        self._column_names = column_names

        row_count = len(df.index)
        column_count = len(column_names)

        self.table.setRowCount(row_count)
        self.table.setColumnCount(column_count)

        # Apply shorthand mapping to column headers if available
        if self._shorthand_mapping:
            display_names = [self._shorthand_mapping.get(name, name) for name in column_names]
            logger.debug("Setting headers WITH mapping: %s -> %s", column_names[:3], display_names[:3])
            self.table.setHorizontalHeaderLabels(display_names)
        else:
            logger.debug("Setting headers WITHOUT mapping (using original names): %s", column_names[:3])
            self.table.setHorizontalHeaderLabels(column_names)

        min_val, max_val = self._compute_value_range(df, self._load_case_columns)
        config = dataset.config

        for row_idx in range(row_count):
            for col_idx, col_name in enumerate(column_names):
                item = QTableWidgetItem()
                value = df.iloc[row_idx, col_idx]

                if col_name == "Story":
                    item.setText(str(value))
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    default_color = QColor("#d1d5db")
                    item.setForeground(default_color)
                    item._original_color = QColor(default_color)
                else:
                    item.setText(self._format_value(value, config))
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                    if col_name in dataset.summary_columns:
                        default_color = QColor("#d1d5db")
                        item.setForeground(default_color)
                        item._original_color = QColor(default_color)
                    elif col_name in self._load_case_column_set:
                        numeric_value = self._safe_numeric(value)
                        color = get_gradient_color(
                            numeric_value,
                            min_val,
                            max_val,
                            config.color_scheme,
                        )
                        item.setForeground(color)
                        item._original_color = QColor(color)
                    else:
                        default_color = QColor("#d1d5db")
                        item.setForeground(default_color)
                        item._original_color = QColor(default_color)

                self.table.setItem(row_idx, col_idx, item)

        self._resize_columns(column_count)
        self._update_header_styling()

    def _resize_columns(self, column_count: int) -> None:
        """Apply width constraints based on column type counts."""
        story_column_width = 52  # Reduced for 10px font
        data_column_width = self._column_width_for_type()

        for col_idx in range(column_count):
            if col_idx == 0:
                self.table.setColumnWidth(col_idx, story_column_width)
            else:
                self.table.setColumnWidth(col_idx, data_column_width)

        table_width = story_column_width + max(0, column_count - 1) * data_column_width

        # Set minimum width to content width - table should not scroll
        self.table.setMinimumWidth(table_width)
        self.table.setMaximumWidth(table_width)
        self.setMinimumWidth(table_width)
        self.setMaximumWidth(table_width)

    def _format_value(self, value, config) -> str:
        """Format numeric table value with unit string."""
        if pd.isna(value):
            return "-"
        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            return str(value)
        # No unit suffix in table cells - unit is shown in column header/title
        return f"{numeric_value:.{config.decimal_places}f}"

    @staticmethod
    def _safe_numeric(value) -> float:
        """Convert table value to float for gradient evaluation."""
        try:
            if pd.isna(value):
                return 0.0
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def _compute_value_range(self, df: pd.DataFrame, columns: List[str]) -> tuple[float, float]:
        """Determine min/max values across load case columns."""
        values: List[float] = []
        for col in columns:
            if col not in df:
                continue
            series = df[col]
            for val in series:
                if pd.isna(val):
                    continue
                try:
                    values.append(float(val))
                except (TypeError, ValueError):
                    continue

        if not values:
            return 0.0, 1.0

        min_val = min(values)
        max_val = max(values)
        if min_val == max_val:
            return min_val, min_val + 1e-6
        return min_val, max_val

    def _on_row_clicked(self, row: int):
        """Handle row click (Story column) - toggle row selection."""
        # Toggle row selection
        if row in self._selected_rows:
            self._selected_rows.remove(row)
        else:
            self._selected_rows.add(row)

        # Update all column highlighting (to update bold state)
        self._update_column_highlighting()

    def _on_header_hovered(self, display_name: str):
        """
        Handle header hover - translate shorthand to full name before emitting.

        Args:
            display_name: The displayed header text (might be shorthand like "Px1")
        """
        # If we have reverse mapping (shorthand -> full name), use it
        if self._reverse_mapping and display_name in self._reverse_mapping:
            full_name = self._reverse_mapping[display_name]
            self.load_case_hovered.emit(full_name)
        else:
            # No mapping or not a shorthand - emit as is
            self.load_case_hovered.emit(display_name)

    def _on_header_clicked(self, logical_index: int):
        """Handle header clicks - toggle selection for load case columns, allow sorting only for Story."""
        if not hasattr(self, '_column_names') or logical_index >= len(self._column_names):
            return

        col_name = self._column_names[logical_index]

        # Check if it's a selectable load case column
        if col_name not in self._non_selectable_columns:
            # Toggle selection
            if col_name in self._selected_load_cases:
                self._selected_load_cases.remove(col_name)
            else:
                self._selected_load_cases.add(col_name)

            # Update header styling
            self._update_header_styling()

            # Emit selection changed signal with list of selected cases
            self.selection_changed.emit(list(self._selected_load_cases))

        elif col_name == 'Story':
            # Story column - toggle sort order
            if self._story_sort_order == Qt.SortOrder.AscendingOrder:
                self._story_sort_order = Qt.SortOrder.DescendingOrder
            else:
                self._story_sort_order = Qt.SortOrder.AscendingOrder

            # Apply the sort
            self.table.sortItems(logical_index, self._story_sort_order)
            self.table.horizontalHeader().setSortIndicator(logical_index, self._story_sort_order)
        # Avg, Max, Min columns - do nothing

    def eventFilter(self, obj, event):
        """Handle hover effects - bold only the hovered cell."""
        table = obj.parent()
        if not isinstance(table, ClickableTableWidget):
            return False

        if event.type() in (QEvent.Type.MouseMove, QEvent.Type.HoverMove):
            if hasattr(event, "pos"):
                pos = event.pos()
            else:
                # QHoverEvent exposes position() returning QPointF
                pos = event.position().toPoint()
            item = table.itemAt(pos)
            new_row = item.row() if item else -1
            new_col = item.column() if item else -1
            old_row = getattr(table, '_hovered_row', -1)
            old_col = getattr(table, '_hovered_col', -1)

            # Only update if hovered cell changed
            if new_row != old_row or new_col != old_col:
                # Clear bold on old hovered cell
                if old_row >= 0 and old_col >= 0:
                    old_item = table.item(old_row, old_col)
                    if old_item:
                        # Only remove bold if not in selected row/column
                        old_col_name = self._column_names[old_col] if old_col < len(self._column_names) else ""
                        is_selected = (old_row in self._selected_rows) or (old_col_name in self._selected_load_cases)
                        old_item.setData(PerimeterBorderDelegate.BoldRole, is_selected)

                # Set bold on new hovered cell
                if new_row >= 0 and new_col >= 0:
                    new_item = table.item(new_row, new_col)
                    if new_item:
                        new_item.setData(PerimeterBorderDelegate.BoldRole, True)

                table._hovered_row = new_row
                table._hovered_col = new_col
                table.viewport().update()

        elif event.type() in (QEvent.Type.Leave, QEvent.Type.HoverLeave):
            # Clear bold on hovered cell when mouse leaves
            old_row = getattr(table, '_hovered_row', -1)
            old_col = getattr(table, '_hovered_col', -1)
            if old_row >= 0 and old_col >= 0:
                old_item = table.item(old_row, old_col)
                if old_item:
                    old_col_name = self._column_names[old_col] if old_col < len(self._column_names) else ""
                    is_selected = (old_row in self._selected_rows) or (old_col_name in self._selected_load_cases)
                    old_item.setData(PerimeterBorderDelegate.BoldRole, is_selected)
            table._hovered_row = -1
            table._hovered_col = -1
            table.viewport().update()

        return False

    def _apply_row_style(self, table, row):
        """Apply style to a row based on selection and column selection state."""
        from PyQt6.QtGui import QColor, QBrush

        if row < 0 or row >= table.rowCount():
            return

        is_row_selected = (row in self._selected_rows)
        selection_color = QColor("#1f2937")
        col_select_color = QColor("#1a2a30")  # Subtle teal tint for column selection

        for col in range(table.columnCount()):
            item = table.item(row, col)
            if not item:
                continue

            original_color = getattr(item, '_original_color', None)
            if original_color is not None:
                item.setForeground(original_color)

            # Check if this column is selected
            col_name = self._column_names[col] if col < len(self._column_names) else ""
            is_col_selected = col_name in self._selected_load_cases

            # Apply background overlay based on states (priority order)
            if is_row_selected:
                bg_color = selection_color
            elif is_col_selected:
                bg_color = col_select_color
            else:
                bg_color = None

            if bg_color:
                brush = QBrush(bg_color)
                item.setBackground(brush)
                item.setData(Qt.ItemDataRole.BackgroundRole, bg_color)
            else:
                item.setBackground(QBrush())
                item.setData(Qt.ItemDataRole.BackgroundRole, None)

            # Set bold for selected cells (column or row selection)
            should_bold = is_col_selected or is_row_selected
            item.setData(PerimeterBorderDelegate.BoldRole, should_bold)

        # Force table to repaint this row
        table.viewport().update()

    def _update_header_styling(self):
        """Update header styling to highlight selected columns."""
        header = self.table.horizontalHeader()
        if isinstance(header, SelectableHeaderView):
            header.set_selected_sections(self._selected_load_cases)
        # Also update column cell highlighting
        self._update_column_highlighting()

    def _update_column_highlighting(self):
        """Apply gentle background highlight and bold text to selected columns and rows."""
        from PyQt6.QtGui import QBrush, QColor

        # Colors for different states
        col_select_color = QColor("#1a2a30")  # Gentle teal tint for column selection
        row_select_color = QColor("#1f2937")  # Row selection

        row_count = self.table.rowCount()
        col_count = len(self._column_names)

        for col_idx in range(col_count):
            col_name = self._column_names[col_idx]
            is_col_selected = col_name in self._selected_load_cases

            for row_idx in range(row_count):
                item = self.table.item(row_idx, col_idx)
                if not item:
                    continue

                is_row_selected = (row_idx in self._selected_rows)

                # Determine background color based on states (row selection takes priority)
                if is_row_selected:
                    bg_color = row_select_color
                elif is_col_selected:
                    bg_color = col_select_color
                else:
                    bg_color = None

                if bg_color:
                    item.setBackground(QBrush(bg_color))
                    item.setData(Qt.ItemDataRole.BackgroundRole, bg_color)
                else:
                    item.setBackground(QBrush())
                    item.setData(Qt.ItemDataRole.BackgroundRole, None)

                # Set bold for selected cells (column or row selection)
                # But preserve hover bold state if cell is currently hovered
                hovered_row = getattr(self.table, '_hovered_row', -1)
                hovered_col = getattr(self.table, '_hovered_col', -1)
                is_hovered = (row_idx == hovered_row and col_idx == hovered_col)
                should_bold = is_col_selected or is_row_selected or is_hovered
                item.setData(PerimeterBorderDelegate.BoldRole, should_bold)

        # Force repaint
        self.table.viewport().repaint()

    def clear_data(self):
        """Clear table contents but preserve shorthand mapping."""
        self.table.setRowCount(0)
        self.table.setColumnCount(0)
        self._selected_load_cases.clear()
        self._selected_rows.clear()
        self._dataset = None
        self._column_names = []
        self._load_case_columns = []
        self._load_case_column_set.clear()
        self._non_selectable_columns = {"Story"}
        # Note: We intentionally DON'T clear _shorthand_mapping or _reverse_mapping
        # They should persist until explicitly cleared or replaced
        self.table._hovered_row = -1
        self._current_result_type = None
        self._apply_type_styles("")
        header = self.table.horizontalHeader()
        if isinstance(header, QHeaderView):
            header.setSortIndicatorShown(False)
        self._update_header_styling()

    def _column_width_for_type(self) -> int:
        """Column width optimized for 10px font to fit table and plot without scrolling."""
        base = self._base_result_type()
        if base == "Drifts":
            return 50
        if base == "Accelerations":
            return 48
        if base == "Forces":
            return 52
        if base == "Displacements":
            return 48
        if base == "WallShears":
            return 52
        if base == "QuadRotations":
            return 50
        return 46

    def _base_result_type(self) -> str:
        value = self._current_result_type or ""
        if not value:
            return ""
        if value.startswith("MaxMin"):
            value = value.replace("MaxMin", "", 1)
        if "_" in value:
            value = value.split("_", 1)[0]
        return value

    def _apply_type_styles(self, base_type: str) -> None:
        font_size = 13
        if base_type in {"Forces", "Displacements", "WallShears", "QuadRotations"}:
            font_size = 12
        font = QFont("Inter", font_size)
        self.table.setFont(font)
        header_font = QFont("Inter", font_size)
        self.table.horizontalHeader().setFont(header_font)
