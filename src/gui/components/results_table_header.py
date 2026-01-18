"""Shared table header and table widgets for results tables."""

from __future__ import annotations

from PyQt6.QtCore import Qt, QRect, pyqtSignal, QModelIndex
from PyQt6.QtGui import QColor, QPainter, QPen, QPaintEvent
from PyQt6.QtWidgets import QHeaderView, QTableWidget, QTableWidgetItem, QStyledItemDelegate, QStyleOptionViewItem




class PerimeterBorderDelegate(QStyledItemDelegate):
    """Delegate that draws bottom border on last row only and respects item background."""

    # Custom data role for bold text
    BoldRole = Qt.ItemDataRole.UserRole + 100

    def __init__(self, parent=None):
        super().__init__(parent)
        self._border_color = QColor("#1e2329")

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        # Get the item's background color if set
        table = self.parent()
        if isinstance(table, QTableWidget):
            item = table.item(index.row(), index.column())
            if item:
                bg = item.data(Qt.ItemDataRole.BackgroundRole)
                if bg and isinstance(bg, QColor) and bg.isValid():
                    painter.fillRect(option.rect, bg)

                # Check if text should be bold
                is_bold = item.data(self.BoldRole)
                if is_bold:
                    font = option.font
                    font.setBold(True)
                    option.font = font

        # Draw normal cell content
        super().paint(painter, option, index)

        # Get table dimensions for border drawing
        if not isinstance(table, QTableWidget):
            return

        row = index.row()
        row_count = table.rowCount()
        rect = option.rect

        # Bottom border - 1px for last row only
        if row == row_count - 1:
            painter.save()
            painter.setPen(Qt.PenStyle.NoPen)
            width = rect.width()
            painter.fillRect(rect.left(), rect.bottom(), min(width + 1, self.parent().viewport().width() - rect.left()), 1, self._border_color)
            painter.restore()


class ClickableTableWidget(QTableWidget):
    """QTableWidget that emits row click signals for Story column only."""

    rowClicked = pyqtSignal(int)  # Emitted when Story column (col 0) is clicked

    def __init__(self, parent=None):
        super().__init__(parent)
        self._border_color = QColor("#1e2329")
        # Set delegate for perimeter borders (right and bottom)
        self._perimeter_delegate = PerimeterBorderDelegate(self)
        self.setItemDelegate(self._perimeter_delegate)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            item = self.itemAt(event.pos())
            if item:
                # Only emit row click for Story column (col 0)
                if item.column() == 0:
                    self.rowClicked.emit(item.row())
        super().mousePressEvent(event)

    def paintEvent(self, event: QPaintEvent):
        # Draw normal table content
        super().paintEvent(event)

        # Draw left and right borders on viewport
        if self.rowCount() > 0 and self.columnCount() > 0:
            painter = QPainter(self.viewport())
            painter.setPen(Qt.PenStyle.NoPen)

            # Calculate content dimensions
            content_height = sum(self.rowHeight(i) for i in range(self.rowCount()))
            content_width = sum(self.columnWidth(i) for i in range(self.columnCount()))
            visible_width = min(content_width, self.viewport().width())

            # Draw 1px left border
            painter.fillRect(0, 0, 1, content_height, self._border_color)

            # Draw 1px right border (cap at viewport width to avoid overflow)
            painter.fillRect(visible_width - 1, 0, 1, content_height, self._border_color)

            painter.end()


class SelectableHeaderView(QHeaderView):
    """Custom horizontal header that supports hover + selection styling."""

    section_hovered = pyqtSignal(str)
    section_hover_left = pyqtSignal()

    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self._selected_sections: set[str] = set()
        self._hovered_section = -1
        self.setMouseTracking(True)

    def set_selected_sections(self, sections: set[str]) -> None:
        self._selected_sections = sections
        self.viewport().update()

    def mouseMoveEvent(self, event):
        logical_index = self.logicalIndexAt(event.pos())

        if logical_index != self._hovered_section:
            self._hovered_section = logical_index
            table = self.parent()
            if isinstance(table, QTableWidget) and 0 <= logical_index < table.columnCount():
                item = table.horizontalHeaderItem(logical_index)
                if item:
                    col_name = item.text()
                    non_selectable = getattr(
                        table, "_non_selectable_columns", {'Story', 'Avg', 'Max', 'Min'}
                    )
                    if col_name not in non_selectable:
                        self.section_hovered.emit(col_name)
            self.viewport().update()

        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self._hovered_section = -1
        self.section_hover_left.emit()
        self.viewport().update()
        super().leaveEvent(event)

    def paintEvent(self, event: QPaintEvent):
        # Paint all sections normally
        super().paintEvent(event)

        # Draw right border on the header's right edge (cap at viewport width to avoid overflow)
        table = self.parent()
        if isinstance(table, QTableWidget) and table.columnCount() > 0:
            painter = QPainter(self.viewport())
            painter.setPen(Qt.PenStyle.NoPen)

            # Calculate total width and cap to viewport to avoid painting beyond visible area
            total_width = sum(self.sectionSize(i) for i in range(table.columnCount()))
            visible_width = min(total_width, self.viewport().width())

            # Draw 1px right border at edge
            border_color = QColor("#1e2329")
            painter.fillRect(visible_width - 1, 0, 1, self.height(), border_color)
            painter.end()

    def paintSection(self, painter: QPainter, rect: QRect, logicalIndex: int):
        painter.save()

        table = self.parent()
        if isinstance(table, QTableWidget) and logicalIndex < table.columnCount():
            item = table.horizontalHeaderItem(logicalIndex)
            col_name = item.text() if isinstance(item, QTableWidgetItem) else ""

            is_selected = col_name in self._selected_sections
            is_hovered = logicalIndex == self._hovered_section
            is_first = logicalIndex == 0
            is_last = logicalIndex == table.columnCount() - 1

            # Fill background
            if is_selected:
                painter.fillRect(rect, QColor("#2c5f6b"))
            elif is_hovered:
                painter.fillRect(rect, QColor("#1f2937"))
            else:
                painter.fillRect(rect, QColor("#161b22"))

            border_color = QColor("#1e2329")

            # Top border - 1px for perimeter
            painter.fillRect(rect.left(), rect.top(), rect.width() + 1, 1, border_color)

            # Bottom border (1px) - separates header from data
            painter.fillRect(rect.left(), rect.bottom(), rect.width() + 1, 1, border_color)

            # Left border - 1px for first column (perimeter)
            if is_first:
                painter.fillRect(rect.left(), rect.top(), 1, rect.height() + 1, border_color)

            # Right border - 1px for internal column separators only (cap at viewport width)
            if not is_last:
                border_x = min(rect.right(), self.viewport().width() - 1)
                painter.fillRect(border_x, rect.top(), 1, rect.height() + 1, border_color)

            # Draw text
            font = painter.font()
            if is_selected or is_hovered:
                font.setBold(True)
            painter.setFont(font)

            if is_selected:
                painter.setPen(QColor("#ffffff"))
            elif is_hovered:
                painter.setPen(QColor("#67e8f9"))
            else:
                painter.setPen(QColor("#4a7d89"))

            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, col_name)

        painter.restore()
