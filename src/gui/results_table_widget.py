"""Results table widget - displays tabular data with GMP styling."""

from __future__ import annotations

from typing import List, Optional, Set, TYPE_CHECKING

import pandas as pd
from PyQt6.QtCore import QEvent, QRect, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHeaderView,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from utils.color_utils import get_gradient_color

if TYPE_CHECKING:
    from processing.result_service import ResultDataset


class ClickableTableWidget(QTableWidget):
    """Custom QTableWidget that emits row click signals."""

    rowClicked = pyqtSignal(int)  # Signal emitted when a row is clicked

    def __init__(self, parent=None):
        super().__init__(parent)

    def mousePressEvent(self, event):
        """Override mouse press to emit row click signal."""
        if event.button() == Qt.MouseButton.LeftButton:
            item = self.itemAt(event.pos())
            if item:
                self.rowClicked.emit(item.row())
        super().mousePressEvent(event)


class SelectableHeaderView(QHeaderView):
    """Custom header view that highlights selected sections."""

    # Signal emitted when hovering over a section (column_name)
    section_hovered = pyqtSignal(str)
    section_hover_left = pyqtSignal()

    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self._selected_sections = set()
        self._hovered_section = -1

        # Enable mouse tracking for hover events
        self.setMouseTracking(True)

    def set_selected_sections(self, sections: set):
        """Set which sections are selected."""
        self._selected_sections = sections
        self.viewport().update()

    def mouseMoveEvent(self, event):
        """Track mouse movement for hover effects."""
        logical_index = self.logicalIndexAt(event.pos())

        if logical_index != self._hovered_section:
            self._hovered_section = logical_index

            # Get column name and emit hover signal
            table = self.parent()
            if isinstance(table, QTableWidget) and logical_index >= 0 and logical_index < table.columnCount():
                item = table.horizontalHeaderItem(logical_index)
                if item:
                    col_name = item.text()
                    non_selectable = getattr(
                        table, "_non_selectable_columns", {'Story', 'Avg', 'Max', 'Min'}
                    )
                    # Only emit for load case columns (not Story, Avg, Max, Min)
                    if col_name not in non_selectable:
                        self.section_hovered.emit(col_name)

            self.viewport().update()

        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        """Handle mouse leaving the header."""
        self._hovered_section = -1
        self.section_hover_left.emit()
        self.viewport().update()
        super().leaveEvent(event)

    def paintSection(self, painter: QPainter, rect: QRect, logicalIndex: int):
        """Paint header section with custom styling for selected and hovered sections."""
        painter.save()

        # Get the column name from parent table
        table = self.parent()
        if isinstance(table, QTableWidget) and logicalIndex < table.columnCount():
            item = table.horizontalHeaderItem(logicalIndex)
            col_name = item.text() if item else ""

            # Check if this section is selected or hovered
            is_selected = col_name in self._selected_sections
            is_hovered = logicalIndex == self._hovered_section

            # Draw background (priority: selected > hovered > default)
            if is_selected:
                painter.fillRect(rect, QColor("#2c5f6b"))  # Darker accent for selected
            elif is_hovered:
                painter.fillRect(rect, QColor("#1f2937"))  # Lighter background for hover
            else:
                painter.fillRect(rect, QColor("#161b22"))  # Default background

            # Draw bottom border
            painter.setPen(QColor("#2c313a"))
            painter.drawLine(rect.bottomLeft(), rect.bottomRight())

            # Draw text
            if is_selected:
                painter.setPen(QColor("#ffffff"))  # White text for selected
                font = painter.font()
                font.setBold(True)
                painter.setFont(font)
            elif is_hovered:
                painter.setPen(QColor("#67e8f9"))  # Cyan text for hover
                font = painter.font()
                font.setBold(True)
                painter.setFont(font)
            else:
                painter.setPen(QColor("#4a7d89"))  # Default accent color
                font = painter.font()
                font.setBold(True)
                painter.setFont(font)

            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, col_name)

        painter.restore()


