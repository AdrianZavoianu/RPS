"""Shared table header and table widgets for results tables."""

from __future__ import annotations

from PyQt6.QtCore import Qt, QRect, pyqtSignal
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QHeaderView, QTableWidget, QTableWidgetItem


class ClickableTableWidget(QTableWidget):
    """QTableWidget that emits row click signals instead of using Qt selection."""

    rowClicked = pyqtSignal(int)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            item = self.itemAt(event.pos())
            if item:
                self.rowClicked.emit(item.row())
        super().mousePressEvent(event)


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

    def paintSection(self, painter: QPainter, rect: QRect, logicalIndex: int):
        painter.save()

        table = self.parent()
        if isinstance(table, QTableWidget) and logicalIndex < table.columnCount():
            item = table.horizontalHeaderItem(logicalIndex)
            col_name = item.text() if isinstance(item, QTableWidgetItem) else ""

            is_selected = col_name in self._selected_sections
            is_hovered = logicalIndex == self._hovered_section

            if is_selected:
                painter.fillRect(rect, QColor("#2c5f6b"))
            elif is_hovered:
                painter.fillRect(rect, QColor("#1f2937"))
            else:
                painter.fillRect(rect, QColor("#161b22"))

            painter.setPen(QColor("#2c313a"))
            painter.drawLine(rect.bottomLeft(), rect.bottomRight())

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
