"""Reusable legend components for result plots."""

from __future__ import annotations

from typing import Callable, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QWidget


class InteractiveLegendItem(QWidget):
    """Legend entry that supports hover + click interactions."""

    def __init__(
        self,
        label: str,
        color: str,
        on_toggle: Optional[Callable[[str], None]] = None,
        on_hover: Optional[Callable[[str], None]] = None,
        on_leave: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__()
        self.label = label
        self.color = color
        self._on_toggle = on_toggle
        self._on_hover = on_hover
        self._on_leave = on_leave
        self.is_selected = False

        self.setStyleSheet(
            f"""
            background-color: transparent;
            border-left: 3px solid {color};
            border-radius: 4px;
            padding-left: 4px;
        """
        )
        self.setContentsMargins(0, 3, 0, 3)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        color_label = QLabel()
        color_label.setStyleSheet(
            f"""
            QLabel {{
                background-color: {color};
                border: none;
                border-radius: 2px;
                min-width: 30px;
                max-width: 30px;
                min-height: 3px;
                max-height: 3px;
            }}
        """
        )

        self.text_label = QLabel(label)
        self.text_label.setStyleSheet(
            "QLabel { color: #d1d5db; font-size: 10pt; font-weight: 600; }"
        )

        layout.addWidget(color_label)
        layout.addWidget(self.text_label)
        layout.addStretch()

    def enterEvent(self, event):
        if self._on_hover:
            self._on_hover(self.label)
        self.setStyleSheet(
            f"""
            background-color: rgba(255, 255, 255, 0.08);
            border-left: 3px solid {self.color};
            border-radius: 4px;
            padding-left: 4px;
        """
        )
        self.text_label.setStyleSheet(
            "QLabel { color: #ffffff; font-size: 10pt; font-weight: 600; }"
        )
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self._on_leave:
            self._on_leave()
        self.set_selected(self.is_selected)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._on_toggle:
            self._on_toggle(self.label)
        super().mousePressEvent(event)

    def set_selected(self, selected: bool):
        self.is_selected = selected
        if selected:
            self.setStyleSheet(
                f"""
                background-color: rgba(103, 232, 249, 0.15);
                border-left: 3px solid {self.color};
                border-radius: 4px;
                padding-left: 4px;
            """
            )
            self.text_label.setStyleSheet(
                "QLabel { color: #67e8f9; font-size: 10pt; font-weight: 600; }"
            )
        else:
            self.setStyleSheet(
                f"""
                background-color: transparent;
                border-left: 3px solid {self.color};
                border-radius: 4px;
                padding-left: 4px;
            """
            )
            self.text_label.setStyleSheet(
                "QLabel { color: #d1d5db; font-size: 10pt; font-weight: 600; }"
            )


def create_static_legend_item(color: str, label: str, pen_style: Qt.PenStyle = Qt.PenStyle.SolidLine) -> QWidget:
    """Return a non-interactive legend entry."""
    item_widget = QWidget()
    item_widget.setStyleSheet("background-color: transparent;")
    item_widget.setContentsMargins(0, 3, 0, 3)

    layout = QHBoxLayout(item_widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(10)

    indicator = QLabel()
    indicator.setStyleSheet(
        f"""
        QLabel {{
            min-width: 30px;
            max-width: 30px;
            min-height: 1px;
            max-height: 1px;
            border-bottom: 2px {'dashed' if pen_style == Qt.PenStyle.DashLine else 'solid'} {color};
        }}
    """
    )

    text_label = QLabel(label)
    text_label.setStyleSheet("QLabel { color: #d1d5db; font-size: 10pt; font-weight: 600; }")

    layout.addWidget(indicator)
    layout.addWidget(text_label)
    layout.addStretch()
    return item_widget