class ResultsTableWidget(QFrame):
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
        # Set size policy: fixed width, expand vertically to match plot height
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)

        # No border on container - table will have its own border
        self.setObjectName("tableContainer")

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
        self._non_selectable_columns: Set[str] = {"Story"}

        self.setup_ui()

    def setup_ui(self):
        """Setup the table UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)  # No margins - table fills container edge-to-edge
        layout.setSpacing(0)

        self.table = ClickableTableWidget()

        # Connect row click signal
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

        # Disable scrolling - table should fit all columns
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Set consistent font across entire table
        table_font = QFont("Inter", 14)
        self.table.setFont(table_font)
        self.table.horizontalHeader().setFont(table_font)

        # Style matching GMP tables
        # NOTE: No background rules for ::item to allow programmatic background styling
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #0a0c10;
                border: 1px solid #2c313a;
                border-radius: 6px;
                gridline-color: #2c313a;
                color: #d1d5db;
            }
            QTableWidget::item {
                padding: 1px 2px;
                border: none;
            }
            QHeaderView::section {
                background-color: #161b22;
                color: #4a7d89;
                padding: 2px 4px;
                border: none;
                border-bottom: 2px solid #2c313a;
                font-weight: 600;
                text-align: center;
            }
            QHeaderView::section:hover {
                background-color: #1f2937;
                color: #67e8f9;
            }
            QTableWidget QTableCornerButton::section {
                background-color: #161b22;
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
            header.section_hovered.connect(self.load_case_hovered.emit)
            header.section_hover_left.connect(self.hover_cleared.emit)

        layout.addWidget(self.table)

    def load_dataset(self, dataset: "ResultDataset"):
        """Load data from a ResultDataset into the table."""
        df = dataset.data
        self._dataset = dataset
        self._current_result_type = dataset.meta.result_type or ""
        self._apply_type_styles(self._base_result_type())
        self._selected_load_cases.clear()
        self._selected_rows.clear()
        self._load_case_columns = list(dataset.load_case_columns)
        self._load_case_column_set = set(self._load_case_columns)
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
        story_column_width = 60
        data_column_width = self._column_width_for_type()

        for col_idx in range(column_count):
            if col_idx == 0:
                self.table.setColumnWidth(col_idx, story_column_width)
            else:
                self.table.setColumnWidth(col_idx, data_column_width)

        total_width = story_column_width + max(0, column_count - 1) * data_column_width + 2
        self.table.setMinimumWidth(total_width)
        self.table.setMaximumWidth(total_width)
        self.setMinimumWidth(total_width)
        self.setMaximumWidth(total_width)

    def _format_value(self, value, config) -> str:
        """Format numeric table value with unit string."""
        if pd.isna(value):
            return "-"
        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            return str(value)
        base_type = self._base_result_type()
        if base_type in {"Accelerations", "Forces", "Displacements"}:
            unit_suffix = ""
        else:
            unit_suffix = config.unit or ""
        return f"{numeric_value:.{config.decimal_places}f}{unit_suffix}"

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
        """Handle row click - toggle selection."""
        # Toggle row selection
        if row in self._selected_rows:
            self._selected_rows.remove(row)
        else:
            self._selected_rows.add(row)

        # Update row styling
        self._apply_row_style(self.table, row)

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
        """Handle hover effects for table rows."""
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
            old_row = getattr(table, '_hovered_row', -1)

            if new_row != old_row:
                if old_row >= 0:
                    self._apply_row_hover(table, old_row, False)
                if new_row >= 0:
                    self._apply_row_hover(table, new_row, True)

        elif event.type() in (QEvent.Type.Leave, QEvent.Type.HoverLeave):
            # Clear hover when mouse leaves table
            old_row = getattr(table, '_hovered_row', -1)
            if old_row >= 0:
                self._apply_row_hover(table, old_row, False)

        return False

    def _apply_row_style(self, table, row, hovered=None):
        """Apply style to a row based on hover and selection state."""
        from PyQt6.QtGui import QColor, QBrush

        if row < 0 or row >= table.rowCount():
            return

        if hovered is None:
            hovered = (row == getattr(table, '_hovered_row', -1))
        is_selected = (row in self._selected_rows)

        hover_color = QColor("#1c2128")
        selection_color = QColor("#1f2937")
        combined_color = QColor("#264653")

        for col in range(table.columnCount()):
            item = table.item(row, col)
            if not item:
                continue

            original_color = getattr(item, '_original_color', None)
            if original_color is not None:
                item.setForeground(original_color)

            # Apply background overlay if hovered or selected
            if hovered and is_selected:
                bg_color = combined_color
            elif is_selected:
                bg_color = selection_color
            elif hovered:
                bg_color = hover_color
            else:
                bg_color = None

            if bg_color:
                brush = QBrush(bg_color)
                item.setBackground(brush)
                item.setData(Qt.ItemDataRole.BackgroundRole, bg_color)
            else:
                item.setBackground(QBrush())
                item.setData(Qt.ItemDataRole.BackgroundRole, None)

        # Force table to repaint this row
        table.viewport().update()

    def _apply_row_hover(self, table, row, is_hovered):
        """Apply or remove hover effect from a row."""
        if row < 0 or row >= table.rowCount():
            return

        if is_hovered:
            table._hovered_row = row
        elif getattr(table, '_hovered_row', -1) == row:
            table._hovered_row = -1

        self._apply_row_style(table, row, hovered=is_hovered)

    def _update_header_styling(self):
        """Update header styling to highlight selected columns."""
        header = self.table.horizontalHeader()
        if isinstance(header, SelectableHeaderView):
            header.set_selected_sections(self._selected_load_cases)

    def clear_data(self):
        """Clear table contents."""
        self.table.setRowCount(0)
        self.table.setColumnCount(0)
        self._selected_load_cases.clear()
        self._selected_rows.clear()
        self._dataset = None
        self._column_names = []
        self._load_case_columns = []
        self._load_case_column_set.clear()
        self._non_selectable_columns = {"Story"}
        self.table._hovered_row = -1
        self._current_result_type = None
        self._apply_type_styles("")
        header = self.table.horizontalHeader()
        if isinstance(header, QHeaderView):
            header.setSortIndicatorShown(False)
        self._update_header_styling()

    def _column_width_for_type(self) -> int:
        base = self._base_result_type()
        if base == "Drifts":
            return 58
        if base == "Accelerations":
            return 54
        if base == "Forces":
            return 60
        if base == "Displacements":
            return 56
        return 50

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
        if base_type in {"Forces", "Displacements"}:
            font_size = 12
        font = QFont("Inter", font_size)
        self.table.setFont(font)
        header_font = QFont("Inter", font_size)
        self.table.horizontalHeader().setFont(header_font)
