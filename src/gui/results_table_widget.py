"""Results table widget - displays tabular data with GMP styling."""

import pandas as pd
from PyQt6.QtCore import Qt, pyqtSignal, QRect, QEvent
from PyQt6.QtGui import QColor, QFont, QPainter
from PyQt6.QtWidgets import (QAbstractItemView, QFrame, QHeaderView,
                             QSizePolicy, QTableWidget, QTableWidgetItem,
                             QVBoxLayout, QWidget, QStyleOptionHeader, QStyle)
from config.result_config import get_config
from utils.color_utils import get_gradient_color


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
                    # Only emit for load case columns (not Story, Avg, Max, Min)
                    if col_name not in ['Story', 'Avg', 'Max', 'Min']:
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
                padding: 3px 4px;
                border: none;
            }
            QHeaderView::section {
                background-color: #161b22;
                color: #4a7d89;
                padding: 4px 6px;
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
        header.setDefaultSectionSize(55)  # Default column width
        header.setSectionsClickable(True)  # Enable clicking

        self.table.verticalHeader().setVisible(False)
        self.table.setWordWrap(False)  # Prevent wrapping for compact display

        # Enable mouse tracking for row hover effects
        self.table.setMouseTracking(True)
        self.table.viewport().setMouseTracking(True)

        # Store references for hover tracking
        self.table._hovered_row = -1

        # Install event filter for hover effects only
        self.table.viewport().installEventFilter(self)

        # Connect header click signal
        header.sectionClicked.connect(self._on_header_clicked)

        # Connect hover signals from custom header
        if isinstance(header, SelectableHeaderView):
            header.section_hovered.connect(self.load_case_hovered.emit)
            header.section_hover_left.connect(self.hover_cleared.emit)

        layout.addWidget(self.table)

    def load_data(self, df: pd.DataFrame, result_type: str):
        """Load data from DataFrame into table."""
        if df.empty:
            self.clear_data()
            return

        # Set table dimensions
        self.table.setRowCount(len(df))
        self.table.setColumnCount(len(df.columns))
        self.table.setHorizontalHeaderLabels(df.columns.tolist())

        # Calculate min/max across load case columns for gradient coloring
        load_case_cols = [col for col in df.columns if col not in ['Story', 'Avg', 'Max', 'Min']]
        all_load_case_values = []

        if load_case_cols:
            for col in load_case_cols:
                for val in df[col]:
                    try:
                        all_load_case_values.append(float(val))
                    except (ValueError, TypeError):
                        pass

        min_val = min(all_load_case_values) if all_load_case_values else 0
        max_val = max(all_load_case_values) if all_load_case_values else 1
        value_range = max_val - min_val if max_val != min_val else 1

        # Populate data
        for row_idx, (_, row) in enumerate(df.iterrows()):
            for col_idx, value in enumerate(row):
                item = QTableWidgetItem()

                # Format value based on column
                col_name = df.columns[col_idx]

                if col_idx == 0:  # Story column
                    item.setText(str(value))
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    # Story column styling - store default color
                    default_color = QColor("#d1d5db")
                    item.setForeground(default_color)
                    item._original_color = QColor(default_color)  # Store a copy
                else:
                    # Numeric columns
                    try:
                        numeric_value = float(value)

                        # Format based on result type configuration
                        config = get_config(result_type)
                        converted_value = numeric_value * config.multiplier
                        formatted = f"{converted_value:.{config.decimal_places}f}{config.unit}"

                        item.setText(formatted)
                        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                        # Apply color based on column type
                        if col_name in ['Avg', 'Max', 'Min']:
                            # Summary columns - keep default text color
                            default_color = QColor("#d1d5db")
                            item.setForeground(default_color)
                            item._original_color = QColor(default_color)  # Store a copy
                        elif col_name != 'Story':
                            # Load case columns - apply gradient using color scheme
                            config = get_config(result_type)
                            color = get_gradient_color(
                                numeric_value,
                                min_val,
                                max_val,
                                config.color_scheme
                            )
                            item.setForeground(color)
                            item._original_color = QColor(color)  # Store a copy

                    except (ValueError, TypeError):
                        item.setText(str(value))
                        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                self.table.setItem(row_idx, col_idx, item)

        # Set column widths - first column (Story) different from data columns
        story_column_width = 70  # Width for Story column
        data_column_width = 55   # Width for data columns (TH01, TH02, Avg, Max, Min, etc.)

        for col_idx in range(len(df.columns)):
            if col_idx == 0:  # First column (Story)
                self.table.setColumnWidth(col_idx, story_column_width)
            else:  # Data columns
                self.table.setColumnWidth(col_idx, data_column_width)

        # Store column names for later reference
        self._column_names = df.columns.tolist()

        # Auto-fit container to table content
        # Calculate actual table width needed (columns + small buffer for borders)
        total_width = story_column_width + (len(df.columns) - 1) * data_column_width + 2

        # Set table to this size
        self.table.setMinimumWidth(total_width)
        self.table.setMaximumWidth(total_width)

        # Container matches table width exactly (no extra margins)
        self.setMinimumWidth(total_width)
        self.setMaximumWidth(total_width)

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

        # Check if it's a load case column (not Story, Avg, Max, Min)
        if col_name not in ['Story', 'Avg', 'Max', 'Min']:
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

        if event.type() == QEvent.Type.MouseMove:
            item = table.itemAt(event.pos())
            new_row = item.row() if item else -1
            old_row = getattr(table, '_hovered_row', -1)

            if new_row != old_row:
                if old_row >= 0:
                    self._apply_row_hover(table, old_row, False)
                if new_row >= 0:
                    self._apply_row_hover(table, new_row, True)

        elif event.type() == QEvent.Type.Leave:
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

        for col in range(table.columnCount()):
            item = table.item(row, col)
            if item and hasattr(item, '_original_color'):
                # Always restore original foreground color
                item.setForeground(item._original_color)

                # Apply background overlay if hovered or selected
                if hovered or is_selected:
                    bg_color = QColor(103, 232, 249, 64 if hovered and not is_selected else 96)
                    brush = QBrush(bg_color)
                    item.setBackground(brush)
                else:
                    # Clear background completely
                    item.setBackground(QBrush())

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
